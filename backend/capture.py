"""Live capture bridge: calls real scrapers and saves responses into the new schema."""
import asyncio
import os
import sys
import uuid
from pathlib import Path

import aiosqlite

# Add repo root to sys.path so scraper.* imports resolve from within backend/
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

from database import DB_PATH
from judge import judge_run


async def _capture_wanderboat(query_text: str) -> tuple[str | None, str | None, int]:
    from scraper.adapters.wanderboat_http import scrape
    result = await scrape(query_text)
    return result.response, result.error, result.duration_ms


def _run_mindtrip_sync(query_text: str, session_file: str, email: str, password: str) -> tuple[str | None, str | None, int]:
    """Run Playwright in a new thread-local ProactorEventLoop (Windows SelectorEventLoop can't spawn subprocesses)."""
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _inner():
        from scraper.adapters.mindtrip import MindTripAdapter
        from scraper.core.runner import run_scrape

        class _AbsMindTripAdapter(MindTripAdapter):
            SESSION_FILE = session_file

        result = await run_scrape(
            adapter_class=_AbsMindTripAdapter,
            credentials={"email": email, "password": password},
            prompt=query_text,
            headless=True,
        )
        return result.response, result.error, result.duration_ms

    try:
        return loop.run_until_complete(_inner())
    finally:
        loop.close()


async def _capture_mindtrip(query_text: str) -> tuple[str | None, str | None, int]:
    return await asyncio.get_event_loop().run_in_executor(
        None,
        _run_mindtrip_sync,
        query_text,
        str(_REPO_ROOT / "sessions" / "mindtrip_session.json"),
        os.environ.get("SCRAPER_EMAIL", ""),
        os.environ.get("SCRAPER_PASSWORD", ""),
    )


MT_CONCURRENCY = 3  # max simultaneous Playwright browser instances (~200 MB each)


async def capture_live_run(run_id: str, query_ids: list[str] | None = None):
    """
    Scrape all queries in parallel:
    - Wanderboat (async HTTP): all queries fire at once, no limit.
    - Mindtrip (Playwright): capped at MT_CONCURRENCY simultaneous browsers.
    WB + MT still run in parallel within each query. Results written to DB as
    each query completes so the progress endpoint reflects real-time state.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if query_ids:
            placeholders = ",".join("?" * len(query_ids))
            cur = await db.execute(
                f"SELECT id, query_text FROM queries WHERE id IN ({placeholders})",
                query_ids,
            )
        else:
            cur = await db.execute("SELECT id, query_text FROM queries")
        queries = [dict(r) for r in await cur.fetchall()]

    print(f"[capture] Live run {run_id} — {len(queries)} queries (MT concurrency={MT_CONCURRENCY})")

    mt_sem = asyncio.Semaphore(MT_CONCURRENCY)

    async def _scrape_query(q: dict):
        query_id = q["id"]
        query_text = q["query_text"]
        print(f"[capture] start {query_id}: {query_text[:60]!r}")

        async def _mt():
            async with mt_sem:
                return await _capture_mindtrip(query_text)

        (wb_resp, wb_err, wb_ms), (mt_resp, mt_err, mt_ms) = await asyncio.gather(
            _capture_wanderboat(query_text),
            _mt(),
        )

        async with aiosqlite.connect(DB_PATH) as db:
            for product, resp_text, err in [
                ("wanderboat", wb_resp, wb_err),
                ("mindtrip",   mt_resp, mt_err),
            ]:
                text = resp_text or f"[capture error: {err}]"
                await db.execute(
                    "INSERT INTO responses "
                    "(id, run_id, query_id, product, response_text, capture_method) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), run_id, query_id, product, text, "live"),
                )
            await db.commit()

        print(
            f"[capture] done  {query_id}: "
            f"wb={'ok' if wb_resp else 'err'}({wb_ms}ms)  "
            f"mt={'ok' if mt_resp else 'err'}({mt_ms}ms)"
        )

    await asyncio.gather(*[_scrape_query(q) for q in queries])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE runs SET status='judging' WHERE id=?", (run_id,))
        await db.commit()

    print(f"[capture] All captured — judging run {run_id}")
    await judge_run(run_id)

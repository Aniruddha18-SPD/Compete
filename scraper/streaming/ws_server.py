"""
WebSocket browser-streaming server.

One WebSocket connection = one browser session.
  - Client connects with ?site=mindtrip (or wanderboat)
  - Server launches Chromium, navigates to the site's login page
  - Server streams JPEG screenshots as binary frames at ~10 fps
  - Client sends JSON control events: {type: "click"|"keydown"|"scroll", ...}
  - Server detects login via cookie/URL marker, saves storage_state, sends
    {type: "login_detected"} message, then closes the browser

Run:
    uvicorn scraper.streaming.ws_server:app --host 0.0.0.0 --port 8765
"""

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright, Page

# Load .env so scraper credentials are available when triggered via API
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

app = FastAPI(title="Compete")

# Serve the login-stream frontend static assets
_FRONTEND = Path(__file__).parent / "frontend"
if _FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND)), name="static")

# Compete dashboard lives at the repo root
_DASHBOARD = Path(__file__).parent.parent.parent / "compete_dashboard.html"


SITE_CONFIG = {
    "mindtrip": {
        "login_url": "https://mindtrip.ai",
        "session_file": "sessions/mindtrip_session.json",
        # CSS selector that is VISIBLE only when logged in (chat input)
        "logged_in_selector": "[placeholder='Ask anything']",
    },
    "wanderboat": {
        "login_url": "https://wanderboat.ai",
        "session_file": "sessions/wanderboat_session.json",
        # Wanderboat redirects to /chat after login
        "login_url_pattern": "wanderboat.ai/chat",
    },
}

SCREENSHOT_INTERVAL = 0.1  # seconds between frames (~10 fps)


async def _is_logged_in(page: Page, cfg: dict) -> bool:
    """Return True only when a reliable post-login element is visible."""
    # Preferred: a DOM element that only appears after login
    selector = cfg.get("logged_in_selector")
    if selector:
        return await page.locator(selector).count() > 0

    # Fallback: URL-contains check (Wanderboat redirects to /chat)
    url_pattern = cfg.get("login_url_pattern")
    if url_pattern:
        return url_pattern in page.url

    return False


async def _screenshot_loop(page: Page, ws: WebSocket, stop_event: asyncio.Event) -> None:
    """Continuously send JPEG screenshots as binary WebSocket frames."""
    while not stop_event.is_set():
        try:
            screenshot = await page.screenshot(type="jpeg", quality=60, full_page=False)
            await ws.send_bytes(screenshot)
        except Exception:
            break
        await asyncio.sleep(SCREENSHOT_INTERVAL)


async def _event_loop(page: Page, ws: WebSocket, stop_event: asyncio.Event) -> None:
    """Receive control events from the client and forward to Playwright."""
    while not stop_event.is_set():
        try:
            raw = await ws.receive_text()
            event = json.loads(raw)
        except WebSocketDisconnect:
            stop_event.set()
            break
        except Exception:
            continue

        etype = event.get("type")
        try:
            if etype == "click":
                await page.mouse.click(event["x"], event["y"])
            elif etype == "dblclick":
                await page.mouse.dblclick(event["x"], event["y"])
            elif etype == "mousemove":
                await page.mouse.move(event["x"], event["y"])
            elif etype == "keydown":
                key = event.get("key", "")
                if len(key) == 1:
                    await page.keyboard.type(key)
                else:
                    await page.keyboard.press(key)
            elif etype == "scroll":
                await page.mouse.wheel(event.get("dx", 0), event.get("dy", 0))
            elif etype == "navigate":
                await page.goto(event["url"])
            elif etype == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
        except Exception as exc:
            await ws.send_text(json.dumps({"type": "error", "message": str(exc)}))


@app.websocket("/ws/login")
async def login_stream(ws: WebSocket):
    await ws.accept()

    params = dict(ws.query_params)
    site = params.get("site", "mindtrip")
    cfg = SITE_CONFIG.get(site)
    if not cfg:
        await ws.send_text(json.dumps({"type": "error", "message": f"Unknown site: {site}"}))
        await ws.close()
        return

    await ws.send_text(json.dumps({"type": "status", "message": f"Launching browser for {site}..."}))

    try:
        async with async_playwright() as pw:
            try:
                browser = await pw.chromium.launch(channel="chrome", headless=False)
            except Exception:
                browser = await pw.chromium.launch(headless=False)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()

            await ws.send_text(json.dumps({"type": "status", "message": f"Browser open — navigating to {site}..."}))
            await page.goto(cfg["login_url"])
            await ws.send_text(json.dumps({"type": "status", "message": "Page loaded — please log in."}))

            stop_event = asyncio.Event()

            screenshot_task = asyncio.create_task(_screenshot_loop(page, ws, stop_event))
            event_task = asyncio.create_task(_event_loop(page, ws, stop_event))

            # Poll for login detection (only after a short delay to avoid false positives on page load)
            try:
                await asyncio.sleep(3)  # let page fully render before first check
                while not stop_event.is_set():
                    if await _is_logged_in(page, cfg):
                        session_path = cfg["session_file"]
                        Path(session_path).parent.mkdir(parents=True, exist_ok=True)
                        await context.storage_state(path=session_path)
                        await ws.send_text(json.dumps({
                            "type": "login_detected",
                            "site": site,
                            "session_file": session_path,
                            "message": f"Login detected! Session saved to {session_path}",
                        }))
                        await asyncio.sleep(2)
                        stop_event.set()
                        break
                    await asyncio.sleep(1)
            except WebSocketDisconnect:
                stop_event.set()

            screenshot_task.cancel()
            event_task.cancel()
            await asyncio.gather(screenshot_task, event_task, return_exceptions=True)
            await context.close()
            await browser.close()

    except Exception as exc:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": f"Browser error: {exc}"}))
        except Exception:
            pass

    try:
        await ws.close()
    except Exception:
        pass


@app.get("/")
async def index():
    if _DASHBOARD.exists():
        return HTMLResponse(_DASHBOARD.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Compete</h1><p>Dashboard not found.</p>")


@app.get("/login")
async def login_page():
    html_path = _FRONTEND / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Compete Browser Stream</h1><p>Frontend not found.</p>")


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Eval API ─────────────────────────────────────────────────────────────────

@app.get("/api/evals")
async def api_evals(limit: int = 50):
    from scraper.core.database import init_db, list_evals_with_responses
    init_db()
    return list_evals_with_responses(limit=limit)


@app.get("/api/evals/{eval_id}")
async def api_eval(eval_id: int):
    from fastapi import HTTPException
    from scraper.core.database import init_db, get_eval_with_responses
    init_db()
    row = get_eval_with_responses(eval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Eval not found")
    return row


@app.post("/api/run")
async def api_run(body: dict):
    """
    Trigger a live eval. Streams Server-Sent Events with progress updates,
    then a final 'done' event containing the full result JSON.

    Body: {"prompt": "...", "bucket": "transactional"|...}
    """
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="prompt is required")
    bucket = body.get("bucket") or None

    async def event_stream():
        def msg(event: str, data: str) -> str:
            return f"event: {event}\ndata: {data}\n\n"

        yield msg("status", json.dumps({"message": "Starting eval..."}))

        try:
            from compete.runner import run_eval
            from scraper.core.database import get_eval_with_responses
            import asyncio

            # run_eval scrapes both sites and saves to DB; it blocks for ~2min
            result = await run_eval(prompt, bucket=bucket)

            # Fetch the full row with responses for the frontend
            from scraper.core.database import init_db, list_evals_with_responses
            init_db()
            rows = list_evals_with_responses(limit=1)
            latest = rows[0] if rows else {}

            yield msg("done", json.dumps(latest))
        except Exception as exc:
            yield msg("error", json.dumps({"message": str(exc)}))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

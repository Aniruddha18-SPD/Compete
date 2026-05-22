"""Judge worker: OpenAI for scoring, Braintrust for experiment logging."""
import asyncio
import json
import os
import uuid
import aiosqlite
from openai import OpenAI
import braintrust
from database import DB_PATH

from typing import Optional

MODEL = "gpt-4o-mini"
MAX_CONCURRENCY = 5

_oai: Optional[OpenAI] = None


def get_oai() -> OpenAI:
    global _oai
    if _oai is None:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        _oai = OpenAI(api_key=key)
    return _oai


def score_assertion(query_text: str, response_text: str, assertion_text: str,
                    level: str, dimension: str) -> dict:
    """Call OpenAI directly to score one (response, assertion) pair."""
    prompt = f"""You are evaluating an AI travel assistant's response against a specific assertion.

Query: {query_text}

Response: {response_text}

Assertion: {assertion_text}
Severity: {level} | Dimension: {dimension}

Does the response satisfy the assertion? Return JSON with:
- "passed": true or false
- "reasoning": one sentence explaining your verdict
- "confidence": float 0.0–1.0

Return only the JSON object."""

    result = get_oai().chat.completions.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(result.choices[0].message.content.strip())


async def judge_run(run_id: str):
    bt_key = os.environ.get("BRAINTRUST_API_KEY", "")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT run_name FROM runs WHERE id = ?", (run_id,))
        row = await cur.fetchone()
        run_name = row["run_name"] if row else run_id

        cur = await db.execute(
            "SELECT r.id, r.query_id, r.product, r.response_text, q.query_text "
            "FROM responses r JOIN queries q ON r.query_id = q.id WHERE r.run_id = ?",
            (run_id,)
        )
        responses = [dict(r) for r in await cur.fetchall()]

        cur2 = await db.execute(
            "SELECT a.id, a.query_id, a.assertion_text, a.level, a.dimension FROM assertions a"
        )
        all_assertions = [dict(a) for a in await cur2.fetchall()]

    assertions_by_query: dict[str, list] = {}
    for a in all_assertions:
        assertions_by_query.setdefault(a["query_id"], []).append(a)

    # Init Braintrust experiment for logging (does not route LLM calls)
    experiment = None
    if bt_key:
        try:
            experiment = braintrust.init(
                project="Compete - Mindtrip vs Wanderboat",
                experiment=run_name,
                api_key=bt_key,
                update=True,
            )
            print(f"Braintrust experiment '{run_name}' initialised.")
        except Exception as e:
            print(f"Braintrust init warning: {e}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    loop = asyncio.get_event_loop()

    async def judge_one(resp: dict, assertion: dict):
        async with semaphore:
            try:
                verdict = await loop.run_in_executor(
                    None,
                    score_assertion,
                    resp["query_text"], resp["response_text"],
                    assertion["assertion_text"], assertion["level"], assertion["dimension"],
                )
            except Exception as e:
                verdict = {"passed": False, "reasoning": f"Judge error: {e}", "confidence": 0.0}

            # Write to SQLite
            verdict_id = str(uuid.uuid4())
            async with aiosqlite.connect(DB_PATH) as db2:
                await db2.execute(
                    "INSERT INTO verdicts (id, response_id, assertion_id, passed, judge_reasoning, judge_confidence) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (verdict_id, resp["id"], assertion["id"],
                     1 if verdict.get("passed") else 0,
                     verdict.get("reasoning", ""), verdict.get("confidence", 0.5))
                )
                await db2.commit()

            # Log to Braintrust (fire-and-forget, no proxy routing)
            if experiment:
                try:
                    experiment.log(
                        input={"query": resp["query_text"], "assertion": assertion["assertion_text"],
                               "level": assertion["level"], "dimension": assertion["dimension"]},
                        output=resp["response_text"],
                        scores={f"{resp['product']}_pass": 1.0 if verdict.get("passed") else 0.0},
                        metadata={
                            "product": resp["product"],
                            "query_id": resp["query_id"],
                            "assertion_id": assertion["id"],
                            "reasoning": verdict.get("reasoning", ""),
                            "confidence": verdict.get("confidence", 0.5),
                        },
                    )
                except Exception as e:
                    print(f"Braintrust log warning: {e}")

    tasks = []
    for resp in responses:
        for assertion in assertions_by_query.get(resp["query_id"], []):
            tasks.append(judge_one(resp, assertion))

    await asyncio.gather(*tasks)

    # Flush to Braintrust in a thread with timeout so it never blocks the event loop
    if experiment:
        try:
            await asyncio.wait_for(loop.run_in_executor(None, experiment.flush), timeout=30)
            print("Braintrust flush complete.")
        except Exception as e:
            print(f"Braintrust flush warning (non-fatal): {e}")

    await compute_pair_results(run_id)

    async with aiosqlite.connect(DB_PATH) as db3:
        await db3.execute(
            "UPDATE runs SET status='complete', completed_at=CURRENT_TIMESTAMP WHERE id=?",
            (run_id,)
        )
        await db3.commit()

    print(f"Run {run_id} ({run_name}) complete.")


async def compute_pair_results(run_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT DISTINCT query_id FROM responses WHERE run_id = ?", (run_id,)
        )
        query_ids = [r[0] for r in await cur.fetchall()]

        for query_id in query_ids:
            rates = {}
            for product in ["mindtrip", "wanderboat"]:
                cur2 = await db.execute(
                    "SELECT v.passed FROM verdicts v "
                    "JOIN responses r ON v.response_id = r.id "
                    "JOIN assertions a ON v.assertion_id = a.id "
                    "WHERE r.run_id = ? AND r.query_id = ? AND r.product = ? AND a.level = 'critical'",
                    (run_id, query_id, product)
                )
                rows = await cur2.fetchall()
                rates[product] = sum(1 for r in rows if r[0]) / len(rows) if rows else 0.0

            mt, wb = rates.get("mindtrip", 0.0), rates.get("wanderboat", 0.0)
            if mt == 1.0 and wb == 1.0:   outcome = "both_pass"
            elif mt == 0.0 and wb == 0.0: outcome = "both_fail"
            elif mt - wb > 0.2:           outcome = "mindtrip_wins"
            elif wb - mt > 0.2:           outcome = "wanderboat_wins"
            else:                          outcome = "tie"

            await db.execute(
                "INSERT OR REPLACE INTO pair_results "
                "(id, run_id, query_id, mindtrip_pass_rate, wanderboat_pass_rate, outcome) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, query_id, mt, wb, outcome)
            )

        await db.commit()

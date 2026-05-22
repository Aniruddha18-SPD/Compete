import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from database import get_db, init_db, DB_PATH
from models import row_to_dict
from seed_loader import load_seed, create_mock_run
from judge import judge_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await load_seed()
    yield


app = FastAPI(title="Compete API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Runs ──────────────────────────────────────────────────────────────────────

@app.get("/api/runs")
async def list_runs(db=Depends(get_db)):
    cur = await db.execute(
        "SELECT r.*, "
        "(SELECT COUNT(DISTINCT query_id) FROM responses WHERE run_id = r.id) as query_count, "
        "(SELECT COUNT(*) FROM pair_results WHERE run_id = r.id) as result_count "
        "FROM runs r ORDER BY r.created_at DESC"
    )
    rows = await cur.fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/api/runs/mock")
async def create_mock(background_tasks: BackgroundTasks):
    run_id = await create_mock_run()
    background_tasks.add_task(judge_run, run_id)
    return {"run_id": run_id, "status": "judging"}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str, db=Depends(get_db)):
    cur = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row_to_dict(row)


# ── Summary / pivot ────────────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/summary")
async def run_summary(run_id: str, db=Depends(get_db)):
    cur = await db.execute(
        "SELECT pr.outcome, COUNT(*) as count FROM pair_results pr WHERE run_id = ? GROUP BY outcome",
        (run_id,)
    )
    outcome_counts = {r["outcome"]: r["count"] for r in await cur.fetchall()}

    cur2 = await db.execute(
        "SELECT AVG(mindtrip_pass_rate) as mt_avg, AVG(wanderboat_pass_rate) as wb_avg FROM pair_results WHERE run_id = ?",
        (run_id,)
    )
    avgs = row_to_dict(await cur2.fetchone())

    return {
        "outcomes": outcome_counts,
        "mindtrip_avg_pass_rate": round(avgs.get("mt_avg") or 0, 3),
        "wanderboat_avg_pass_rate": round(avgs.get("wb_avg") or 0, 3),
    }


@app.get("/api/runs/{run_id}/pivot")
async def run_pivot(run_id: str, pivot_by: str = "intent", db=Depends(get_db)):
    allowed = {"intent", "domain"}
    if pivot_by not in allowed:
        raise HTTPException(status_code=400, detail=f"pivot_by must be one of {allowed}")

    cur = await db.execute(
        f"SELECT q.{pivot_by} as pivot_val, pr.outcome, pr.mindtrip_pass_rate, pr.wanderboat_pass_rate "
        f"FROM pair_results pr JOIN queries q ON pr.query_id = q.id WHERE pr.run_id = ?",
        (run_id,)
    )
    rows = await cur.fetchall()

    groups: dict = {}
    for r in rows:
        pv = r["pivot_val"]
        if pv not in groups:
            groups[pv] = {"pivot_val": pv, "outcomes": {}, "mt_rates": [], "wb_rates": [], "query_count": 0}
        g = groups[pv]
        g["outcomes"][r["outcome"]] = g["outcomes"].get(r["outcome"], 0) + 1
        g["mt_rates"].append(r["mindtrip_pass_rate"])
        g["wb_rates"].append(r["wanderboat_pass_rate"])
        g["query_count"] += 1

    result = []
    for pv, g in groups.items():
        result.append({
            "pivot_val": pv,
            "query_count": g["query_count"],
            "outcomes": g["outcomes"],
            "mindtrip_pass_rate": round(sum(g["mt_rates"]) / len(g["mt_rates"]), 3),
            "wanderboat_pass_rate": round(sum(g["wb_rates"]) / len(g["wb_rates"]), 3),
        })

    return sorted(result, key=lambda x: x["pivot_val"])


# ── Pair results table ─────────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/pairs")
async def run_pairs(
    run_id: str,
    intent: Optional[str] = None,
    domain: Optional[str] = None,
    outcome: Optional[str] = None,
    db=Depends(get_db)
):
    where = ["pr.run_id = ?"]
    params = [run_id]
    if intent:
        where.append("q.intent = ?")
        params.append(intent)
    if domain:
        where.append("q.domain = ?")
        params.append(domain)
    if outcome:
        where.append("pr.outcome = ?")
        params.append(outcome)

    cur = await db.execute(
        f"SELECT pr.*, q.query_text, q.intent, q.domain, q.query_attrs "
        f"FROM pair_results pr JOIN queries q ON pr.query_id = q.id "
        f"WHERE {' AND '.join(where)} ORDER BY q.intent, q.domain",
        params
    )
    rows = await cur.fetchall()
    return [row_to_dict(r) for r in rows]


# ── Query drill-in ────────────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/queries/{query_id}")
async def query_detail(run_id: str, query_id: str, db=Depends(get_db)):
    cur = await db.execute("SELECT * FROM queries WHERE id = ?", (query_id,))
    query = await cur.fetchone()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    cur2 = await db.execute(
        "SELECT * FROM assertions WHERE query_id = ? ORDER BY level, id", (query_id,)
    )
    assertions = [row_to_dict(r) for r in await cur2.fetchall()]

    # Responses
    cur3 = await db.execute(
        "SELECT * FROM responses WHERE run_id = ? AND query_id = ?", (run_id, query_id)
    )
    responses = {r["product"]: row_to_dict(r) for r in await cur3.fetchall()}

    # Verdicts
    verdicts = {}
    for product, resp in responses.items():
        cur4 = await db.execute(
            "SELECT v.*, a.assertion_text, a.level, a.dimension FROM verdicts v "
            "JOIN assertions a ON v.assertion_id = a.id "
            "WHERE v.response_id = ?",
            (resp["id"],)
        )
        verdicts[product] = [row_to_dict(r) for r in await cur4.fetchall()]

    # Pair result
    cur5 = await db.execute(
        "SELECT * FROM pair_results WHERE run_id = ? AND query_id = ?", (run_id, query_id)
    )
    pair = await cur5.fetchone()

    return {
        "query": row_to_dict(query),
        "assertions": assertions,
        "responses": responses,
        "verdicts": verdicts,
        "pair_result": row_to_dict(pair) if pair else None,
    }


# ── Queries CRUD ──────────────────────────────────────────────────────────────

@app.get("/api/queries")
async def list_queries(db=Depends(get_db)):
    cur = await db.execute(
        "SELECT q.*, COUNT(a.id) as assertion_count FROM queries q "
        "LEFT JOIN assertions a ON a.query_id = q.id GROUP BY q.id ORDER BY q.intent, q.domain"
    )
    rows = await cur.fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/api/queries/{query_id}")
async def get_query(query_id: str, db=Depends(get_db)):
    cur = await db.execute("SELECT * FROM queries WHERE id = ?", (query_id,))
    q = await cur.fetchone()
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    cur2 = await db.execute("SELECT * FROM assertions WHERE query_id = ?", (query_id,))
    assertions = [row_to_dict(r) for r in await cur2.fetchall()]
    return {**row_to_dict(q), "assertions": assertions}


# ── Key Findings ──────────────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/findings")
async def run_findings(run_id: str, db=Depends(get_db)):
    from openai import OpenAI
    oai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    # Gather summary
    cur = await db.execute(
        "SELECT pr.outcome, COUNT(*) as c FROM pair_results pr WHERE run_id=? GROUP BY outcome",
        (run_id,)
    )
    outcomes = {r["outcome"]: r["c"] for r in await cur.fetchall()}

    cur2 = await db.execute(
        "SELECT AVG(mindtrip_pass_rate) as mt, AVG(wanderboat_pass_rate) as wb FROM pair_results WHERE run_id=?",
        (run_id,)
    )
    avgs = row_to_dict(await cur2.fetchone())

    # Per-intent pivot
    cur3 = await db.execute(
        "SELECT q.intent, pr.outcome, pr.mindtrip_pass_rate, pr.wanderboat_pass_rate "
        "FROM pair_results pr JOIN queries q ON pr.query_id=q.id WHERE pr.run_id=?",
        (run_id,)
    )
    pivot_rows = await cur3.fetchall()
    intent_data: dict = {}
    for r in pivot_rows:
        iv = r["intent"]
        if iv not in intent_data:
            intent_data[iv] = {"mt": [], "wb": [], "outcomes": []}
        intent_data[iv]["mt"].append(r["mindtrip_pass_rate"])
        intent_data[iv]["wb"].append(r["wanderboat_pass_rate"])
        intent_data[iv]["outcomes"].append(r["outcome"])

    intent_summary = []
    for intent, d in intent_data.items():
        mt_avg = sum(d["mt"]) / len(d["mt"])
        wb_avg = sum(d["wb"]) / len(d["wb"])
        intent_summary.append({
            "intent": intent,
            "mt_pass_rate": round(mt_avg, 3),
            "wb_pass_rate": round(wb_avg, 3),
            "outcomes": {o: d["outcomes"].count(o) for o in set(d["outcomes"])},
        })

    # Sample verdict reasoning per intent
    cur4 = await db.execute(
        "SELECT q.intent, r.product, v.judge_reasoning, v.passed "
        "FROM verdicts v "
        "JOIN responses r ON v.response_id=r.id "
        "JOIN queries q ON r.query_id=q.id "
        "JOIN assertions a ON v.assertion_id=a.id "
        "WHERE r.run_id=? AND a.level='critical' AND v.passed=0 "
        "ORDER BY q.intent LIMIT 30",
        (run_id,)
    )
    failures = [dict(r) for r in await cur4.fetchall()]

    prompt = f"""You are analyzing the results of a head-to-head AI travel assistant evaluation: Mindtrip vs Wanderboat.

OVERALL RESULTS:
- Mindtrip wins: {outcomes.get('mindtrip_wins', 0)} queries
- Wanderboat wins: {outcomes.get('wanderboat_wins', 0)} queries
- Both pass: {outcomes.get('both_pass', 0)} queries
- Mindtrip avg pass rate: {round((avgs.get('mt') or 0)*100)}%
- Wanderboat avg pass rate: {round((avgs.get('wb') or 0)*100)}%

PER-INTENT BREAKDOWN:
{json.dumps(intent_summary, indent=2)}

SAMPLE FAILURE REASONING (judge explanations for failed assertions):
{json.dumps(failures[:20], indent=2)}

Generate a Key Findings report as a JSON array of 4-6 findings. Each finding must be a JSON object with:
- "title": short headline (max 10 words)
- "winner": "mindtrip" | "wanderboat" | "neutral"
- "intent": the relevant intent bucket or "Overall"
- "summary": 2-3 sentence explanation of WHY one product outperforms the other on this dimension, citing specific patterns from the judge reasoning
- "evidence": one concrete example phrase from the judge reasoning that illustrates the finding

Return a JSON object with a single key "findings" whose value is the array. Example shape:
{{"findings": [{{"title": "...", "winner": "mindtrip", "intent": "Transactional", "summary": "...", "evidence": "..."}}]}}"""

    loop = asyncio.get_event_loop()
    def call_openai():
        result = oai.chat.completions.create(
            model="gpt-4o",
            max_tokens=1400,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = result.choices[0].message.content.strip()
        parsed = json.loads(text)
        # Handle: {"findings": [...]} or {"0": {...}, "1": {...}} or direct array
        if isinstance(parsed, list):
            return parsed
        if "findings" in parsed and isinstance(parsed["findings"], list):
            return parsed["findings"]
        # Fallback: values of the dict if they look like finding objects
        values = list(parsed.values())
        if values and isinstance(values[0], dict) and "title" in values[0]:
            return values
        # Single finding returned as flat object
        if "title" in parsed:
            return [parsed]
        return values

    findings = await loop.run_in_executor(None, call_openai)
    return {"findings": findings, "outcomes": outcomes, "avgs": avgs}


# ── Misc ──────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}

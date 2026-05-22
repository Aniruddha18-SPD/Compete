"""
Parallel eval runner.

For a given prompt:
  1. Fires both site scrapers concurrently (browser-based adapter OR HTTP client
     once API endpoints are known from sniff_api.py).
  2. Scores the two responses with the weighted rubric from compete_eval.py
     using an LLM-as-judge (Claude via the autoevals Battle scorer).
  3. Writes a structured result to SQLite (evals + runs tables).

Usage (CLI):
    python -m compete.runner "Best beaches in Thailand" --bucket personalized
    python -m compete.runner --batch               # runs all DATASET prompts
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Load .env if present so ANTHROPIC_API_KEY and SCRAPER_* are available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from scraper.core.database import init_db, save_result, save_eval
from scraper.core.base_adapter import ScrapeResult
from compete.rubric import RUBRIC, DATASET


@dataclass
class EvalResult:
    prompt: str
    bucket: str | None
    mindtrip_response: str | None
    wanderboat_response: str | None
    mindtrip_error: str | None
    wanderboat_error: str | None
    mindtrip_duration_ms: int
    wanderboat_duration_ms: int
    winner: str | None
    scores: dict
    judge_reasoning: str | None


async def _scrape_one(site: str, prompt: str) -> tuple[ScrapeResult, int]:
    """Run a scrape for one site. Wanderboat uses the pure HTTP path; others use the browser."""
    if site == "wanderboat":
        from scraper.adapters.wanderboat_http import scrape as wb_scrape
        result = await wb_scrape(prompt)
    else:
        import os
        from scraper.adapters import REGISTRY
        from scraper.core.runner import run_scrape

        adapter_class = REGISTRY[site]
        credentials = {
            "email": os.environ.get("SCRAPER_EMAIL", ""),
            "password": os.environ.get("SCRAPER_PASSWORD", ""),
        }
        result = await run_scrape(
            adapter_class=adapter_class,
            credentials=credentials,
            prompt=prompt,
            headless=True,
        )
    run_id = save_result(result)
    return result, run_id


async def _judge(prompt: str, mindtrip_resp: str, wanderboat_resp: str, bucket: str | None) -> dict:
    """
    Score both responses using Claude as the LLM judge.
    Returns {winner, scores, reasoning} where scores includes per-axis breakdowns.
    Falls back gracefully if ANTHROPIC_API_KEY is missing.
    """
    import os
    # Reload .env dynamically — handles the case where the server was started
    # before .env was created and the key wasn't in the environment at import time.
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env", override=False)
    except ImportError:
        pass
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "winner": None,
            "scores": {},
            "reasoning": "[scoring unavailable: ANTHROPIC_API_KEY not set in .env]",
        }

    rubric_text = "\n".join(
        f"- {axis} (weight {spec['weight']}): {spec['definition']}"
        for axis, spec in RUBRIC.items()
    )

    system = (
        "You are an expert travel-AI product evaluator. "
        "You score responses objectively on the given rubric and return only valid JSON."
    )

    user = f"""Compare two travel-AI responses to this prompt: "{prompt}"
Capability bucket: {bucket or 'general'}

== RESPONSE A (Mindtrip) ==
{mindtrip_resp[:3000]}

== RESPONSE B (Wanderboat) ==
{wanderboat_resp[:3000]}

Score each response on these axes from 1–5:
{rubric_text}

Compute the weighted score for each:
  weighted = actionability*0.30 + specificity*0.25 + personalization*0.25 + trustworthiness*0.20

Pick winner = "mindtrip" if A's weighted score exceeds B's by more than 0.5, "wanderboat" if B exceeds A by more than 0.5, otherwise "tie".

Reply with ONLY this JSON (no markdown, no extra text):
{{
  "winner": "mindtrip"|"wanderboat"|"tie",
  "score_mindtrip": <weighted float>,
  "score_wanderboat": <weighted float>,
  "axes": {{
    "actionability":    {{"mindtrip": <1-5>, "wanderboat": <1-5>}},
    "specificity":      {{"mindtrip": <1-5>, "wanderboat": <1-5>}},
    "personalization":  {{"mindtrip": <1-5>, "wanderboat": <1-5>}},
    "trustworthiness":  {{"mindtrip": <1-5>, "wanderboat": <1-5>}}
  }},
  "reasoning": "<2-3 sentence explanation>"
}}"""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)

        # Retry up to 4 times with exponential backoff for 529 overloaded errors.
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                msg = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=512,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                break
            except anthropic.APIStatusError as exc:
                if exc.status_code == 529 and attempt < 3:
                    wait = 2 ** attempt * 10  # 10s, 20s, 40s
                    print(f"[judge] Anthropic overloaded (529), retrying in {wait}s "
                          f"(attempt {attempt + 1}/4)...")
                    await asyncio.sleep(wait)
                    last_exc = exc
                else:
                    raise
        else:
            raise last_exc  # type: ignore[misc]

        raw = msg.content[0].text.strip()
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        axes = data.get("axes", {})
        return {
            "winner": data.get("winner"),
            "scores": {
                "mindtrip":        data.get("score_mindtrip"),
                "wanderboat":      data.get("score_wanderboat"),
                "actionability":   axes.get("actionability", {}).get("mindtrip"),
                "specificity":     axes.get("specificity",   {}).get("mindtrip"),
                "personalization": axes.get("personalization", {}).get("mindtrip"),
                "trustworthiness": axes.get("trustworthiness", {}).get("mindtrip"),
                # Wanderboat per-axis (stored in reasoning JSON for dashboard)
                "wb_actionability":   axes.get("actionability", {}).get("wanderboat"),
                "wb_specificity":     axes.get("specificity",   {}).get("wanderboat"),
                "wb_personalization": axes.get("personalization", {}).get("wanderboat"),
                "wb_trustworthiness": axes.get("trustworthiness", {}).get("wanderboat"),
            },
            "reasoning": json.dumps({
                "summary": data.get("reasoning", ""),
                "axes": axes,
                "score_mindtrip": data.get("score_mindtrip"),
                "score_wanderboat": data.get("score_wanderboat"),
            }),
        }
    except Exception as exc:
        return {
            "winner": None,
            "scores": {},
            "reasoning": f"[scoring error: {exc}]",
        }


async def run_eval(
    prompt: str,
    bucket: str | None = None,
    headless: bool = True,
) -> EvalResult:
    init_db()

    print(f"\n[eval] Prompt: {prompt!r}  bucket={bucket}")
    print("[eval] Scraping both sites in parallel ...")

    t0 = time.monotonic()
    (mt_result, mt_run_id), (wb_result, wb_run_id) = await asyncio.gather(
        _scrape_one("mindtrip", prompt),
        _scrape_one("wanderboat", prompt),
    )

    print(f"[eval] MindTrip   {'OK' if not mt_result.error else 'ERR'} "
          f"({mt_result.duration_ms}ms)")
    print(f"[eval] Wanderboat {'OK' if not wb_result.error else 'ERR'} "
          f"({wb_result.duration_ms}ms)")

    mt_resp = mt_result.response or ""
    wb_resp = wb_result.response or ""

    judge = {"winner": None, "scores": {}, "reasoning": None}
    if mt_resp and wb_resp:
        print("[eval] Judging responses ...")
        judge = await _judge(prompt, mt_resp, wb_resp, bucket)
        print(f"[eval] Winner: {judge['winner']}")

    save_eval(
        prompt=prompt,
        bucket=bucket,
        mindtrip_run_id=mt_run_id,
        wanderboat_run_id=wb_run_id,
        winner=judge["winner"],
        scores=judge["scores"],
        judge_reasoning=judge["reasoning"],
    )

    return EvalResult(
        prompt=prompt,
        bucket=bucket,
        mindtrip_response=mt_resp or None,
        wanderboat_response=wb_resp or None,
        mindtrip_error=mt_result.error,
        wanderboat_error=wb_result.error,
        mindtrip_duration_ms=mt_result.duration_ms,
        wanderboat_duration_ms=wb_result.duration_ms,
        winner=judge["winner"],
        scores=judge["scores"],
        judge_reasoning=judge["reasoning"],
    )


async def run_batch() -> list[EvalResult]:
    """Run all prompts from the DATASET in compete_eval.py sequentially."""
    results = []
    for row in DATASET:
        result = await run_eval(row["input"], bucket=row.get("bucket"))
        results.append(result)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compete eval runner")
    parser.add_argument("prompt", nargs="?", help="Single prompt to evaluate")
    parser.add_argument("--bucket", default=None, help="Bucket label (transactional, itinerary…)")
    parser.add_argument("--batch", action="store_true", help="Run all DATASET prompts")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    if args.batch:
        results = asyncio.run(run_batch())
        print(f"\n[done] {len(results)} evals complete")
    elif args.prompt:
        result = asyncio.run(run_eval(args.prompt, bucket=args.bucket))
        print(json.dumps({
            "winner": result.winner,
            "scores": result.scores,
            "mindtrip": (result.mindtrip_response or "")[:300],
            "wanderboat": (result.wanderboat_response or "")[:300],
        }, indent=2))
    else:
        parser.print_help()

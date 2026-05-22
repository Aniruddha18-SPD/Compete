import sqlite3
from pathlib import Path

from scraper.core.base_adapter import ScrapeResult

DB_PATH = Path("data/runs.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    site        TEXT    NOT NULL,
    prompt      TEXT    NOT NULL,
    response    TEXT,
    model_hint  TEXT,
    tokens_hint INTEGER,
    error       TEXT,
    duration_ms INTEGER,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_runs_site       ON runs(site);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);

CREATE TABLE IF NOT EXISTS evals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt              TEXT    NOT NULL,
    bucket              TEXT,
    mindtrip_run_id     INTEGER REFERENCES runs(id),
    wanderboat_run_id   INTEGER REFERENCES runs(id),
    winner              TEXT,
    score_mindtrip      REAL,
    score_wanderboat    REAL,
    score_actionability REAL,
    score_specificity   REAL,
    score_personalization REAL,
    score_trustworthiness REAL,
    judge_reasoning     TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_evals_created_at ON evals(created_at);
"""


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(_SCHEMA)


def save_result(result: ScrapeResult) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO runs
               (site, prompt, response, model_hint, tokens_hint, error, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                result.site,
                result.prompt,
                result.response,
                result.model_hint,
                result.tokens_hint,
                result.error,
                result.duration_ms,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def save_eval(
    prompt: str,
    bucket: str | None,
    mindtrip_run_id: int | None,
    wanderboat_run_id: int | None,
    winner: str | None,
    scores: dict,
    judge_reasoning: str | None,
) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO evals
               (prompt, bucket, mindtrip_run_id, wanderboat_run_id, winner,
                score_mindtrip, score_wanderboat,
                score_actionability, score_specificity,
                score_personalization, score_trustworthiness,
                judge_reasoning)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                prompt, bucket, mindtrip_run_id, wanderboat_run_id, winner,
                scores.get("mindtrip"), scores.get("wanderboat"),
                scores.get("actionability"), scores.get("specificity"),
                scores.get("personalization"), scores.get("trustworthiness"),
                judge_reasoning,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def list_evals(limit: int = 50) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(
            "SELECT * FROM evals ORDER BY created_at DESC LIMIT ?", (limit,)
        )]


def get_eval_with_responses(eval_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT e.*,
                      mt.response   AS mindtrip_response,
                      mt.duration_ms AS mindtrip_duration_ms,
                      mt.error      AS mindtrip_error,
                      wb.response   AS wanderboat_response,
                      wb.duration_ms AS wanderboat_duration_ms,
                      wb.error      AS wanderboat_error
               FROM evals e
               LEFT JOIN runs mt ON e.mindtrip_run_id   = mt.id
               LEFT JOIN runs wb ON e.wanderboat_run_id = wb.id
               WHERE e.id = ?""",
            (eval_id,),
        ).fetchone()
        return dict(row) if row else None


def list_evals_with_responses(limit: int = 50) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT e.*,
                      mt.response   AS mindtrip_response,
                      mt.duration_ms AS mindtrip_duration_ms,
                      mt.error      AS mindtrip_error,
                      wb.response   AS wanderboat_response,
                      wb.duration_ms AS wanderboat_duration_ms,
                      wb.error      AS wanderboat_error
               FROM evals e
               LEFT JOIN runs mt ON e.mindtrip_run_id   = mt.id
               LEFT JOIN runs wb ON e.wanderboat_run_id = wb.id
               ORDER BY e.created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_runs(site: str | None = None, limit: int = 50) -> list[dict]:
    query = "SELECT * FROM runs"
    params: list = []
    if site:
        query += " WHERE site = ?"
        params.append(site)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query, params)]

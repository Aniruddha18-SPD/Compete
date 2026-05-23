import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "compete.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS queries (
            id TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            intent TEXT NOT NULL,
            domain TEXT NOT NULL,
            query_attrs TEXT DEFAULT '{}',
            persona_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assertions (
            id TEXT PRIMARY KEY,
            query_id TEXT REFERENCES queries(id),
            assertion_text TEXT NOT NULL,
            level TEXT NOT NULL,
            dimension TEXT NOT NULL,
            assertion_type TEXT DEFAULT 'soft_binary',
            check_pattern TEXT
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            run_name TEXT,
            query_set_version TEXT DEFAULT 'v1',
            status TEXT DEFAULT 'pending',
            run_type TEXT DEFAULT 'mock',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS responses (
            id TEXT PRIMARY KEY,
            run_id TEXT REFERENCES runs(id),
            query_id TEXT REFERENCES queries(id),
            product TEXT NOT NULL,
            response_text TEXT NOT NULL,
            response_metadata TEXT DEFAULT '{}',
            captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            capture_method TEXT DEFAULT 'mock'
        );

        CREATE TABLE IF NOT EXISTS verdicts (
            id TEXT PRIMARY KEY,
            response_id TEXT REFERENCES responses(id),
            assertion_id TEXT REFERENCES assertions(id),
            passed INTEGER NOT NULL,
            judge_reasoning TEXT,
            judge_confidence REAL,
            judged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pair_results (
            id TEXT PRIMARY KEY,
            run_id TEXT REFERENCES runs(id),
            query_id TEXT REFERENCES queries(id),
            mindtrip_pass_rate REAL,
            wanderboat_pass_rate REAL,
            outcome TEXT,
            outcome_severity TEXT DEFAULT 'critical'
        );
        """)
        await db.commit()

    # Safe migrations for existing databases
    async with aiosqlite.connect(DB_PATH) as db:
        for stmt in [
            "ALTER TABLE runs ADD COLUMN run_type TEXT DEFAULT 'mock'",
            "ALTER TABLE assertions ADD COLUMN assertion_type TEXT DEFAULT 'soft_binary'",
            "ALTER TABLE assertions ADD COLUMN check_pattern TEXT",
        ]:
            try:
                await db.execute(stmt)
                await db.commit()
            except Exception:
                pass  # Column already exists

"""Load eval dataset from compete_travel_eval_final.py into the database."""
import asyncio
import json
import sys
import uuid
from pathlib import Path

import aiosqlite
from database import init_db, DB_PATH

# Add repo root so we can import compete_travel_eval_final
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from compete_travel_eval_final import DATASET


async def load_seed():
    await init_db()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM queries LIMIT 1")
        first = await cur.fetchone()

        # Reseed if DB is empty or has old data (not from DATASET)
        if first and first[0] == DATASET[0]["id"]:
            count = (await (await db.execute("SELECT COUNT(*) FROM queries")).fetchone())[0]
            print(f"Already seeded ({count} queries from compete_travel_eval_final). Skipping.")
            return

        if first:
            print("Old seed data detected — clearing and reseeding from compete_travel_eval_final.")
            await db.execute("DELETE FROM assertions")
            await db.execute("DELETE FROM queries")
            await db.commit()

        for q in DATASET:
            await db.execute(
                "INSERT INTO queries (id, query_text, intent, domain, query_attrs, persona_context) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    q["id"],
                    q["input"],
                    q["query_type"],
                    q["difficulty"],
                    json.dumps({}),
                    q.get("user_intent", ""),
                ),
            )
            for a in q["assertions"]:
                await db.execute(
                    "INSERT INTO assertions "
                    "(id, query_id, assertion_text, level, dimension, assertion_type, check_pattern) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        a["id"],
                        q["id"],
                        a["description"],
                        "critical" if a["critical"] else "expected",
                        a["capability"],
                        a["type"],
                        a["check"],
                    ),
                )

        await db.commit()
        print(f"Loaded {len(DATASET)} queries from compete_travel_eval_final.")


async def create_mock_run():
    """Create a run with mock responses from the fixture file."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM runs WHERE run_name LIKE 'Mock Run%'")
        count = (await cur.fetchone())[0]
        run_name = f"Mock Run v{count + 1}"

        run_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO runs (id, run_name, status) VALUES (?, ?, ?)",
            (run_id, run_name, "capturing"),
        )

        seed_dir = Path(__file__).parent / "seed"
        mock_file = seed_dir / "mock_responses.json"
        if mock_file.exists():
            with open(mock_file) as f:
                mock_data = json.load(f)
            for query_id, products in mock_data.items():
                for product, text in products.items():
                    resp_id = str(uuid.uuid4())
                    await db.execute(
                        "INSERT INTO responses (id, run_id, query_id, product, response_text, capture_method) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (resp_id, run_id, query_id, product, text, "mock"),
                    )

        await db.execute("UPDATE runs SET status = 'judging' WHERE id = ?", (run_id,))
        await db.commit()
        print(f"Created mock run: {run_id}.")
        return run_id


if __name__ == "__main__":
    asyncio.run(load_seed())

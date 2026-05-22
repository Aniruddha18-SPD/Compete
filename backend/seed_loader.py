"""Load queries.yaml and mock_responses.json into the database."""
import asyncio
import json
import uuid
import yaml
from pathlib import Path
from database import init_db, DB_PATH
import aiosqlite

SEED_DIR = Path(__file__).parent / "seed"


async def load_seed():
    await init_db()

    async with aiosqlite.connect(DB_PATH) as db:
        # Check if already seeded
        cur = await db.execute("SELECT COUNT(*) FROM queries")
        count = (await cur.fetchone())[0]
        if count > 0:
            print(f"Already seeded ({count} queries). Skipping.")
            return

        with open(SEED_DIR / "queries.yaml") as f:
            data = yaml.safe_load(f)

        for q in data["queries"]:
            await db.execute(
                "INSERT INTO queries (id, query_text, intent, domain, query_attrs, persona_context) VALUES (?, ?, ?, ?, ?, ?)",
                (q["id"], q["query_text"], q["intent"], q["domain"],
                 json.dumps(q.get("query_attrs", {})), q.get("persona_context"))
            )
            for a in q.get("assertions", []):
                await db.execute(
                    "INSERT INTO assertions (id, query_id, assertion_text, level, dimension) VALUES (?, ?, ?, ?, ?)",
                    (a["id"], q["id"], a["text"], a["level"], a["dimension"])
                )

        await db.commit()
        print(f"Loaded {len(data['queries'])} queries.")


async def create_mock_run():
    """Create a run with mock responses from the fixture file."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM runs WHERE run_name LIKE 'Mock Run%'")
        count = (await cur.fetchone())[0]
        run_name = f"Mock Run v{count + 1}"

        run_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO runs (id, run_name, status) VALUES (?, ?, ?)",
            (run_id, run_name, "capturing")
        )

        with open(SEED_DIR / "mock_responses.json") as f:
            mock_data = json.load(f)

        for query_id, products in mock_data.items():
            for product, text in products.items():
                resp_id = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO responses (id, run_id, query_id, product, response_text, capture_method) VALUES (?, ?, ?, ?, ?, ?)",
                    (resp_id, run_id, query_id, product, text, "mock")
                )

        await db.execute("UPDATE runs SET status = 'judging' WHERE id = ?", (run_id,))
        await db.commit()
        print(f"Created mock run: {run_id} with {len(mock_data)} query pairs.")
        return run_id


if __name__ == "__main__":
    asyncio.run(load_seed())
    asyncio.run(create_mock_run())

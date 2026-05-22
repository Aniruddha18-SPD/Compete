import argparse
import asyncio
import json
import os


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Travel AI scraper — logs in, sends a prompt, saves the response."
    )
    p.add_argument("site", choices=["mindtrip", "wanderboat"], help="Target site")
    p.add_argument("prompt", nargs="?", default="", help="Prompt text to send")
    p.add_argument("--email",    help="Login email    (or set SCRAPER_EMAIL)")
    p.add_argument("--password", help="Login password (or set SCRAPER_PASSWORD)")
    p.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        default=True,
        help="Show the browser window (useful for debugging selectors)",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Pause with Playwright Inspector before closing (use with --no-headless to inspect DOM)",
    )
    p.add_argument(
        "--list-runs",
        action="store_true",
        help="Print recent runs from the database and exit",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=20,
        help="How many runs to show with --list-runs (default: 20)",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()

    if args.list_runs:
        from scraper.core.database import init_db, list_runs
        init_db()
        runs = list_runs(site=args.site, limit=args.limit)
        print(json.dumps(runs, indent=2, ensure_ascii=False))
        return

    if not args.prompt:
        build_parser().error("prompt is required unless --list-runs is set")

    from scraper.adapters import REGISTRY

    adapter_class = REGISTRY[args.site]
    email    = args.email    or os.environ.get("SCRAPER_EMAIL", "")
    password = args.password or os.environ.get("SCRAPER_PASSWORD", "")

    if getattr(adapter_class, "REQUIRES_LOGIN", True) and (not email or not password):
        build_parser().error(
            "Provide --email/--password or set SCRAPER_EMAIL/SCRAPER_PASSWORD"
        )
    from scraper.core.runner import run_scrape

    result = asyncio.run(
        run_scrape(
            adapter_class=adapter_class,
            credentials={"email": email, "password": password},
            prompt=args.prompt,
            headless=args.headless,
            debug=args.debug,
        )
    )

    if result.error:
        print(f"[ERROR] {result.error}")
        raise SystemExit(1)

    print(f"[OK] site={result.site}  duration={result.duration_ms}ms")
    print()
    print(result.response)


if __name__ == "__main__":
    main()

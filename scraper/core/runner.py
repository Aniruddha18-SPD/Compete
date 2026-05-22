import time

from scraper.core.base_adapter import BaseSiteAdapter, ScrapeResult
from scraper.core.browser import create_context
from scraper.core.database import init_db, save_result


async def run_scrape(
    adapter_class: type[BaseSiteAdapter],
    credentials: dict,
    prompt: str,
    headless: bool = True,
    debug: bool = False,
) -> ScrapeResult:
    init_db()
    playwright, browser, context = await create_context(
        session_file=adapter_class.SESSION_FILE,
        headless=headless,
    )
    page = await context.new_page()
    adapter = adapter_class(page, context, credentials)

    start = time.monotonic()
    error: str | None = None
    response: str | None = None

    try:
        await adapter.ensure_logged_in()
        await adapter.navigate_to_chat()
        await adapter.send_prompt(prompt)
        await adapter.wait_for_response_complete()
        response = await adapter.extract_response()
    except Exception as exc:
        error = str(exc)
        print(f"[DEBUG] Error at step: {exc}")
    finally:
        if debug:
            print("[DEBUG] Pausing — inspect the browser, then click Resume in the Playwright Inspector.")
            await page.pause()
        duration_ms = int((time.monotonic() - start) * 1000)
        await context.close()
        await browser.close()
        await playwright.stop()

    result = ScrapeResult(
        site=adapter_class.SITE_NAME,
        prompt=prompt,
        response=response,
        model_hint=None,
        tokens_hint=None,
        error=error,
        duration_ms=duration_ms,
    )
    save_result(result)
    return result

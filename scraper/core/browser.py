import os
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Removes the most common bot-detection signals Cloudflare and similar services check
_ANTI_DETECT_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]


async def create_context(
    session_file: str | None = None,
    headless: bool = True,
    channel: str | None = "chrome",
) -> tuple[Playwright, Browser, BrowserContext]:
    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.launch(
            headless=headless,
            channel=channel,
            args=_ANTI_DETECT_ARGS,
        )
    except Exception:
        # Fall back to bundled Chromium if real Chrome is not installed
        browser = await playwright.chromium.launch(
            headless=headless,
            args=_ANTI_DETECT_ARGS,
        )

    context_kwargs: dict = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": _USER_AGENT,
    }
    if session_file and os.path.exists(session_file):
        context_kwargs["storage_state"] = session_file

    context = await browser.new_context(**context_kwargs)
    # Hide the `navigator.webdriver` flag that Cloudflare checks
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return playwright, browser, context

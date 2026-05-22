import asyncio

from playwright.async_api import Page


async def wait_for_element_hidden(
    page: Page,
    selector: str,
    timeout_ms: int = 120_000,
) -> None:
    """Wait until `selector` disappears or is hidden — best for 'Stop generating' buttons."""
    await page.wait_for_selector(selector, state="hidden", timeout=timeout_ms)


async def wait_for_send_button_re_enabled(
    page: Page,
    send_button_selector: str,
    timeout_ms: int = 120_000,
) -> None:
    """Wait for the send button to become enabled again after submission."""
    await page.wait_for_selector(
        f"{send_button_selector}:not([disabled])",
        timeout=timeout_ms,
    )


async def wait_for_network_idle_after_submit(
    page: Page,
    url_pattern: str,
    timeout_ms: int = 120_000,
) -> None:
    """Wait for the streaming fetch/SSE request to close (fires when stream ends)."""
    async with page.expect_response(
        lambda r: url_pattern in r.url,
        timeout=timeout_ms,
    ) as resp_info:
        pass
    await resp_info.value


async def wait_for_dom_stable(
    page: Page,
    selector: str,
    stable_duration_ms: int = 1500,
    poll_interval_ms: int = 300,
    timeout_ms: int = 120_000,
) -> None:
    """
    Poll `selector` text content every poll_interval_ms.
    When content stops changing for stable_duration_ms, generation is considered done.
    Universal fallback when no cleaner signal is available.
    """
    elapsed = 0
    stable_for = 0
    last_text = ""

    while elapsed < timeout_ms:
        try:
            el = page.locator(selector)
            current_text = await el.inner_text()
        except Exception:
            current_text = last_text

        if current_text == last_text:
            stable_for += poll_interval_ms
            if stable_for >= stable_duration_ms:
                return
        else:
            stable_for = 0
            last_text = current_text

        await asyncio.sleep(poll_interval_ms / 1000)
        elapsed += poll_interval_ms

    raise TimeoutError(
        f"DOM did not stabilize on '{selector}' within {timeout_ms}ms"
    )

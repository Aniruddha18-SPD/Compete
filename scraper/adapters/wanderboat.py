"""
Wanderboat adapter — selectors confirmed via codegen + DevTools inspection.
"""

from scraper.core.base_adapter import BaseSiteAdapter
from scraper.utils.wait_helpers import wait_for_dom_stable, wait_for_send_button_re_enabled


class WanderboatAdapter(BaseSiteAdapter):
    SITE_NAME      = "wanderboat"
    SESSION_FILE   = "sessions/wanderboat_session.json"
    REQUIRES_LOGIN = False

    # Send button: disabled while streaming, re-enables when done
    _SEND_BUTTON = "button[aria-label='send-button']"
    # Response container: the prose div wrapping each AI reply
    _AI_MESSAGE  = "div.prose.max-w-none"

    def _chat_url(self) -> str:
        return "https://wanderboat.ai/chat"

    async def is_logged_in(self) -> bool:
        # Wanderboat allows anonymous chat — always return True to skip login
        return True

    async def login(self) -> None:
        pass

    async def navigate_to_chat(self) -> None:
        await self.page.goto("https://wanderboat.ai/chat")
        await self.page.get_by_role("textbox", name="input-textarea").wait_for(timeout=20_000)

    async def send_prompt(self, prompt: str) -> None:
        chat_input = self.page.get_by_role("textbox", name="input-textarea")
        await chat_input.fill(prompt)
        await chat_input.press("Enter")

    async def wait_for_response_complete(self) -> None:
        try:
            await wait_for_send_button_re_enabled(self.page, self._SEND_BUTTON, timeout_ms=120_000)
        except Exception:
            await wait_for_dom_stable(self.page, self._AI_MESSAGE, stable_duration_ms=2000)

    async def extract_response(self) -> str:
        el = self.page.locator(self._AI_MESSAGE).last
        return (await el.inner_text()).strip()

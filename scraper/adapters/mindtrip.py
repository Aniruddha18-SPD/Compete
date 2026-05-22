"""
MindTrip adapter — selectors confirmed via `playwright codegen` and DevTools inspection.

Token lifecycle:
  mindtrip.auth_token  — short-lived (~hours); auto-refreshed by the React app
                         if mindtrip.refresh_token is still valid.
  mindtrip.refresh_token — long-lived (~1 year); only needs full re-login when expired.
"""

import json
import time
from pathlib import Path

from scraper.core.base_adapter import BaseSiteAdapter
from scraper.utils.wait_helpers import wait_for_dom_stable, wait_for_send_button_re_enabled


class MindTripAdapter(BaseSiteAdapter):
    SITE_NAME = "mindtrip"
    SESSION_FILE = "sessions/mindtrip_session.json"

    _AI_MESSAGE = ".e2e\\:message-bot"
    _SEND_BUTTON = "button[aria-label='Send message']"

    def _chat_url(self) -> str:
        return "https://mindtrip.ai"

    def _cookie_expiry(self, name: str) -> float:
        """Return the expiry unix-timestamp for a named cookie in the session file, or 0."""
        sf = Path(self.SESSION_FILE)
        if not sf.exists():
            return 0.0
        try:
            data = json.loads(sf.read_text())
            c = next((c for c in data.get("cookies", []) if c["name"] == name), None)
            return float(c["expires"]) if c and c.get("expires", -1) > 0 else 0.0
        except Exception:
            return 0.0

    def _refresh_token_expired(self) -> bool:
        exp = self._cookie_expiry("mindtrip.refresh_token")
        return exp == 0.0 or exp < time.time()

    async def ensure_logged_in(self) -> None:
        sf = Path(self.SESSION_FILE)

        # If the long-lived refresh token is gone/expired, we need full re-login
        if self._refresh_token_expired():
            if sf.exists():
                sf.unlink()
            if not self.credentials.get("email"):
                raise RuntimeError(
                    "MindTrip session fully expired. Re-login at http://localhost:8765/login "
                    "or set SCRAPER_EMAIL + SCRAPER_PASSWORD in .env for headless re-login."
                )
        # auth_token may be expired but refresh_token is valid:
        # the React app will auto-refresh the token when the page loads.
        # is_logged_in() waits up to 20 s for the chat input — enough time for auto-refresh.

        await self.page.goto(self._chat_url())
        if sf.exists() and await self.is_logged_in():
            # Save session every time to capture any freshly auto-refreshed auth_token
            sf.parent.mkdir(parents=True, exist_ok=True)
            await self.context.storage_state(path=str(sf))
            return

        # Not logged in — try headless login with credentials
        if not self.credentials.get("email"):
            raise RuntimeError(
                "MindTrip: not logged in and no credentials available. "
                "Re-login at http://localhost:8765/login or set SCRAPER_EMAIL + SCRAPER_PASSWORD in .env."
            )
        await self.login()
        sf.parent.mkdir(parents=True, exist_ok=True)
        await self.context.storage_state(path=str(sf))

    async def is_logged_in(self) -> bool:
        # The chat input only appears after a successful login (or auto token refresh).
        # 20 s gives the React app enough time to call the refresh endpoint and re-render.
        try:
            await self.page.get_by_role("textbox", name="Ask anything").wait_for(
                state="visible", timeout=20_000
            )
            return True
        except Exception:
            return False

    async def login(self) -> None:
        await self.page.goto("https://mindtrip.ai")
        await self.page.get_by_role("button", name="Log in").click()
        await self.page.get_by_role("textbox", name="Email").fill(self.credentials["email"])
        await self.page.get_by_role("button", name="Continue", exact=True).click()
        await self.page.get_by_role("textbox", name="Password").fill(self.credentials["password"])
        await self.page.get_by_role("button", name="Continue").click()
        # Optional post-login modal
        try:
            cont = self.page.get_by_role("button", name="Continue")
            await cont.wait_for(state="visible", timeout=3_000)
            await cont.click()
        except Exception:
            pass
        await self.page.get_by_role("textbox", name="Ask anything").wait_for(timeout=30_000)

    async def navigate_to_chat(self) -> None:
        # ensure_logged_in() already landed on the homepage and confirmed the chat input
        # is visible — skip the redundant reload.
        chat_input = self.page.get_by_role("textbox", name="Ask anything")
        try:
            await chat_input.wait_for(state="visible", timeout=2_000)
            return
        except Exception:
            pass
        await self.page.goto("https://mindtrip.ai")
        await chat_input.wait_for(timeout=30_000)

    async def send_prompt(self, prompt: str) -> None:
        chat_input = self.page.get_by_role("textbox", name="Ask anything")
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

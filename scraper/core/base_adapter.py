import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from playwright.async_api import BrowserContext, Page


@dataclass
class ScrapeResult:
    site: str
    prompt: str
    response: str | None
    model_hint: str | None
    tokens_hint: int | None
    error: str | None
    duration_ms: int


class BaseSiteAdapter(ABC):
    """
    Subclass one per target site. The runner calls these methods in order:
      1. ensure_logged_in()
      2. navigate_to_chat()
      3. send_prompt(prompt)
      4. wait_for_response_complete()
      5. extract_response()
    """

    SITE_NAME: str = ""
    SESSION_FILE: str = ""

    def __init__(self, page: Page, context: BrowserContext, credentials: dict) -> None:
        self.page = page
        self.context = context
        self.credentials = credentials

    @abstractmethod
    async def is_logged_in(self) -> bool: ...

    @abstractmethod
    async def login(self) -> None: ...

    @abstractmethod
    async def navigate_to_chat(self) -> None: ...

    @abstractmethod
    async def send_prompt(self, prompt: str) -> None: ...

    @abstractmethod
    async def wait_for_response_complete(self) -> None: ...

    @abstractmethod
    async def extract_response(self) -> str: ...

    @abstractmethod
    def _chat_url(self) -> str: ...

    async def ensure_logged_in(self) -> None:
        """Load saved session if present; fall back to full login and save a fresh session."""
        await self.page.goto(self._chat_url())
        if os.path.exists(self.SESSION_FILE) and await self.is_logged_in():
            return
        await self.login()
        os.makedirs(os.path.dirname(self.SESSION_FILE), exist_ok=True)
        await self.context.storage_state(path=self.SESSION_FILE)

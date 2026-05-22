"""
Pure-HTTP Wanderboat scraper — no browser required.

Flow:
  1. Generate a random device ID (x-wb-user-id header)
  2. GET /v2/oauth/anonymous → anonymous JWT
  3. POST /v1/chat/message with that token → SSE stream
  4. Parse SSE: streaming_message events carry payload.streaming_string,
     which is JSON {"message": "<accumulated text>"}. Take the last one.
"""

import json
import re
import time
import uuid

import httpx

from scraper.core.base_adapter import ScrapeResult

SITE_NAME = "wanderboat"

_ANON_URL = "https://api.wanderboat.ai/v2/oauth/anonymous"
_CHAT_URL = "https://api.wanderboat.ai/v1/chat/message"


def _gen_device_id() -> str:
    h = uuid.uuid4().hex
    ts = int(time.time() * 1000)
    return f"$device:{h[:14]}-{h[14:29]}-{ts}-{ts % 1_000_000}-{h[:14]}"


def _base_headers(device_id: str) -> dict:
    return {
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        ),
        "referer": "https://wanderboat.ai/",
        "x-wb-user-id": device_id,
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }


_INTERNAL_LINK_RE = re.compile(r'\[([^\]]+)\]\(\{[^)]*\}\)', re.DOTALL)
_INSERT_RE = re.compile(r'\[insert_[^\]]+\]\([^)]*\)', re.DOTALL)


def _clean(text: str) -> str:
    """Strip Wanderboat's internal place-link and multimedia markers."""
    text = _INTERNAL_LINK_RE.sub(r'\1', text)
    text = _INSERT_RE.sub('', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _build_body(prompt: str) -> dict:
    return {
        "mode": "inspur",
        "message": prompt,
        "streaming": True,
        "use_v2": True,
        "local_tz": "America/Los_Angeles",
        "user_language": "English",
        "parameters": {
            "marg": True,
            "newaf": True,
            "two_stage": True,
            "inline_annotation": True,
            "mobile_app": False,
        },
    }


async def scrape(prompt: str) -> ScrapeResult:
    """Fetch a Wanderboat response via pure HTTP. Returns a ScrapeResult."""
    t0 = time.monotonic()
    error: str | None = None
    response: str | None = None

    try:
        device_id = _gen_device_id()
        base = _base_headers(device_id)

        async with httpx.AsyncClient(http2=True, follow_redirects=True) as client:
            # Step 1: anonymous JWT
            auth_resp = await client.get(_ANON_URL, headers=base, timeout=15)
            auth_resp.raise_for_status()
            token = auth_resp.json()["access_token"]

            # Step 2: streaming chat
            chat_headers = {
                **base,
                "authorization": f"Bearer {token}",
                "content-type": "application/json",
                "accept": "text/event-stream",
            }
            last_message: str = ""

            async with client.stream(
                "POST", _CHAT_URL,
                json=_build_body(prompt),
                headers=chat_headers,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    if event.get("ai_state") != "streaming_message":
                        continue

                    raw_str = event.get("payload", {}).get("streaming_string", "")
                    if not raw_str:
                        continue
                    try:
                        inner = json.loads(raw_str)
                        msg = inner.get("message", "")
                        if msg:
                            last_message = msg
                    except json.JSONDecodeError:
                        if isinstance(raw_str, str) and raw_str:
                            last_message = raw_str

            response = _clean(last_message) or None
            if not response:
                error = "Empty response — no streaming_message events with text"

    except Exception as exc:
        error = str(exc)

    duration_ms = int((time.monotonic() - t0) * 1000)
    return ScrapeResult(
        site=SITE_NAME,
        prompt=prompt,
        response=response,
        model_hint=None,
        tokens_hint=None,
        error=error,
        duration_ms=duration_ms,
    )

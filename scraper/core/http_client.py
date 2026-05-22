"""
Pure-HTTP chat client.  After the one-time browser login (session saved to
disk), this module replays the session cookies/token against the site's chat
API endpoint directly — no browser involved.

Each site exposes its configuration as a SiteConfig dataclass.  The
`stream_response` coroutine handles both SSE (text/event-stream) and
newline-delimited JSON streaming formats automatically.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import AsyncIterator

import httpx


@dataclass
class SiteConfig:
    name: str
    chat_url: str
    session_file: str | None
    # Headers added on top of the session headers (e.g. content-type, origin)
    extra_headers: dict[str, str] = field(default_factory=dict)
    # Function that builds the POST body given a prompt string
    # Set after API sniffing; defaults to a plain JSON body
    build_body: object = None


def _sse_chunks(raw: str) -> list[str]:
    """Extract 'data: ...' payloads from an SSE frame."""
    chunks = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                chunks.append(payload)
    return chunks


def _extract_text(payload: str) -> str:
    """
    Try to pull the text delta out of a streamed payload.
    Handles:
      - OpenAI-style: {"choices":[{"delta":{"content":"..."}}]}
      - Anthropic-style: {"type":"content_block_delta","delta":{"text":"..."}}
      - Plain string payloads
    """
    try:
        obj = json.loads(payload)
        # OpenAI / OpenAI-compatible
        if "choices" in obj:
            delta = obj["choices"][0].get("delta", {})
            return delta.get("content", "")
        # Anthropic
        if obj.get("type") == "content_block_delta":
            return obj.get("delta", {}).get("text", "")
        # Generic {"text": "..."} or {"content": "..."}
        for key in ("text", "content", "message", "response"):
            if key in obj:
                val = obj[key]
                if isinstance(val, str):
                    return val
    except (json.JSONDecodeError, KeyError, IndexError):
        return payload  # treat raw string as plain text delta
    return ""


async def stream_chat(
    config: SiteConfig,
    prompt: str,
    session_headers: dict[str, str],
    timeout: int = 120,
) -> str:
    """
    POST `prompt` to config.chat_url, stream the response, return full text.
    Falls back to reading the full response body if streaming fails.
    """
    body = config.build_body(prompt) if config.build_body else {"message": prompt}

    headers = {
        **session_headers,
        "content-type": "application/json",
        "accept": "text/event-stream, application/json, */*",
        **config.extra_headers,
    }

    accumulated: list[str] = []

    async with httpx.AsyncClient(http2=True, timeout=timeout, follow_redirects=True) as client:
        async with client.stream("POST", config.chat_url, json=body, headers=headers) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            if "event-stream" in content_type or "text/plain" in content_type:
                # SSE / chunked plain text
                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    # Process complete SSE frames (double newline boundary)
                    while "\n\n" in buffer:
                        frame, buffer = buffer.split("\n\n", 1)
                        for payload in _sse_chunks(frame):
                            text = _extract_text(payload)
                            if text:
                                accumulated.append(text)
                # Flush remainder
                if buffer.strip():
                    for payload in _sse_chunks(buffer):
                        text = _extract_text(payload)
                        if text:
                            accumulated.append(text)
            else:
                # Non-streaming JSON response
                body_bytes = await resp.aread()
                try:
                    obj = json.loads(body_bytes)
                    for key in ("response", "message", "content", "text", "answer"):
                        if key in obj and isinstance(obj[key], str):
                            accumulated.append(obj[key])
                            break
                    else:
                        accumulated.append(body_bytes.decode("utf-8", errors="replace"))
                except Exception:
                    accumulated.append(body_bytes.decode("utf-8", errors="replace"))

    return "".join(accumulated).strip()

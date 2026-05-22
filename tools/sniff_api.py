"""
One-time tool: launches a browser session with the saved session file,
sends a short prompt, and logs every network request/response so we can
identify the chat API endpoint to hit directly with httpx.

Usage:
    python tools/sniff_api.py mindtrip
    python tools/sniff_api.py wanderboat
"""

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

SITES = {
    "mindtrip": {
        "url": "https://mindtrip.ai",
        "session": "sessions/mindtrip_session.json",
        "input_locator": ("role", "textbox", "Ask anything"),
        "submit": "Enter",
    },
    "wanderboat": {
        "url": "https://wanderboat.ai/chat",
        "session": None,
        "input_locator": ("role", "textbox", "input-textarea"),
        "submit": "Enter",
    },
}

PROBE_PROMPT = "Best city to visit in Italy in one sentence."

SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2", ".css"}
SKIP_PREFIXES = ("data:", "blob:")


def _interesting(url: str) -> bool:
    if any(url.startswith(p) for p in SKIP_PREFIXES):
        return False
    path = url.split("?")[0].split("#")[0]
    if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    return True


async def sniff(site: str) -> None:
    cfg = SITES[site]
    captured: list[dict] = []

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(channel="chrome", headless=False)
        except Exception:
            browser = await pw.chromium.launch(headless=False)

        ctx_kwargs: dict = {
            "viewport": {"width": 1280, "height": 900},
        }
        if cfg["session"] and Path(cfg["session"]).exists():
            ctx_kwargs["storage_state"] = cfg["session"]

        context = await browser.new_context(**ctx_kwargs)
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()

        def on_request(req):
            if not _interesting(req.url):
                return
            # Capture ALL methods for api.mindtrip.ai / api.wanderboat.ai;
            # skip GET on everything else (analytics noise)
            is_api = "api.mindtrip.ai" in req.url or "api.wanderboat.ai" in req.url or "wanderboat.ai/api" in req.url
            if req.method in ("GET", "OPTIONS") and not is_api:
                return
            try:
                post_data = req.post_data
            except Exception:
                try:
                    raw = req.post_data_buffer
                    post_data = f"<binary {len(raw)} bytes>"
                except Exception:
                    post_data = "<unreadable>"
            captured.append({
                "type": "request",
                "method": req.method,
                "url": req.url,
                "headers": dict(req.headers),
                "post_data": post_data,
            })
            print(f"  [REQ] {req.method} {req.url}")

        async def on_response(resp):
            if not _interesting(resp.url):
                return
            is_api = "api.mindtrip.ai" in resp.url or "api.wanderboat.ai" in resp.url or "wanderboat.ai/api" in resp.url
            if resp.request.method in ("GET", "OPTIONS") and not is_api:
                return
            try:
                body = await resp.body()
                body_preview = body[:400].decode("utf-8", errors="replace")
            except Exception:
                body_preview = "<unreadable>"
            captured.append({
                "type": "response",
                "status": resp.status,
                "url": resp.url,
                "headers": dict(resp.headers),
                "body_preview": body_preview,
            })
            print(f"  [RSP] {resp.status} {resp.url}  body[0:80]={body_preview[:80]!r}")

        ws_log: list[dict] = []

        def on_websocket(ws):
            print(f"  [WS] Connected → {ws.url}")
            ws_log.append({"type": "ws_connect", "url": ws.url})

            def on_sent(payload):
                text = payload.get("text") if isinstance(payload, dict) else str(payload)
                preview = (text or "")[:300]
                print(f"  [WS→] {preview}")
                ws_log.append({"type": "ws_sent", "url": ws.url, "data": text})

            def on_recv(payload):
                text = payload.get("text") if isinstance(payload, dict) else str(payload)
                preview = (text or "")[:300]
                print(f"  [WS←] {preview}")
                ws_log.append({"type": "ws_recv", "url": ws.url, "data": text})

            ws.on("framesent", on_sent)
            ws.on("framereceived", on_recv)
            ws.on("close", lambda: print(f"  [WS] Closed → {ws.url}"))

        page.on("websocket", on_websocket)
        page.on("request", on_request)
        page.on("response", on_response)

        print(f"\n[sniff] Navigating to {cfg['url']} ...")
        await page.goto(cfg["url"])

        kind, role, name = cfg["input_locator"]
        print(f"[sniff] Waiting for chat input ({name!r}) ...")
        chat_input = page.get_by_role(role, name=name)
        await chat_input.wait_for(timeout=30_000)

        print(f"[sniff] Sending probe prompt: {PROBE_PROMPT!r}")
        await chat_input.fill(PROBE_PROMPT)
        await chat_input.press(cfg["submit"])

        print("[sniff] Waiting 40 s for streaming response to complete ...")
        await asyncio.sleep(40)

        await context.close()
        await browser.close()

    all_events = captured + ws_log
    out_path = Path(f"tools/{site}_api_sniff.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(all_events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[sniff] Saved {len(all_events)} events → {out_path}")

    print("\n=== WebSocket connections ===")
    for ev in ws_log:
        if ev["type"] == "ws_connect":
            print(f"  {ev['url']}")

    print("\n=== WebSocket frames received (first 500 chars each) ===")
    for ev in ws_log:
        if ev["type"] == "ws_recv" and ev.get("data"):
            print(f"  {ev['data'][:500]}")

    print("\n=== POST requests (chat API candidates) ===")
    for ev in captured:
        if ev["type"] == "request" and ev["method"] == "POST":
            if any(x in ev["url"] for x in ("api.mindtrip", "api.wanderboat", "wanderboat.ai/api")):
                print(f"  {ev['url']}")
                if ev["post_data"]:
                    print(f"    body: {ev['post_data'][:200]}")


if __name__ == "__main__":
    site = sys.argv[1] if len(sys.argv) > 1 else "mindtrip"
    if site not in SITES:
        print(f"Usage: python tools/sniff_api.py [{' | '.join(SITES)}]")
        sys.exit(1)
    asyncio.run(sniff(site))

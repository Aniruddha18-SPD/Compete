"""
Extracts cookies and auth tokens from Playwright storage_state JSON files
and converts them into httpx-ready headers/cookies.
"""

import json
from pathlib import Path


def load_storage_state(session_file: str) -> dict:
    p = Path(session_file)
    if not p.exists():
        raise FileNotFoundError(f"Session file not found: {session_file}")
    return json.loads(p.read_text())


def extract_cookies(session_file: str, domain_filter: str | None = None) -> dict[str, str]:
    """Return {name: value} cookie dict, optionally filtered by domain substring."""
    state = load_storage_state(session_file)
    cookies: dict[str, str] = {}
    for c in state.get("cookies", []):
        if domain_filter and domain_filter not in c.get("domain", ""):
            continue
        cookies[c["name"]] = c["value"]
    return cookies


def extract_bearer_token(session_file: str) -> str | None:
    """
    Scan localStorage origins for a bearer / access token.
    Checks common key names used by auth providers.
    """
    state = load_storage_state(session_file)
    token_keys = ("access_token", "accessToken", "token", "id_token", "idToken", "auth_token")
    for origin in state.get("origins", []):
        for entry in origin.get("localStorage", []):
            name: str = entry.get("name", "")
            if any(k in name for k in token_keys):
                value: str = entry.get("value", "")
                # Strip JSON wrapping if stored as {"access_token":"..."}
                if value.startswith("{"):
                    try:
                        obj = json.loads(value)
                        for k in token_keys:
                            if k in obj:
                                return obj[k]
                    except Exception:
                        pass
                return value
    return None


def build_httpx_headers(session_file: str, domain_filter: str | None = None) -> dict[str, str]:
    """
    Build a headers dict suitable for httpx that includes:
    - Cookie header assembled from saved cookies
    - Authorization: Bearer <token> if a token is found in localStorage
    """
    cookies = extract_cookies(session_file, domain_filter=domain_filter)
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

    headers: dict[str, str] = {
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
    }
    if cookie_header:
        headers["cookie"] = cookie_header

    token = extract_bearer_token(session_file)
    if token:
        headers["authorization"] = f"Bearer {token}"

    return headers

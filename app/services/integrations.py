"""
Integration helpers for the external services configured in the Admin panel:

- Supabase: used to pull "Other Details" for a record based on its
  Boccard Item Number (table configured by the admin, default "listData").
- Accurate.id: OAuth2 accounting integration. We can't fully complete the
  OAuth flow from the server alone (it needs a browser redirect + user
  login), but we CAN validate that the Client ID / Client Secret pair is
  recognized by Accurate's token endpoint, which is enough to confirm the
  credentials and route are correct.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from app.services.db_service import get_setting

ACCURATE_TOKEN_URL = "https://account.accurate.id/oauth/token"


def _normalize_key(key):
    """Normalize a column/field name for loose matching (case, spaces, punctuation insensitive)."""
    return "".join(ch for ch in str(key).lower() if ch.isalnum())


def _http_request(url, method="GET", headers=None, data=None, timeout=10):
    req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, None
    except urllib.error.URLError as e:
        return None, None, str(e.reason)
    except Exception as e:  # noqa: BLE001 - surface any unexpected failure to the caller
        return None, None, str(e)


def get_supabase_settings():
    return {
        "enabled": get_setting("supabase_enabled", "0") == "1",
        "url": (os.environ.get("SUPABASE_URL", "") or "").rstrip("/"),
        "key": os.environ.get("SUPABASE_KEY", "") or "",
        "table": get_setting("supabase_table", "listData") or "listData",
        "match_column": get_setting("supabase_match_column", "boccard_item_number") or "boccard_item_number",
    }


def fetch_other_details_by_boccard(boccard_item_number, extra_data_keys=None):
    """
    Look up a row in the Supabase "listData" table matching the given
    Boccard Item Number, and return a dict of {extra_data_key: value}
    for every column whose name loosely matches one of extra_data_keys.

    Returns (result_dict, error_message). error_message is None on success.
    """
    settings = get_supabase_settings()
    if not settings["enabled"]:
        return {}, "Supabase integration is disabled."
    if not settings["url"] or not settings["key"]:
        return {}, "Supabase URL / Key is not configured."
    if not boccard_item_number:
        return {}, None

    match_param = urllib.parse.quote(settings["match_column"], safe="")
    query_url = (
        f"{settings['url']}/rest/v1/{urllib.parse.quote(settings['table'], safe='')}"
        f"?{match_param}=eq.{urllib.parse.quote(str(boccard_item_number), safe='')}"
        f"&select=*&limit=1"
    )
    headers = {
        "apikey": settings["key"],
        "Authorization": f"Bearer {settings['key']}",
        "Accept": "application/json",
    }
    status, body, err = _http_request(query_url, headers=headers)
    if err:
        return {}, f"Could not reach Supabase: {err}"
    if status is None or status >= 400:
        return {}, f"Supabase returned an error (HTTP {status}): {(body or '')[:300]}"

    try:
        rows = json.loads(body or "[]")
    except ValueError:
        return {}, "Supabase returned an unexpected (non-JSON) response."

    if not rows:
        return {}, None

    row = rows[0]
    if not extra_data_keys:
        return row, None

    normalized_lookup = {_normalize_key(col): value for col, value in row.items()}
    matched = {}
    for key in extra_data_keys:
        norm = _normalize_key(key)
        if norm in normalized_lookup:
            matched[key] = normalized_lookup[norm]
    return matched, None


def test_supabase_connection(url=None, key=None, table=None):
    """Perform a real request against the Supabase REST API to confirm the
    URL / Key / table are valid and reachable."""
    settings = get_supabase_settings()
    url = (url or settings["url"] or "").rstrip("/")
    key = key or settings["key"]
    table = table or settings["table"]

    if not url or not key:
        return {"success": False, "message": "Project URL and Key are required."}

    check_url = f"{url}/rest/v1/{urllib.parse.quote(table, safe='')}?select=*&limit=1"
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    status, body, err = _http_request(check_url, headers=headers)

    if err:
        return {"success": False, "message": f"Could not reach {url}: {err}"}
    if status == 200:
        try:
            rows = json.loads(body or "[]")
            count = len(rows)
        except ValueError:
            count = 0
        return {
            "success": True,
            "message": f"Connected successfully. Table \"{table}\" is reachable "
                       f"({count} row{'s' if count != 1 else ''} returned by the test query).",
        }
    if status in (401, 403):
        return {"success": False, "message": f"Rejected (HTTP {status}): the API key looks invalid or lacks access."}
    if status == 404:
        return {"success": False, "message": f"HTTP 404: table \"{table}\" was not found at that Project URL."}
    return {"success": False, "message": f"Unexpected response (HTTP {status}): {(body or '')[:300]}"}


def test_accurate_credentials(client_id=None, client_secret=None):
    """
    Validate the Accurate.id Client ID / Client Secret against the real
    token endpoint. We can't complete a full OAuth login from the server,
    but Accurate validates the Basic Auth (client credentials) before it
    even looks at the grant itself, so sending a deliberately invalid
    refresh_token still tells us whether the credentials/route are correct:
      - invalid_client / 401           -> credentials wrong
      - invalid_grant / any other 400  -> credentials + route are correct,
                                           just no valid token/code (expected)
    """
    settings_enabled = get_setting("accurate_enabled", "0") == "1"
    client_id = client_id or os.environ.get("ACCURATE_CLIENT_ID", "")
    client_secret = client_secret or os.environ.get("ACCURATE_CLIENT_SECRET", "")

    if not settings_enabled and client_id is None:
        return {"success": False, "message": "Accurate.id integration is disabled."}
    if not client_id or not client_secret:
        return {"success": False, "message": "Client ID and Client Secret are required."}

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": "connection-test-invalid-token",
    }).encode("utf-8")
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    status, resp_body, err = _http_request(ACCURATE_TOKEN_URL, method="POST", headers=headers, data=body)

    if err:
        return {"success": False, "message": f"Could not reach {ACCURATE_TOKEN_URL}: {err}"}

    try:
        parsed = json.loads(resp_body or "{}")
    except ValueError:
        parsed = {}
    error_code = (parsed.get("error") or "").lower() if isinstance(parsed, dict) else ""

    if status in (401,) or error_code in ("invalid_client", "unauthorized_client"):
        return {"success": False, "message": f"Rejected (HTTP {status}, {error_code or 'unauthorized'}): "
                                              f"Client ID / Client Secret is not recognized by Accurate.id."}
    if status == 400 and error_code in ("invalid_grant", "invalid_request", "unsupported_grant_type"):
        return {"success": True, "message": "Route and credentials look correct: Accurate.id recognized the "
                                             f"Client ID / Secret (server responded with '{error_code}', which is "
                                             "expected since no real token was sent)."}
    if status == 200:
        return {"success": True, "message": "Unexpectedly received a token for a fake refresh_token; "
                                             "route and credentials are reachable."}
    return {"success": False, "message": f"Unexpected response (HTTP {status}): {(resp_body or '')[:300]}"}

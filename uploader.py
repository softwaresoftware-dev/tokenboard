"""HTTP client for uploading stats to the tokenboard API."""

import json
import urllib.request
import urllib.error

DEFAULT_API_BASE = "https://tokenboard.softwaresoftware.dev"
USER_AGENT = "tokenboard-plugin/1.0"


def register(display_name: str, api_base: str = DEFAULT_API_BASE) -> dict:
    """Register a new user. Returns {"user_id": ..., "api_key": ...}."""
    data = json.dumps({"display_name": display_name}).encode()
    req = urllib.request.Request(
        f"{api_base}/api/register",
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Registration failed ({e.code}): {body}") from e


def upload(stats: dict, api_key: str, api_base: str = DEFAULT_API_BASE) -> dict:
    """Upload a stats snapshot. Returns {"ok": true, "rank": N}."""
    payload = {
        "total_tokens": stats["total_tokens"],
        "total_input_tokens": stats["total_input_tokens"],
        "total_output_tokens": stats["total_output_tokens"],
        "total_cache_read_tokens": stats["total_cache_read_tokens"],
        "total_cache_write_tokens": stats["total_cache_write_tokens"],
        "total_cost_usd": stats["total_cost_usd"],
        "cost_by_model": stats["cost_by_model"],
        "total_sessions": stats["total_sessions"],
        "total_messages": stats["total_messages"],
        "first_session_date": stats.get("first_session_date"),
        "stats_computed_date": stats.get("stats_computed_date"),
        "subscription_tier": stats.get("subscription_tier", "unknown"),
        "subscription_label": stats.get("subscription_label", "Unknown"),
        "monthly_cost": stats.get("monthly_cost", 0),
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{api_base}/api/submit",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Upload failed ({e.code}): {body}") from e

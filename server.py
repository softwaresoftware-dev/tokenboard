"""MCP server for tokenboard — token usage leaderboard.

On startup, silently uploads stats to the leaderboard in a background thread.
Exposes tools for registration, status checks, and manual refresh.
"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP

import calculator
import store
import uploader

mcp = FastMCP("tokenboard")

STATS_PATH = calculator.STATS_PATH
API_BASE = os.environ.get("TOKENBOARD_API_BASE", uploader.DEFAULT_API_BASE)


def _bg_upload():
    """Background upload — runs once on MCP server start."""
    try:
        config = store.load_config()
        if not config.get("api_key"):
            return

        stats_date = calculator.get_stats_date(STATS_PATH)
        if not stats_date:
            return
        if stats_date == config.get("last_upload_date"):
            return

        stats = calculator.calculate(STATS_PATH)
        uploader.upload(stats, config["api_key"], API_BASE)
        store.save_last_upload(stats_date)
    except Exception:
        pass


threading.Thread(target=_bg_upload, daemon=True).start()


@mcp.tool()
def tokenboard_register(display_name: str) -> str:
    """Register for the tokenboard leaderboard.

    Args:
        display_name: Your name on the leaderboard (e.g. 'Thatcher')
    """
    if store.is_registered():
        config = store.load_config()
        return (
            f"Already registered as '{config.get('display_name')}'. "
            f"Your API key is stored locally."
        )

    try:
        result = uploader.register(display_name, API_BASE)
    except RuntimeError as e:
        return f"Registration failed: {e}"

    store.save_registration(result["user_id"], result["api_key"], display_name)

    # Do initial upload
    try:
        stats = calculator.calculate(STATS_PATH)
        resp = uploader.upload(stats, result["api_key"], API_BASE)
        stats_date = calculator.get_stats_date(STATS_PATH)
        if stats_date:
            store.save_last_upload(stats_date)
        rank_msg = f" You're rank #{resp['rank']} on the leaderboard."
    except Exception:
        rank_msg = ""

    return (
        f"Registered as '{display_name}'{rank_msg}\n"
        f"Your stats will be uploaded automatically on each session.\n"
        f"View the leaderboard at https://tokenboard.nov.solutions"
    )


@mcp.tool()
def tokenboard_status() -> str:
    """Show your current token usage stats and leaderboard info."""
    if not store.is_registered():
        return (
            "Not registered yet. Use tokenboard_register(display_name) "
            "to join the leaderboard."
        )

    config = store.load_config()
    try:
        stats = calculator.calculate(STATS_PATH)
    except FileNotFoundError:
        return "No stats-cache.json found. Use Claude Code to generate usage data first."

    def fmt_tokens(n):
        if n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.2f}B"
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.0f}K"
        return str(n)

    lines = [
        f"Display name: {config.get('display_name', 'unknown')}",
        f"Total tokens: {fmt_tokens(stats['total_tokens'])}",
        f"Equivalent API cost: ${stats['total_cost_usd']:,.2f}",
        f"Sessions: {stats['total_sessions']:,}",
        f"Messages: {stats['total_messages']:,}",
        f"First session: {stats.get('first_session_date', 'unknown')}",
        f"Last upload: {config.get('last_upload_date', 'never')}",
        f"Leaderboard: https://tokenboard.nov.solutions",
    ]
    return "\n".join(lines)


@mcp.tool()
def tokenboard_refresh() -> str:
    """Force re-upload your current stats to the leaderboard."""
    if not store.is_registered():
        return "Not registered yet. Use tokenboard_register(display_name) first."

    config = store.load_config()
    try:
        stats = calculator.calculate(STATS_PATH)
        resp = uploader.upload(stats, config["api_key"], API_BASE)
        stats_date = calculator.get_stats_date(STATS_PATH)
        if stats_date:
            store.save_last_upload(stats_date)
        return f"Stats uploaded. You're rank #{resp['rank']} on the leaderboard."
    except FileNotFoundError:
        return "No stats-cache.json found."
    except RuntimeError as e:
        return f"Upload failed: {e}"


if __name__ == "__main__":
    mcp.run()

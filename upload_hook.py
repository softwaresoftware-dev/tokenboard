#!/usr/bin/env python3
"""SessionEnd hook — uploads fresh token stats to the tokenboard leaderboard.

Triggered by Claude Code on session end via hooks/hooks.json.
Aggregates stats from raw JSONL session files, uploads to the API,
and logs errors to ~/.tokenboard/upload.log.

Always exits 0 to avoid interfering with Claude Code shutdown.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

LOG_PATH = os.path.expanduser("~/.tokenboard/upload.log")
LOG_MAX_BYTES = 50 * 1024  # 50KB cap


def _log(message: str):
    """Append a timestamped message to the upload log, capping at LOG_MAX_BYTES."""
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}\n"

        # Cap log size by truncating from the top
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > LOG_MAX_BYTES:
            with open(LOG_PATH) as f:
                content = f.read()
            # Keep the last ~40KB
            content = content[-(LOG_MAX_BYTES - 10 * 1024) :]
            with open(LOG_PATH, "w") as f:
                f.write(content)

        with open(LOG_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass


def main():
    import aggregator
    import store
    import uploader

    config = store.load_config()
    if not config.get("api_key"):
        return  # Not registered

    stats = aggregator.calculate()
    result = uploader.upload(stats, config["api_key"])

    # Save the current date as last upload
    today = time.strftime("%Y-%m-%d")
    store.save_last_upload(today)

    _log(f"ok rank={result.get('rank', '?')} tokens={stats['total_tokens']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log(f"error: {e}")
    sys.exit(0)

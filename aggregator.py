"""Token usage aggregator that builds on Claude Code's stats-cache.json.

Reads ~/.claude/stats-cache.json for historical totals (preserved even after
session files are cleaned up), then supplements with fresh data from JSONL
session files newer than the cache's lastComputedDate. This mirrors how
Claude Code's own stats.ts works: cache for history, live scan for today.
"""

import glob
import json
import os

from calculator import PRICING, _cost_for_model, _match_pricing, get_subscription_tier

STATS_CACHE_PATH = os.path.expanduser("~/.claude/stats-cache.json")
PROJECTS_DIR = os.path.expanduser("~/.claude/projects")


def _load_stats_cache() -> dict | None:
    """Load Claude Code's stats-cache.json."""
    try:
        with open(STATS_CACHE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _get_session_files() -> list[str]:
    """Collect all session JSONL files, including subagent transcripts."""
    files = []
    files.extend(glob.glob(os.path.join(PROJECTS_DIR, "*", "*.jsonl")))
    files.extend(
        glob.glob(os.path.join(PROJECTS_DIR, "*", "*", "subagents", "agent-*.jsonl"))
    )
    return files


def _process_file(path: str) -> dict:
    """Extract token usage, session count, and message count from a JSONL file.

    Only includes entries with timestamps >= from_date if provided.
    """
    is_subagent = "/subagents/" in path
    model_usage: dict[str, dict] = {}
    message_count = 0
    first_ts = None

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            ts = entry.get("timestamp")

            # Track first timestamp
            if ts and first_ts is None and not is_subagent:
                first_ts = ts

            # Count non-sidechain user and assistant messages
            if not is_subagent and entry_type in ("user", "assistant"):
                if not entry.get("isSidechain"):
                    message_count += 1

            # Extract token usage from assistant messages
            if entry_type == "assistant":
                msg = entry.get("message", {})
                usage = msg.get("usage")
                model = msg.get("model")
                if not usage or not model or model in ("unknown", "<synthetic>"):
                    continue

                if model not in model_usage:
                    model_usage[model] = {
                        "inputTokens": 0,
                        "outputTokens": 0,
                        "cacheReadInputTokens": 0,
                        "cacheCreationInputTokens": 0,
                    }

                mu = model_usage[model]
                mu["inputTokens"] += usage.get("input_tokens", 0)
                mu["outputTokens"] += usage.get("output_tokens", 0)
                mu["cacheReadInputTokens"] += usage.get("cache_read_input_tokens", 0)
                mu["cacheCreationInputTokens"] += usage.get(
                    "cache_creation_input_tokens", 0
                )

    return {
        "model_usage": model_usage,
        "message_count": message_count,
        "is_subagent": is_subagent,
        "first_timestamp": first_ts,
    }


def _merge_model_usage(base: dict, new: dict):
    """Merge new model usage counts into base (mutates base)."""
    for model, counts in new.items():
        if model not in base:
            base[model] = {
                "inputTokens": 0,
                "outputTokens": 0,
                "cacheReadInputTokens": 0,
                "cacheCreationInputTokens": 0,
            }
        for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"):
            base[model][key] += counts.get(key, 0)


def _date_from_mtime(path: str) -> str | None:
    """Get YYYY-MM-DD date string from file mtime."""
    try:
        import time
        mtime = os.path.getmtime(path)
        return time.strftime("%Y-%m-%d", time.localtime(mtime))
    except OSError:
        return None


def aggregate() -> dict:
    """Aggregate token usage: stats-cache.json baseline + fresh JSONL data.

    Returns raw aggregation: model_usage, total_sessions, total_messages,
    first_session_date.
    """
    cache = _load_stats_cache()

    if cache:
        # Start with historical totals from stats-cache.json
        model_usage = dict(cache.get("modelUsage", {}))
        total_sessions = cache.get("totalSessions", 0)
        total_messages = cache.get("totalMessages", 0)
        first_session_date = cache.get("firstSessionDate")
        last_computed = cache.get("lastComputedDate")  # e.g. "2026-04-04"
    else:
        # No cache — scan everything
        model_usage = {}
        total_sessions = 0
        total_messages = 0
        first_session_date = None
        last_computed = None

    # Scan JSONL files for data newer than what the cache covers
    if last_computed:
        session_files = _get_session_files()
        for path in session_files:
            # Skip files not modified after the cache date
            file_date = _date_from_mtime(path)
            if file_date and file_date <= last_computed:
                continue

            result = _process_file(path)
            _merge_model_usage(model_usage, result["model_usage"])
            if not result["is_subagent"]:
                total_sessions += 1
                total_messages += result["message_count"]
                ts = result.get("first_timestamp")
                if ts and (first_session_date is None or ts < first_session_date):
                    first_session_date = ts
    else:
        # No cache at all — full scan of everything
        session_files = _get_session_files()
        for path in session_files:
            result = _process_file(path)
            _merge_model_usage(model_usage, result["model_usage"])
            if not result["is_subagent"]:
                total_sessions += 1
                total_messages += result["message_count"]
                ts = result.get("first_timestamp")
                if ts and (first_session_date is None or ts < first_session_date):
                    first_session_date = ts

    return {
        "model_usage": model_usage,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "first_session_date": first_session_date,
    }


def calculate() -> dict:
    """Aggregate and calculate costs. Returns same shape as calculator.calculate()."""
    raw = aggregate()
    model_usage = raw["model_usage"]

    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0
    total_cost = 0.0
    cost_by_model = {}

    for model_id, usage in model_usage.items():
        inp = usage.get("inputTokens", 0)
        out = usage.get("outputTokens", 0)
        cr = usage.get("cacheReadInputTokens", 0)
        cw = usage.get("cacheCreationInputTokens", 0)

        total_input += inp
        total_output += out
        total_cache_read += cr
        total_cache_write += cw

        pricing = _match_pricing(model_id)
        if pricing:
            model_cost = _cost_for_model(usage, pricing)
            total_cost += model_cost
            cost_by_model[model_id] = round(model_cost, 2)

    sub = get_subscription_tier()

    return {
        "total_tokens": total_input + total_output + total_cache_read + total_cache_write,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_read_tokens": total_cache_read,
        "total_cache_write_tokens": total_cache_write,
        "total_cost_usd": round(total_cost, 2),
        "cost_by_model": cost_by_model,
        "total_sessions": raw["total_sessions"],
        "total_messages": raw["total_messages"],
        "first_session_date": raw["first_session_date"],
        "stats_computed_date": None,
        "subscription_tier": sub["tier"],
        "subscription_label": sub["label"],
        "monthly_cost": sub["monthly_cost"],
    }

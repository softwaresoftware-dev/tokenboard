"""Token cost calculation from Claude Code stats-cache.json."""

import json
import os

# Per-million-token pricing by model prefix
PRICING = {
    "claude-opus-4-5": (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-6": (15.00, 75.00, 1.50, 18.75),
    "claude-sonnet-4-5": (3.00, 15.00, 0.30, 3.75),
    "claude-sonnet-4-6": (3.00, 15.00, 0.30, 3.75),
    "claude-haiku-4-5": (0.80, 4.00, 0.08, 1.00),
}

STATS_PATH = os.path.expanduser("~/.claude/stats-cache.json")
CREDENTIALS_PATH = os.path.expanduser("~/.claude/.credentials.json")

SUBSCRIPTION_TIERS = {
    "pro": {"label": "Pro", "monthly_cost": 20},
    "max": {"label": "Max", "monthly_cost": 100},
    "max_5x": {"label": "Max (5x)", "monthly_cost": 200},
}


def _match_pricing(model_id: str):
    """Match a model ID like 'claude-opus-4-6' or 'claude-opus-4-5-20251101' to pricing."""
    for prefix, prices in PRICING.items():
        if model_id.startswith(prefix):
            return prices
    return None


def _cost_for_model(usage: dict, pricing: tuple) -> float:
    """Calculate cost in USD for a single model's usage."""
    inp_price, out_price, cache_read_price, cache_write_price = pricing
    cost = 0.0
    cost += usage.get("inputTokens", 0) * inp_price / 1_000_000
    cost += usage.get("outputTokens", 0) * out_price / 1_000_000
    cost += usage.get("cacheReadInputTokens", 0) * cache_read_price / 1_000_000
    cost += usage.get("cacheCreationInputTokens", 0) * cache_write_price / 1_000_000
    return cost


def get_stats_date(path: str = STATS_PATH) -> str | None:
    """Return the lastComputedDate from stats-cache.json, or None."""
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("lastComputedDate")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def calculate(path: str = STATS_PATH) -> dict:
    """Calculate aggregate token usage and equivalent API cost.

    Returns dict with:
        total_tokens, total_cost_usd, cost_by_model,
        total_sessions, total_messages, first_session_date,
        stats_computed_date
    """
    with open(path) as f:
        data = json.load(f)

    model_usage = data.get("modelUsage", {})

    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0
    total_cost = 0.0
    cost_by_model = {}

    for model_id, usage in model_usage.items():
        inp = usage.get("inputTokens", 0)
        out = usage.get("outputTokens", 0)
        cache_read = usage.get("cacheReadInputTokens", 0)
        cache_write = usage.get("cacheCreationInputTokens", 0)

        total_input += inp
        total_output += out
        total_cache_read += cache_read
        total_cache_write += cache_write

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
        "total_sessions": data.get("totalSessions", 0),
        "total_messages": data.get("totalMessages", 0),
        "first_session_date": data.get("firstSessionDate"),
        "stats_computed_date": data.get("lastComputedDate"),
        "subscription_tier": sub["tier"],
        "subscription_label": sub["label"],
        "monthly_cost": sub["monthly_cost"],
    }


def get_subscription_tier(path: str = CREDENTIALS_PATH) -> dict:
    """Read subscription tier from Claude credentials."""
    try:
        with open(path) as f:
            data = json.load(f)
        oauth = data.get("claudeAiOauth", {})
        sub_type = oauth.get("subscriptionType", "unknown")
        rate_tier = oauth.get("rateLimitTier", "")

        # Detect 5x from rate limit tier
        if "5x" in rate_tier:
            tier_key = "max_5x"
        else:
            tier_key = sub_type

        info = SUBSCRIPTION_TIERS.get(tier_key, {"label": sub_type.title(), "monthly_cost": 0})
        return {"tier": tier_key, "label": info["label"], "monthly_cost": info["monthly_cost"]}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {"tier": "unknown", "label": "Unknown", "monthly_cost": 0}

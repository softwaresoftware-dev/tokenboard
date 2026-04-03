"""Shared fixtures for tokenboard tests."""

import json
import pytest


SAMPLE_STATS = {
    "version": 3,
    "lastComputedDate": "2026-04-02",
    "dailyActivity": [],
    "dailyModelTokens": [],
    "modelUsage": {
        "claude-opus-4-5-20251101": {
            "inputTokens": 617648,
            "outputTokens": 625019,
            "cacheReadInputTokens": 812196584,
            "cacheCreationInputTokens": 65888565,
            "webSearchRequests": 0,
            "costUSD": 0,
            "contextWindow": 0,
            "maxOutputTokens": 0,
        },
        "claude-opus-4-6": {
            "inputTokens": 893323,
            "outputTokens": 6001746,
            "cacheReadInputTokens": 4306947898,
            "cacheCreationInputTokens": 96601128,
            "webSearchRequests": 0,
            "costUSD": 0,
            "contextWindow": 0,
            "maxOutputTokens": 0,
        },
        "claude-sonnet-4-5-20250929": {
            "inputTokens": 59736,
            "outputTokens": 244276,
            "cacheReadInputTokens": 121251831,
            "cacheCreationInputTokens": 9735693,
            "webSearchRequests": 0,
            "costUSD": 0,
            "contextWindow": 0,
            "maxOutputTokens": 0,
        },
        "claude-sonnet-4-6": {
            "inputTokens": 138,
            "outputTokens": 26663,
            "cacheReadInputTokens": 2222293,
            "cacheCreationInputTokens": 518772,
            "webSearchRequests": 0,
            "costUSD": 0,
            "contextWindow": 0,
            "maxOutputTokens": 0,
        },
        "claude-haiku-4-5-20251001": {
            "inputTokens": 464439,
            "outputTokens": 1290256,
            "cacheReadInputTokens": 397377875,
            "cacheCreationInputTokens": 48467674,
            "webSearchRequests": 0,
            "costUSD": 0,
            "contextWindow": 0,
            "maxOutputTokens": 0,
        },
    },
    "totalSessions": 478,
    "totalMessages": 90329,
    "firstSessionDate": "2026-01-05T12:14:15.211Z",
    "hourCounts": {},
    "totalSpeculationTimeSavedMs": 0,
}


@pytest.fixture
def stats_file(tmp_path):
    """Write sample stats to a temp file and return the path."""
    p = tmp_path / "stats-cache.json"
    p.write_text(json.dumps(SAMPLE_STATS))
    return str(p)


@pytest.fixture
def empty_stats_file(tmp_path):
    """Stats file with no model usage."""
    p = tmp_path / "stats-cache.json"
    p.write_text(json.dumps({
        "version": 3,
        "lastComputedDate": "2026-01-01",
        "modelUsage": {},
        "totalSessions": 0,
        "totalMessages": 0,
    }))
    return str(p)

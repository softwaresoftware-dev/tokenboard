"""Tests for the token cost calculator (pricing helpers and aggregator delegation)."""

import json
import os

import pytest

import aggregator
from calculator import _cost_for_model, _match_pricing, calculate, get_stats_date


def test_match_pricing_opus_45():
    assert _match_pricing("claude-opus-4-5-20251101") is not None


def test_match_pricing_opus_46():
    assert _match_pricing("claude-opus-4-6") is not None


def test_match_pricing_sonnet():
    assert _match_pricing("claude-sonnet-4-5-20250929") is not None


def test_match_pricing_haiku():
    assert _match_pricing("claude-haiku-4-5-20251001") is not None


def test_match_pricing_unknown():
    assert _match_pricing("claude-unknown-99") is None


def test_cost_for_model_opus():
    usage = {
        "inputTokens": 1_000_000,
        "outputTokens": 1_000_000,
        "cacheReadInputTokens": 1_000_000,
        "cacheCreationInputTokens": 1_000_000,
    }
    pricing = (15.00, 75.00, 1.50, 18.75)
    cost = _cost_for_model(usage, pricing)
    assert cost == pytest.approx(15.0 + 75.0 + 1.5 + 18.75)


def test_cost_for_model_haiku():
    usage = {
        "inputTokens": 1_000_000,
        "outputTokens": 1_000_000,
        "cacheReadInputTokens": 1_000_000,
        "cacheCreationInputTokens": 1_000_000,
    }
    pricing = (0.80, 4.00, 0.08, 1.00)
    cost = _cost_for_model(usage, pricing)
    assert cost == pytest.approx(0.8 + 4.0 + 0.08 + 1.0)


def test_get_stats_date(stats_file):
    assert get_stats_date(stats_file) == "2026-04-02"


def test_get_stats_date_missing():
    assert get_stats_date("/nonexistent/path") is None


def test_calculate_delegates_to_aggregator(tmp_path, monkeypatch):
    """calculator.calculate() delegates to aggregator.calculate()."""
    # Set up aggregator with a fake stats-cache and no JSONL files
    projects_dir = str(tmp_path / "projects")
    os.makedirs(projects_dir)
    monkeypatch.setattr(aggregator, "PROJECTS_DIR", projects_dir)

    cache_path = str(tmp_path / "stats-cache.json")
    cache_data = {
        "version": 3,
        "lastComputedDate": "2099-12-31",
        "modelUsage": {
            "claude-opus-4-6": {
                "inputTokens": 1_000_000,
                "outputTokens": 1_000_000,
                "cacheReadInputTokens": 0,
                "cacheCreationInputTokens": 0,
            },
        },
        "totalSessions": 42,
        "totalMessages": 500,
        "firstSessionDate": "2026-01-05T12:00:00.000Z",
    }
    with open(cache_path, "w") as f:
        json.dump(cache_data, f)
    monkeypatch.setattr(aggregator, "STATS_CACHE_PATH", cache_path)

    result = calculate()
    assert result["total_sessions"] == 42
    assert result["total_messages"] == 500
    assert result["total_cost_usd"] == pytest.approx(90.0, rel=0.01)
    assert result["first_session_date"] == "2026-01-05T12:00:00.000Z"

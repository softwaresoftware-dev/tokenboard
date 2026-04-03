"""Tests for the token cost calculator."""

import pytest
from calculator import calculate, get_stats_date, _match_pricing, _cost_for_model


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


def test_calculate_totals(stats_file):
    result = calculate(stats_file)
    assert result["total_sessions"] == 478
    assert result["total_messages"] == 90329
    assert result["first_session_date"] == "2026-01-05T12:14:15.211Z"
    assert result["stats_computed_date"] == "2026-04-02"


def test_calculate_tokens(stats_file):
    result = calculate(stats_file)
    # All token fields should be positive
    assert result["total_tokens"] > 0
    assert result["total_input_tokens"] > 0
    assert result["total_output_tokens"] > 0
    assert result["total_cache_read_tokens"] > 0
    assert result["total_cache_write_tokens"] > 0
    # Total should be sum of parts
    assert result["total_tokens"] == (
        result["total_input_tokens"]
        + result["total_output_tokens"]
        + result["total_cache_read_tokens"]
        + result["total_cache_write_tokens"]
    )


def test_calculate_cost(stats_file):
    result = calculate(stats_file)
    assert result["total_cost_usd"] > 0
    assert len(result["cost_by_model"]) == 5
    # Sum of model costs should match total
    model_sum = sum(result["cost_by_model"].values())
    assert model_sum == pytest.approx(result["total_cost_usd"], rel=0.01)


def test_calculate_empty(empty_stats_file):
    result = calculate(empty_stats_file)
    assert result["total_tokens"] == 0
    assert result["total_cost_usd"] == 0.0
    assert result["cost_by_model"] == {}
    assert result["total_sessions"] == 0


def test_calculate_file_not_found():
    with pytest.raises(FileNotFoundError):
        calculate("/nonexistent/path")

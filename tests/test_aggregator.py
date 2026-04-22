"""Tests for the stats-cache + JSONL aggregator."""

import json
import os
import time

import pytest

import aggregator


def _make_assistant_entry(model, input_t, output_t, cache_read=0, cache_write=0, ts=None):
    """Build a minimal assistant JSONL entry."""
    return json.dumps({
        "type": "assistant",
        "isSidechain": False,
        "timestamp": ts or "2026-04-01T10:00:00.000Z",
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input_t,
                "output_tokens": output_t,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
            },
        },
    })


def _make_user_entry(ts=None):
    return json.dumps({
        "type": "user",
        "isSidechain": False,
        "timestamp": ts or "2026-04-01T09:59:00.000Z",
        "message": {"role": "user", "content": "hello"},
    })


def _make_session(tmp_path, project, session_id, entries):
    """Create a session JSONL file under a fake projects dir."""
    proj_dir = tmp_path / "projects" / project
    proj_dir.mkdir(parents=True, exist_ok=True)
    path = proj_dir / f"{session_id}.jsonl"
    path.write_text("\n".join(entries) + "\n")
    return str(path)


def _make_subagent(tmp_path, project, session_id, agent_id, entries):
    """Create a subagent JSONL file."""
    sub_dir = tmp_path / "projects" / project / session_id / "subagents"
    sub_dir.mkdir(parents=True, exist_ok=True)
    path = sub_dir / f"agent-{agent_id}.jsonl"
    path.write_text("\n".join(entries) + "\n")
    return str(path)


def _make_stats_cache(tmp_path, model_usage=None, sessions=0, messages=0,
                      first_session=None, last_computed=None):
    """Write a fake stats-cache.json."""
    cache = {
        "version": 3,
        "lastComputedDate": last_computed,
        "modelUsage": model_usage or {},
        "totalSessions": sessions,
        "totalMessages": messages,
        "firstSessionDate": first_session,
    }
    path = tmp_path / "stats-cache.json"
    path.write_text(json.dumps(cache))
    return str(path)


@pytest.fixture
def agg_env(tmp_path, monkeypatch):
    """Set up aggregator to use temp dirs."""
    projects_dir = str(tmp_path / "projects")
    os.makedirs(projects_dir, exist_ok=True)
    monkeypatch.setattr(aggregator, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(aggregator, "STATS_CACHE_PATH", str(tmp_path / "stats-cache.json"))
    return tmp_path


class TestProcessFile:
    def test_extracts_token_usage(self, agg_env):
        path = _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 100, 200, 300, 400),
        ])
        result = aggregator._process_file(path)
        mu = result["model_usage"]["claude-opus-4-6"]
        assert mu["inputTokens"] == 100
        assert mu["outputTokens"] == 200
        assert mu["cacheReadInputTokens"] == 300
        assert mu["cacheCreationInputTokens"] == 400

    def test_counts_messages(self, agg_env):
        path = _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 10, 20),
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 10, 20),
        ])
        result = aggregator._process_file(path)
        assert result["message_count"] == 4

    def test_skips_sidechain_messages(self, agg_env):
        sidechain = json.dumps({
            "type": "assistant",
            "isSidechain": True,
            "timestamp": "2026-04-01T10:00:00.000Z",
            "message": {
                "model": "claude-opus-4-6",
                "usage": {"input_tokens": 100, "output_tokens": 200},
            },
        })
        path = _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            sidechain,
        ])
        result = aggregator._process_file(path)
        assert "claude-opus-4-6" in result["model_usage"]
        assert result["message_count"] == 1

    def test_subagent_no_message_count(self, agg_env):
        path = _make_subagent(agg_env, "proj1", "sess1", "abc123", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 100, 200),
        ])
        result = aggregator._process_file(path)
        assert result["is_subagent"] is True
        assert result["message_count"] == 0
        assert result["model_usage"]["claude-opus-4-6"]["inputTokens"] == 100

    def test_skips_unknown_model(self, agg_env):
        entry = json.dumps({
            "type": "assistant",
            "timestamp": "2026-04-01T10:00:00.000Z",
            "message": {
                "model": "unknown",
                "usage": {"input_tokens": 100, "output_tokens": 200},
            },
        })
        path = _make_session(agg_env, "proj1", "sess1", [entry])
        result = aggregator._process_file(path)
        assert result["model_usage"] == {}

    def test_skips_synthetic_model(self, agg_env):
        entry = json.dumps({
            "type": "assistant",
            "timestamp": "2026-04-01T10:00:00.000Z",
            "message": {
                "model": "<synthetic>",
                "usage": {"input_tokens": 100, "output_tokens": 200},
            },
        })
        path = _make_session(agg_env, "proj1", "sess1", [entry])
        result = aggregator._process_file(path)
        assert result["model_usage"] == {}

    def test_extracts_first_timestamp(self, agg_env):
        path = _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(ts="2026-01-15T08:00:00.000Z"),
            _make_assistant_entry("claude-opus-4-6", 10, 20, ts="2026-01-15T08:01:00.000Z"),
        ])
        result = aggregator._process_file(path)
        assert result["first_timestamp"] == "2026-01-15T08:00:00.000Z"

    def test_handles_malformed_json(self, agg_env):
        proj_dir = agg_env / "projects" / "proj1"
        proj_dir.mkdir(parents=True)
        path = proj_dir / "sess1.jsonl"
        path.write_text("not json\n" + _make_assistant_entry("claude-opus-4-6", 10, 20) + "\n")
        result = aggregator._process_file(str(path))
        assert result["model_usage"]["claude-opus-4-6"]["inputTokens"] == 10


class TestAggregate:
    def test_no_cache_scans_everything(self, agg_env):
        """Without stats-cache.json, scans all JSONL files."""
        _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 100, 200),
        ])
        result = aggregator.aggregate()
        assert result["total_sessions"] == 1
        assert result["total_messages"] == 2
        assert result["model_usage"]["claude-opus-4-6"]["inputTokens"] == 100

    def test_cache_baseline_used(self, agg_env):
        """With stats-cache.json, historical totals are the baseline."""
        _make_stats_cache(agg_env,
            model_usage={
                "claude-opus-4-6": {
                    "inputTokens": 1000,
                    "outputTokens": 2000,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                },
            },
            sessions=10,
            messages=500,
            first_session="2026-01-05T12:00:00.000Z",
            last_computed="2099-12-31",  # Far future — no files will be newer
        )
        result = aggregator.aggregate()
        assert result["total_sessions"] == 10
        assert result["total_messages"] == 500
        assert result["model_usage"]["claude-opus-4-6"]["inputTokens"] == 1000
        assert result["first_session_date"] == "2026-01-05T12:00:00.000Z"

    def test_cache_plus_new_files(self, agg_env):
        """New files after lastComputedDate are merged with cache baseline."""
        _make_stats_cache(agg_env,
            model_usage={
                "claude-opus-4-6": {
                    "inputTokens": 1000,
                    "outputTokens": 2000,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                },
            },
            sessions=10,
            messages=500,
            first_session="2026-01-05T12:00:00.000Z",
            last_computed="2020-01-01",  # Old date — all files are newer
        )
        _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 100, 200),
        ])
        result = aggregator.aggregate()
        # Cache baseline + new file
        assert result["total_sessions"] == 11
        assert result["total_messages"] == 502
        assert result["model_usage"]["claude-opus-4-6"]["inputTokens"] == 1100

    def test_old_files_skipped_with_cache(self, agg_env):
        """Files older than lastComputedDate are skipped (already in cache)."""
        _make_stats_cache(agg_env,
            model_usage={
                "claude-opus-4-6": {
                    "inputTokens": 1000,
                    "outputTokens": 2000,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                },
            },
            sessions=10,
            messages=500,
            last_computed="2099-12-31",  # Far future
        )
        # This file's mtime is today — but lastComputedDate is far future
        _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 999, 999),
        ])
        result = aggregator.aggregate()
        # Should only have cache data, file is "older" than cache
        assert result["model_usage"]["claude-opus-4-6"]["inputTokens"] == 1000

    def test_subagent_tokens_counted_no_session(self, agg_env):
        _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 100, 200),
        ])
        _make_subagent(agg_env, "proj1", "sess1", "agent1", [
            _make_assistant_entry("claude-opus-4-6", 50, 50),
        ])
        result = aggregator.aggregate()
        assert result["model_usage"]["claude-opus-4-6"]["inputTokens"] == 150
        assert result["total_sessions"] == 1

    def test_empty_projects_dir_no_cache(self, agg_env):
        result = aggregator.aggregate()
        assert result["total_sessions"] == 0
        assert result["model_usage"] == {}

    def test_first_session_date_from_cache(self, agg_env):
        """Cache's firstSessionDate is preserved even without matching files."""
        _make_stats_cache(agg_env,
            first_session="2026-01-05T12:00:00.000Z",
            last_computed="2099-12-31",
        )
        result = aggregator.aggregate()
        assert result["first_session_date"] == "2026-01-05T12:00:00.000Z"


class TestCalculate:
    def test_returns_expected_shape(self, agg_env):
        _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 1_000_000, 1_000_000),
        ])
        result = aggregator.calculate()
        assert "total_tokens" in result
        assert "total_input_tokens" in result
        assert "total_output_tokens" in result
        assert "total_cache_read_tokens" in result
        assert "total_cache_write_tokens" in result
        assert "total_cost_usd" in result
        assert "cost_by_model" in result
        assert "total_sessions" in result
        assert "total_messages" in result
        assert "subscription_tier" in result

    def test_cost_calculation(self, agg_env):
        _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 1_000_000, 1_000_000),
        ])
        result = aggregator.calculate()
        # opus-4-6: 1M input @ $5 + 1M output @ $25 = $30
        assert result["total_cost_usd"] == pytest.approx(30.0, rel=0.01)
        assert result["cost_by_model"]["claude-opus-4-6"] == pytest.approx(30.0, rel=0.01)

    def test_token_sum(self, agg_env):
        _make_session(agg_env, "proj1", "sess1", [
            _make_user_entry(),
            _make_assistant_entry("claude-opus-4-6", 100, 200, 300, 400),
        ])
        result = aggregator.calculate()
        assert result["total_tokens"] == 1000
        assert result["total_input_tokens"] == 100
        assert result["total_output_tokens"] == 200
        assert result["total_cache_read_tokens"] == 300
        assert result["total_cache_write_tokens"] == 400

    def test_with_cache_baseline(self, agg_env):
        """Cost calculation includes cache baseline data."""
        _make_stats_cache(agg_env,
            model_usage={
                "claude-opus-4-6": {
                    "inputTokens": 1_000_000,
                    "outputTokens": 1_000_000,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                },
            },
            sessions=5,
            messages=100,
            last_computed="2099-12-31",
        )
        result = aggregator.calculate()
        assert result["total_cost_usd"] == pytest.approx(30.0, rel=0.01)
        assert result["total_sessions"] == 5

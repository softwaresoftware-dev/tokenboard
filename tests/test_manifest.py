"""Test plugin manifest validity."""

import json
import os

PLUGIN_ROOT = os.path.dirname(os.path.dirname(__file__))
MANIFEST_PATH = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")


def test_manifest_exists():
    assert os.path.isfile(MANIFEST_PATH)


def test_manifest_valid_json():
    with open(MANIFEST_PATH) as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_manifest_required_fields():
    with open(MANIFEST_PATH) as f:
        data = json.load(f)
    assert data["name"] == "tokenboard"
    assert "description" in data
    assert "version" in data
    assert "mcpServers" in data


def test_manifest_mcp_server():
    with open(MANIFEST_PATH) as f:
        data = json.load(f)
    server = data["mcpServers"]["tokenboard"]
    assert server["command"] == "uv"
    assert "server.py" in " ".join(server["args"])


# --- userConfig schema validation (added to prevent regressions like the
# `enum` field in claude-browser-bridge 3.3.0 that broke install). Schema:
# https://code.claude.com/docs/en/plugins-reference.md#user-configuration ---

import json as _json
import os as _os

USER_CONFIG_COMMON_KEYS = {"type", "title", "description", "default", "required", "sensitive"}
USER_CONFIG_TYPE_KEYS = {
    "string": USER_CONFIG_COMMON_KEYS | {"multiple"},
    "number": USER_CONFIG_COMMON_KEYS | {"min", "max"},
    "boolean": USER_CONFIG_COMMON_KEYS,
    "directory": USER_CONFIG_COMMON_KEYS,
    "file": USER_CONFIG_COMMON_KEYS,
}


def _load_manifest_for_uc():
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    with open(_os.path.join(root, ".claude-plugin", "plugin.json")) as f:
        return _json.load(f)


def test_user_config_types():
    """Every userConfig entry must declare a recognized type."""
    plugin_json = _load_manifest_for_uc()
    for name, entry in plugin_json.get("userConfig", {}).items():
        assert "type" in entry, f"userConfig.{name} missing 'type'"
        assert entry["type"] in USER_CONFIG_TYPE_KEYS, (
            f"userConfig.{name}.type={entry['type']!r} is not a recognized "
            f"type. Valid: {sorted(USER_CONFIG_TYPE_KEYS)}"
        )


def test_user_config_schema_strict():
    """userConfig entries must only use keys from the official schema.

    Catches regressions like an `enum` field — the Claude Code manifest schema
    does not support `enum`, `pattern`, or arbitrary JSON Schema keywords.
    """
    plugin_json = _load_manifest_for_uc()
    for name, entry in plugin_json.get("userConfig", {}).items():
        allowed = USER_CONFIG_TYPE_KEYS.get(entry.get("type"), USER_CONFIG_COMMON_KEYS)
        unknown = set(entry.keys()) - allowed
        assert not unknown, (
            f"userConfig.{name} contains unknown keys: {sorted(unknown)}. "
            f"Allowed for type={entry.get('type')!r}: {sorted(allowed)}. "
            f"See https://code.claude.com/docs/en/plugins-reference.md#user-configuration"
        )

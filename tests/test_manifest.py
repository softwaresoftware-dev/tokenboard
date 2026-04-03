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
    assert server["command"] == "python"
    assert "server.py" in server["args"][0]

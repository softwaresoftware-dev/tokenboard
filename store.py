"""Local config store for tokenboard at ~/.tokenboard/config.json."""

import json
import os

CONFIG_DIR = os.path.expanduser("~/.tokenboard")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> dict:
    """Load config from disk. Returns empty dict if not found."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config: dict):
    """Write config to disk."""
    _ensure_dir()
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def save_registration(user_id: str, api_key: str, display_name: str):
    """Store registration details."""
    config = load_config()
    config["user_id"] = user_id
    config["api_key"] = api_key
    config["display_name"] = display_name
    config["registered"] = True
    save_config(config)


def save_last_upload(stats_date: str):
    """Record the last successful upload date."""
    config = load_config()
    config["last_upload_date"] = stats_date
    save_config(config)


def is_registered() -> bool:
    """Check if the user has registered."""
    config = load_config()
    return bool(config.get("api_key"))

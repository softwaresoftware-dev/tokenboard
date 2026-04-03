"""Tests for the local config store."""

import json
import store


def test_load_config_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "CONFIG_PATH", str(tmp_path / "nope.json"))
    assert store.load_config() == {}


def test_save_and_load(tmp_path, monkeypatch):
    path = str(tmp_path / "config.json")
    monkeypatch.setattr(store, "CONFIG_PATH", path)
    monkeypatch.setattr(store, "CONFIG_DIR", str(tmp_path))
    store.save_config({"foo": "bar"})
    assert store.load_config() == {"foo": "bar"}


def test_save_registration(tmp_path, monkeypatch):
    path = str(tmp_path / "config.json")
    monkeypatch.setattr(store, "CONFIG_PATH", path)
    monkeypatch.setattr(store, "CONFIG_DIR", str(tmp_path))
    store.save_registration("uid-123", "key-abc", "Thatcher")
    config = store.load_config()
    assert config["user_id"] == "uid-123"
    assert config["api_key"] == "key-abc"
    assert config["display_name"] == "Thatcher"
    assert config["registered"] is True


def test_save_last_upload(tmp_path, monkeypatch):
    path = str(tmp_path / "config.json")
    monkeypatch.setattr(store, "CONFIG_PATH", path)
    monkeypatch.setattr(store, "CONFIG_DIR", str(tmp_path))
    store.save_config({"api_key": "k"})
    store.save_last_upload("2026-04-02")
    config = store.load_config()
    assert config["last_upload_date"] == "2026-04-02"
    assert config["api_key"] == "k"


def test_is_registered(tmp_path, monkeypatch):
    path = str(tmp_path / "config.json")
    monkeypatch.setattr(store, "CONFIG_PATH", path)
    monkeypatch.setattr(store, "CONFIG_DIR", str(tmp_path))
    assert store.is_registered() is False
    store.save_registration("uid", "key", "Name")
    assert store.is_registered() is True

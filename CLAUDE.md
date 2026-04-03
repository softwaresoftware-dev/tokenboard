# CLAUDE.md — tokenboard

Token usage leaderboard plugin for Claude Code. Calculates equivalent API cost from `~/.claude/stats-cache.json` and uploads to the public leaderboard at tokenboard.softwaresoftware.dev.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/tokenboard:setup` | Register for the leaderboard |
| `/tokenboard:status` | Check your stats and rank |

## Stack

- Python 3.10+, FastMCP
- Reads `~/.claude/stats-cache.json` (local, read-only)
- Uploads to `https://tokenboard.softwaresoftware.dev/api`
- Local config at `~/.tokenboard/config.json`

## How It Works

1. **MCP server** (`server.py`) — On startup, spawns a background thread that reads stats, computes cost, and uploads to the leaderboard. Silent failure. Also exposes 3 tools for manual interaction.
2. **Calculator** (`calculator.py`) — Parses stats-cache.json, applies per-model pricing, returns aggregate totals.
3. **Uploader** (`uploader.py`) — HTTP client that POSTs to the tokenboard API.
4. **Store** (`store.py`) — Local JSON config for registration state and upload deduplication.

## MCP Tools

- `tokenboard_register(display_name)` — Register for the leaderboard
- `tokenboard_status()` — Show local stats and last upload
- `tokenboard_refresh()` — Force re-upload current stats

## Development

```bash
make test     # run pytest suite
make dev      # launch Claude Code with this plugin loaded
```

---
name: setup
description: Register for the tokenboard leaderboard
---

# tokenboard:setup — Join the Leaderboard

## Steps

1. Ask the user for their **display name** — this is how they'll appear on the leaderboard. Must be unique, max 50 characters.

2. Call the `tokenboard_register` MCP tool with their chosen display name.

3. If registration succeeds, confirm:
   - Their display name
   - Their current rank
   - That stats will upload automatically on every future session
   - Link to the leaderboard: https://tokenboard.nov.solutions

4. If the name is taken (409 error), ask them to pick a different name and retry.

5. If they're already registered, let them know and show their current status by calling `tokenboard_status`.

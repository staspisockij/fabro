Goal: Build a terminal-based FreeCell solitaire game in Python

## Completed stages
- **expand_spec**: succeeded
  - Model: gemini-3.5-flash, 85.9k tokens in / 8.3k out
  - Files: /home/daytona/workspace/fabro/.ai/card-game-spec.md, /home/daytona/workspace/fabro/status.json
- **impl_setup**: succeeded
  - Model: gemini-3.5-flash, 144.1k tokens in / 6.8k out
  - Files: /home/daytona/workspace/fabro/card-game-app/README.md, /home/daytona/workspace/fabro/card-game-app/main.py, /home/daytona/workspace/fabro/card-game-app/pyproject.toml, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/__init__.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/domain.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/tui.py, /home/daytona/workspace/fabro/card-game-app/tests/__init__.py, /home/daytona/workspace/fabro/card-game-app/tests/test_domain.py, /home/daytona/workspace/fabro/status.json


Verify setup for the card game app.

Check:
1. card-game-app/pyproject.toml exists
2. card-game-app/main.py exists
3. card-game-app/src/card_game_tui exists
4. Python files compile

Run:
cd card-game-app && python3 -m py_compile main.py src/card_game_tui/*.py

Write findings to .ai/verify_setup.md.
Write status.json at workspace root: outcome=succeeded if all checks pass, outcome=failed with failure_reason otherwise.
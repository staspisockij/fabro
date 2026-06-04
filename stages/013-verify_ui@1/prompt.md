Goal: Build a terminal-based FreeCell solitaire game in Python

## Completed stages
- **expand_spec**: succeeded
  - Model: gemini-3.5-flash, 85.9k tokens in / 8.3k out
  - Files: /home/daytona/workspace/fabro/.ai/card-game-spec.md, /home/daytona/workspace/fabro/status.json
- **impl_setup**: succeeded
  - Model: gemini-3.5-flash, 144.1k tokens in / 6.8k out
  - Files: /home/daytona/workspace/fabro/card-game-app/README.md, /home/daytona/workspace/fabro/card-game-app/main.py, /home/daytona/workspace/fabro/card-game-app/pyproject.toml, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/__init__.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/domain.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/tui.py, /home/daytona/workspace/fabro/card-game-app/tests/__init__.py, /home/daytona/workspace/fabro/card-game-app/tests/test_domain.py, /home/daytona/workspace/fabro/status.json
- **verify_setup**: succeeded
  - Model: gemini-3.5-flash, 185.9k tokens in / 2.2k out
  - Files: /home/daytona/workspace/fabro/.ai/verify_setup.md, /home/daytona/workspace/fabro/status.json
- **check_setup**: succeeded
- **impl_data**: succeeded
  - Model: gemini-3.5-flash, 179.9k tokens in / 32.0k out
  - Files: /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/domain.py, /home/daytona/workspace/fabro/card-game-app/tests/test_domain.py, /home/daytona/workspace/fabro/status.json
- **verify_data**: succeeded
  - Model: gemini-3.5-flash, 140.2k tokens in / 3.2k out
  - Files: /home/daytona/workspace/fabro/.ai/verify_data.md, /home/daytona/workspace/fabro/status.json
- **check_data**: succeeded
- **impl_logic**: succeeded
  - Model: gemini-3.5-flash, 177.0k tokens in / 8.2k out
  - Files: /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/domain.py, /home/daytona/workspace/fabro/card-game-app/tests/test_domain.py, /home/daytona/workspace/fabro/status.json
- **verify_logic**: succeeded
  - Model: gemini-3.5-flash, 151.0k tokens in / 10.0k out
  - Files: /home/daytona/workspace/fabro/.ai/verify_logic.md, /home/daytona/workspace/fabro/status.json
- **check_logic**: succeeded
- **impl_ui**: succeeded
  - Model: gemini-3.5-flash, 263.6k tokens in / 27.0k out
  - Files: /home/daytona/workspace/fabro/card-game-app/main.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/render.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/tui.py, /home/daytona/workspace/fabro/card-game-app/tests/test_render.py, /home/daytona/workspace/fabro/card-game-app/tests/test_tui.py, /home/daytona/workspace/fabro/status.json


Verify the terminal UI.

Run:
cd card-game-app && python3 -m pytest tests/ -v && python3 -m py_compile main.py src/card_game_tui/*.py && python3 main.py --smoke

Check that:
- main.py can start smoke mode
- UI module imports without requiring an interactive terminal
- Board rendering helpers have tests or smoke coverage
- Controls are documented in README.md

Write findings to .ai/verify_ui.md.
Write status.json at workspace root: outcome=succeeded if all checks pass, outcome=failed with failure_reason otherwise.
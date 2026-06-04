Goal: Build a terminal-based FreeCell solitaire game in Python

## Completed stages
- **expand_spec**: succeeded
  - Model: gemini-3.5-flash, 91.5k tokens in / 10.9k out
  - Files: .ai/card-game-spec.md, status.json
- **impl_setup**: succeeded
  - Model: gemini-3.5-flash, 174.8k tokens in / 9.7k out
  - Files: /home/daytona/workspace/fabro/card-game-app/README.md, /home/daytona/workspace/fabro/card-game-app/main.py, /home/daytona/workspace/fabro/card-game-app/pyproject.toml, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/__init__.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/engine.py, /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/tui.py, /home/daytona/workspace/fabro/card-game-app/tests/__init__.py, /home/daytona/workspace/fabro/card-game-app/tests/test_card.py, /home/daytona/workspace/fabro/card-game-app/tests/test_integration.py, /home/daytona/workspace/fabro/card-game-app/tests/test_rules.py, /home/daytona/workspace/fabro/card-game-app/tests/test_state.py, /home/daytona/workspace/fabro/status.json
- **verify_setup**: succeeded
  - Model: gemini-3.5-flash, 148.1k tokens in / 2.4k out
  - Files: /home/daytona/workspace/fabro/.ai/verify_setup.md, /home/daytona/workspace/fabro/status.json
- **check_setup**: succeeded
- **impl_data**: succeeded
  - Model: gemini-3.5-flash, 258.5k tokens in / 19.8k out
  - Files: /home/daytona/workspace/fabro/card-game-app/src/card_game_tui/engine.py, /home/daytona/workspace/fabro/card-game-app/tests/test_rules.py, /home/daytona/workspace/fabro/card-game-app/tests/test_state.py, /home/daytona/workspace/fabro/status.json
- **verify_data**: succeeded
  - Model: gemini-3.5-flash, 134.1k tokens in / 3.8k out
  - Files: /home/daytona/workspace/fabro/.ai/verify_data.md, /home/daytona/workspace/fabro/status.json
- **check_data**: succeeded


Read .ai/card-game-spec.md and the current card-game-app implementation.

Implement the requested card game's rules:
- Initial setup/deal where applicable
- Move/action validation
- Auto-complete or helper actions where applicable
- Win/loss condition
- Undo

Add tests for legal actions, illegal actions, win/loss detection, and edge cases.

Run:
cd card-game-app && python3 -m pytest tests/ -v

Write status.json at workspace root: outcome=succeeded if all tests pass and rules are implemented, outcome=failed with failure_reason otherwise.
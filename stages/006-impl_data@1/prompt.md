Goal: Build a terminal-based Klondike solitaire game in Python with a curses TUI

## Completed stages
- **expand_spec**: succeeded
  - Model: gemini-3.5-flash, 140.8k tokens in / 24.8k out
  - Files: /home/daytona/workspace/fabro/.ai/solitaire-spec.md, /home/daytona/workspace/fabro/solitaire-app/game.py, /home/daytona/workspace/fabro/solitaire-app/main.py, /home/daytona/workspace/fabro/solitaire-app/test_game.py, /home/daytona/workspace/fabro/solitaire-app/ui.py, /home/daytona/workspace/fabro/status.json
- **impl_setup**: succeeded
  - Model: gemini-3.5-flash, 148.0k tokens in / 18.3k out
  - Files: /home/daytona/workspace/fabro/solitaire-app/README.md, /home/daytona/workspace/fabro/solitaire-app/main.py, /home/daytona/workspace/fabro/solitaire-app/pyproject.toml, /home/daytona/workspace/fabro/solitaire-app/src/solitaire_tui/__init__.py, /home/daytona/workspace/fabro/solitaire-app/src/solitaire_tui/game.py, /home/daytona/workspace/fabro/solitaire-app/src/solitaire_tui/ui.py, /home/daytona/workspace/fabro/solitaire-app/tests/__init__.py, /home/daytona/workspace/fabro/solitaire-app/tests/test_game.py, /home/daytona/workspace/fabro/status.json
- **verify_setup**: succeeded
  - Model: gemini-3.5-flash, 154.6k tokens in / 2.2k out
  - Files: /home/daytona/workspace/fabro/.ai/verify_setup.md, /home/daytona/workspace/fabro/status.json
- **check_setup**: succeeded


Read .ai/solitaire-spec.md.

Implement core data structures under solitaire-app/src/solitaire_tui/:
- Card with rank, suit, face_up, color, display helpers
- Deck with standard 52-card creation and shuffle
- Pile types or clear pile abstractions for tableau, foundation, stock, and waste
- GameState container with initial deal

Add focused unit tests under solitaire-app/tests/.

Run:
cd solitaire-app && python3 -m pytest tests/ -v

Write status.json at workspace root: outcome=succeeded if tests pass and the data model is implemented, outcome=failed with failure_reason otherwise.
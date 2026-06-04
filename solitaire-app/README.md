# Terminal Klondike Solitaire

A terminal-based Klondike Solitaire game in Python 3.11+ using the standard `curses` library.

## Features
- Standard Draw-One Klondike Solitaire rules
- Fully keyboard-driven curses TUI
- Unlimited Undo functionality
- Auto-move to foundations
- Fully testable pure Python core game engine

## Installation & Running

To run the game, use:
```bash
python3 main.py
```

To run smoke tests (non-interactive):
```bash
python3 main.py --smoke
```

## Testing
To run the automated tests using pytest:
```bash
cd solitaire-app
pytest
```

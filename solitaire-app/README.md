# Python Klondike Solitaire Curses TUI

A terminal-based Klondike Solitaire game in Python using the standard library `curses` module, featuring full game rules, multi-step undo history, win detection, an interactive TUI, and automated smoke & unit tests.

## Features

- **Pure Python Game Engine**: Decoupled game rules, move validation, and state history management.
- **TUI Controls**: Intuitive grid navigation using Arrow Keys or WASD.
- **Card Selection & Dragging**: Visual highlight of selected cards or multi-card stacks when dragging.
- **Full Solitaire Rules**: Stock and waste drawing/recycling, tableau piles, foundation piles (building up Aces to Kings), and auto-reveal of face-down cards.
- **Multi-Step Undo**: Unlimited undo states.
- **Color Support**: Red suit coloration and distinct styling for highlights/selections.
- **Robust Verification**: Automated unit test suite via `pytest` and a headless `--smoke` test.

---

## Installation & Setup

No external dependencies are required to run the game, as it uses Python's standard `curses` library. To run tests, `pytest` is required.

### 1. Run Unit Tests

Execute the following to run all unit tests for game rules, state changes, and win detection:

```bash
cd solitaire-app
python3 -m pytest tests/ -v
```

### 2. Run Non-Interactive Smoke Test

Run a programmatically simulated full game simulation that validates drawing, moving, undos, and win detection:

```bash
cd solitaire-app
python3 main.py --smoke
```

### 3. Play the Game

Launch the interactive curses terminal interface:

```bash
cd solitaire-app
python3 main.py
```

*Note: Ensure your terminal window is at least 80 columns wide and 24 rows high.*

---

## Control Scheme

- **Arrow Keys** or **WASD**: Move the cursor between areas:
  - **Top Row**: Stock (far-left), Waste, and the 4 Foundations (♠, ♥, ♦, ♣).
  - **Tableau Row**: The 7 column piles. Inside columns, use Up/Down keys to choose which card to select.
- **Space** or **Enter**:
  - If cursor is on **Stock**: Draw a card.
  - If no card is selected: Select the current card or stack.
  - If a stack is already selected: Move the selected cards to the current cursor position.
- **Esc** or **'c' / 'C'**: Cancel the current selection.
- **'u' / 'U'**: Undo the last move.
- **'r' / 'R'**: Restart / deal a new game.
- **'q' / 'Q'**: Quit the game.

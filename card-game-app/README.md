# Terminal-Based Spider Solitaire Game

A terminal-based Spider Solitaire game written in Python using the `curses` standard library.

## Features

- **Standard Spider Solitaire Rules**: Play with 104 cards, 10 tableau columns, and 5 stock deals.
- **Multiple Difficulties**:
  - **1 Suit (Easy)**: All cards are Spades (♠).
  - **2 Suits (Medium)**: Spades (♠) and Hearts (♥).
  - **4 Suits (Hard)**: Spades (♠), Hearts (♥), Diamonds (♦), and Clubs (♣).
- **Smooth Cursor Navigation**: Move around the tableau and select cards seamlessly with arrow keys or WASD.
- **Color Coding**: Suit-colored rendering (Red for Hearts/Diamonds, White/Default for Spades/Clubs) and distinct highlight styles for selection and active cursors.
- **Full Undo/Redo**: Revert moves with `U`.
- **Responsive Layout**: Adapts gracefully to different terminal heights and widths.
- **Smoke Test Mode**: Run programmatic assertions and verify game correctness in a completely non-interactive terminal environment with `--smoke`.

## Installation & Setup

Ensure you have Python 3.10+ installed.

```bash
cd card-game-app
pip install -e .
```

## Running the Game

To play the interactive curses game:
```bash
python3 main.py
```

To run the automated smoke test verification:
```bash
python3 main.py --smoke
```

## Running Tests

Run the test suite using `pytest`:
```bash
python3 -m pytest tests/ -v
```

## Controls

- **Left/Right Arrows (H/L, A/D)**: Move cursor left/right across columns.
- **Up/Down Arrows (K/J, W/S)**: Move cursor up/down within a column to select starting card of a sequence.
- **Space/Enter**: Select starting card of a sequence, or drop sequence onto a destination column.
- **S**: Deal a round of 10 cards from the Stock.
- **U**: Undo the last move.
- **R**: Restart game (allows choosing a new difficulty).
- **Q / ESC**: Quit the game.
- **C**: Clear current selection.

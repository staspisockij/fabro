# Implementation Plan - Terminal FreeCell Solitaire in Python

This document outlines the design and implementation details for a terminal-based FreeCell Solitaire game in Python using the `curses` standard library.

## 1. Game Rules & Logic Constraints

FreeCell is a standard 52-card solitaire game played with all cards dealt face-up.

### Data Structures
- **Card**:
  - `suit`: `'C'` (Clubs), `'D'` (Diamonds), `'H'` (Hearts), `'S'` (Spades)
  - `rank`: `1` (Ace) to `13` (King)
  - `color`: `'R'` (Red) for `D`/`H`, `'B'` (Black) for `C`/`S`
  - String representation: e.g., `"10♦"`, `"A♥"`, `"K♠"`, `"2♣"`
- **GameState**:
  - `tableaux`: 8 columns. Columns 1-4 start with 7 cards, columns 5-8 with 6 cards.
  - `freecells`: 4 slots, initially empty (`None`).
  - `foundations`: Dict mapping suit to current max rank (initially `0` for all suits).
  - `history`: Undo stack storing snapshots or reverse-moves for full undo support.

### Move Validation Rules
1. **To FreeCell**: Any single card can be moved to an empty FreeCell.
2. **To Foundation**: A card of rank $R$ and suit $S$ can be moved to its foundation if the foundation's current rank is $R-1$.
3. **To Tableau**:
   - A card (or sequence) can be moved to a tableau column if the target column is empty, OR if the target's bottom card is of opposite color and exactly 1 rank higher.
   - **Multi-Card Moves**: Moving a sequence of $K$ cards is permitted if:
     - The sequence is sorted descending and alternates colors.
     - The maximum size $K$ does not exceed standard FreeCell storage constraints:
       $$\text{Max Movable} = (1 + \text{Empty FreeCells}) \times 2^{\text{Empty Tableau Columns}}$$
       *(If moving to an empty column, that destination column does not count as "empty" in the power exponent).*

### Auto-Collect (Auto-Home) Rules
To enhance playability, safe cards are automatically moved to foundations:
- A card of suit $S$ and rank $R$ is safe to auto-collect if:
  - All cards of opposite color and rank $< R$ are already in the foundations.
  - *Example*: Hearts 3 (♥3) is safe if Spades 2 (♠2) and Clubs 2 (♣2) are in the foundations.

---

## 2. Terminal UI & Curses Rendering

The interface uses standard-library `curses` with full color support.

### UI Layout Grid
- **Top Row**: 4 FreeCells on the left, 4 Foundation Piles on the right.
- **Middle Divider**: Simple line showing current game seed or stats.
- **Bottom Row**: 8 Tableau Columns rendered vertically.
- **Status/Command Bar**: Highlights selected cards, prompts for inputs, and shows error messages/victory celebrations.

### Color Coding
- **Red suits (♦, ♥)**: Rendered in Red color pair.
- **Black suits (♠, ♣)**: Rendered in White/Cyan color pair.
- **UI Elements / Selection**: Highlighted using bold or distinct background/yellow colors.

---

## 3. Keyboard Input & Move Workflow

We implement a two-step keyboard command sequence:
1. **Source Selection**:
   - `1` to `8`: Select Tableau column 1 to 8.
   - `q`, `w`, `e`, `r`: Select FreeCell 1, 2, 3, or 4.
2. **Destination Selection**:
   - `1` to `8`: Select destination Tableau.
   - `q`, `w`, `e`, `r`: Select destination FreeCell.
   - `f` (or `space`): Move selected card to the appropriate Foundation pile automatically.
3. **General Commands**:
   - `u`: Undo last move.
   - `s`: Force auto-collect safe cards.
   - `n`: Start a new game (prompt for confirmation).
   - `Esc` or `x`: Exit game.

---

## 4. Non-Interactive Demo Mode (`--smoke`)

To support headless CI environment verification:
- Running `python3 main.py --smoke` bypasses the `curses` interface entirely.
- It instantiates a fixed seed game (using standard `random` seeding).
- Simulates a predefined sequence of valid moves.
- Validates game win-conditions/state-transitions.
- Prints the intermediate states as ASCII text to stdout.
- Exits with `0` on success, or non-zero on failure.

---

## 5. Directory Structure & App Files

All files will be placed under `card-game-app/`:
```
card-game-app/
├── main.py        # CLI entry point (handles --smoke vs curses UI)
├── game.py        # Game mechanics, Card, Deck, GameState, and rule validator
├── ui.py          # Curses layout drawing, keyboard inputs, and event loops
└── test_game.py   # Automated unit tests for rules, state, and moves
```

---

## 6. Testing Strategy

- **Unit Tests**:
  - Valid and invalid moves (to empty columns, correct color alternating, foundation stacking).
  - Multi-card sequence calculations.
  - Auto-collect safety checks.
  - Win state verification.
- **Smoke Tests**: Run via `python3 main.py --smoke` to verify the execution flow without curses.
- **Format / Linting**: Checked and formatted before submission.

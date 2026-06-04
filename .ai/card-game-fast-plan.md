# Implementation Plan - Terminal FreeCell Solitaire in Python

This document outlines the design and implementation strategy for a terminal-based FreeCell solitaire game. The application will be located under `card-game-app/` and will support both an interactive curses UI and a non-interactive `--smoke` mode.

## 1. Game Rules & Data Structures

### Card Model
- **Suit**: Spades (♠), Hearts (♥), Diamonds (♦), Clubs (♣).
- **Rank**: Ace (1) to King (13).
- **Color**: Red (Hearts, Diamonds) or Black (Spades, Clubs).
- **Representation**: Displayed as `[A♠]`, `[10♦]`, `[K♣]`, etc. (with red color highlighting for Heart/Diamond suits).

### Board State
- **Cascades (Tableau)**: 8 columns of cards.
  - Initially, 52 cards are dealt face-up: 7 cards in the first 4 columns, 6 cards in the remaining 4.
- **Free Cells**: 4 slots, each holding at most 1 card.
- **Foundations**: 4 piles, one for each suit, built up from Ace to King.
- **Move History**: A stack of previous board states to support full **Undo** (`U`).

### Move Validation Rules
1. **To Free Cell**: Any single card can be moved to an empty Free Cell.
2. **To Foundation**:
   - An Ace can be moved to an empty Foundation pile.
   - A card of rank $R$ and suit $S$ can be moved to Foundation pile of suit $S$ if the top card is of rank $R-1$.
3. **To Cascade**:
   - A card of rank $R$ and color $C$ can be placed on a cascade's bottom card of rank $R+1$ and opposite color.
   - Any card can be placed on an empty cascade.
4. **Sequence Moves**:
   - Moving a packed sequence of size $L$ from Cascade A to Cascade B is allowed if the cards are sorted in alternating colors and descending ranks, and the number of cards does not exceed the maximum allowed sequence limit:
     $$M = (F + 1) \times 2^E$$
     where $F$ is the number of empty Free Cells, and $E$ is the number of empty Cascades (excluding source and destination).

---

## 2. Terminal Rendering & Curses

The UI is built using Python's standard `curses` library.

### Layout (Minimum 80x24 characters)
- **Header**: Game title, Moves counter, Time elapsed, and Status line.
- **Top Panel**:
  - **Free Cells**: Labelled `Q`, `W`, `E`, `R`.
  - **Foundations**: Labelled `A`, `S`, `D`, `F`.
- **Main Panel**:
  - **Cascades**: 8 columns labelled `1` to `8` below them. Cards are stacked vertically with overlapping cards.
- **Footer**: Instructions & legend:
  - `Src Key` + `Dest Key` to move.
  - `U`: Undo, `C`: Auto-collect, `R`: Restart, `N`: New Game, `Q`/`Esc`: Quit.

### Color Coding
- **Red cards** (Hearts, Diamonds): Rendered using a red-on-black or red-on-default color pair.
- **Black cards** (Spades, Clubs): Rendered using default/white-on-black text.
- **Selected Card**: Highlighted with reverse video or a distinct color pair.

---

## 3. Input Handling & Interactive Loop

The main loop:
1. Render current state.
2. If first key is pressed (Source):
   - Highlight selection.
   - Wait for second key (Destination).
3. If both keys are valid, validate the move:
   - If valid, execute the move, record state to undo history, and trigger an auto-collect check.
   - If invalid, show an error status.
4. If special key is pressed:
   - `U`: Pop from undo history.
   - `C`: Scan cascades/free cells for any cards that can safely be moved to foundations.
   - `R`: Reset current game to starting layout.
   - `N`: Deal a completely new random game.
   - `Q` / `Esc`: Exit game.

---

## 4. Non-Interactive Demo (`--smoke` Mode)

To support automated validation and CI:
- Running `python3 main.py --smoke` executes a non-interactive smoke test.
- It will:
  1. Initialize a deterministic deck (seeded RNG or fixed sequence).
  2. Perform a series of valid moves.
  3. Validate move logic and status updates.
  4. Ensure no exceptions are thrown.
  5. Print a success message and exit with code `0`.

---

## 5. Test Strategy

1. **Unit Tests**:
   - Card representation & colors.
   - Board state initialization (correct count of cards in cascades, free cells, foundations).
   - Move validation logic (valid/invalid cascade-to-cascade, freecell-to-cascade, cascade-to-foundation).
   - Multi-card sequence move calculation.
2. **Integration Tests**:
   - Smoke test running end-to-end moves without starting curses.

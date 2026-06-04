I have successfully completed the implementation of the FreeCell solitaire game data models and state engine according to the technical specification, added a comprehensive focused unit test suite, and verified that all tests pass perfectly.

### Summary of Changes

1. **Pure Domain Data Model & State Engine (`card-game-app/src/card_game_tui/domain.py`)**:
   - Implemented `Suit`, `Rank`, and `Card` representations.
   - Built the `Deck` class supporting deterministic seeding and standard 52-card dealing.
   - Designed the `Position` representation, covering tableau columns (0–7), free cells (0–3), and foundations (0–3).
   - Designed `MoveRecord` with full support for tracking regular moves and recursive `auto_moves` (auto-homing).
   - Implemented `GameState` managing all piles, validations (`validate_move`), executions (`execute_move`), full asymmetric/nested undo/redo, and win-state detection.
   - Implemented **Auto-Homing** rules exactly as specified: cards are moved automatically to foundations if and only if they are legal moves and all cards of the opposite color of lower ranks have already been homed.

2. **Comprehensive Headless Unit Tests (`card-game-app/tests/test_domain.py`)**:
   - Built a comprehensive unit test suite covering:
     - Standard 52-card deck deal correctness.
     - Deterministic seeding verification.
     - Moves to and validations of Free Cells.
     - Moves to and validations of Foundations.
     - Single card move rules on the Tableau (descending rank, alternating colors).
     - Sequence/multi-card moves Tableau-to-Tableau obeying the rules & formula: `(1 + Empty Free Cells) * 2^(Empty Tableau Columns)` with destination empty-column exception.
     - Core Auto-Homing logic.
     - Perfect full undo/redo capabilities, including reverting auto-homing sequences.
     - Winning state detection.

3. **Status Validation**:
   - All 13 unit tests passed flawlessly inside the Python testing framework.
   - The CLI non-interactive `--smoke` mode executes perfectly.
   - Wrote `status.json` with `outcome=succeeded`.
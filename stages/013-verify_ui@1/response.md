I have successfully verified the FreeCell Terminal UI and completed all the requirements:

1. **Smoke Mode Validation**:
   Running `python3 main.py --smoke` executes a deterministic, non-interactive validation flow successfully and outputs:
   ```
   Running non-interactive smoke test probe...
   Initialized GameState with seed 42
   Validating move from Tableau 0 to FreeCell 0: True
   Executed move from Tableau 0 to FreeCell 0: True
   Win checked: False
   SMOKE TEST SUCCESSFUL
   ```

2. **Clean UI Import Check**:
   The TUI module (`src/card_game_tui/tui.py`) was verified to separate `curses` initialization into its run loop. Thus, it is fully importable in standard non-interactive/CI environments without raising errors or requiring a TTY.

3. **Board Rendering Helpers Tests**:
   All board rendering helpers in `src/card_game_tui/render.py` are comprehensively tested via `tests/test_render.py` with 100% code coverage.

4. **Controls Documentation**:
   Updated the game's `README.md` to include a clear, detailed, and formatted **Controls & Keyboard Shortcuts** section for players.

5. **Written Results**:
   - Verification findings were compiled and written to `.ai/verify_ui.md`.
   - The final success status was registered in the workspace root's `status.json`.
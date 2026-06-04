import argparse
import sys
import time

# Ensure engine can be imported from same directory
from engine import FreeCellGame, Card, SUITS, SUIT_COLORS, RANK_NAMES

def run_smoke_test():
    """
    Non-interactive smoke test.
    Loads a deterministic game (seed=42), performs a sequence of valid moves,
    verifies logic, undoes, and verifies state correctness.
    """
    print("Running non-interactive FreeCell smoke test...")
    
    # 1. Initialize game with a seed
    game = FreeCellGame(seed=42)
    print(f"Game initialized with seed 42. Moves: {game.move_count}")
    
    # Check initial counts
    total_cards = sum(len(col) for col in game.cascades)
    assert total_cards == 52, f"Expected 52 cards, got {total_cards}"
    assert len(game.cascades[0]) == 7, "Cascade 0 should have 7 cards"
    assert len(game.cascades[4]) == 6, "Cascade 4 should have 6 cards"
    print("Initial card counts and distribution verified successfully.")

    # 2. Perform a valid move (bottom card of Cascade 0 to Free Cell 0)
    card_0_bottom = game.cascades[0][-1]
    print(f"Moving bottom card of Cascade 0 ({card_0_bottom}) to Free Cell 0.")
    success, msg = game.validate_and_move('cascade', 0, 'freecell', 0)
    assert success, f"Expected move to succeed, but failed: {msg}"
    assert game.free_cells[0] == card_0_bottom, "Card was not placed in Free Cell 0"
    assert len(game.cascades[0]) == 6, f"Expected Cascade 0 to have 6 cards, got {len(game.cascades[0])}"
    assert game.move_count == 1, f"Expected move count to be 1, got {game.move_count}"
    print("First move completed and verified successfully.")

    # 3. Perform another valid move (bottom card of Cascade 1 to Free Cell 1)
    card_1_bottom = game.cascades[1][-1]
    print(f"Moving bottom card of Cascade 1 ({card_1_bottom}) to Free Cell 1.")
    success, msg = game.validate_and_move('cascade', 1, 'freecell', 1)
    assert success, f"Expected move to succeed, but failed: {msg}"
    assert game.free_cells[1] == card_1_bottom, "Card was not placed in Free Cell 1"
    assert len(game.cascades[1]) == 6, f"Expected Cascade 1 to have 6 cards, got {len(game.cascades[1])}"
    assert game.move_count == 2, f"Expected move count to be 2, got {game.move_count}"
    print("Second move completed and verified successfully.")

    # 4. Perform an invalid move (moving to occupied free cell 0)
    print("Testing invalid move: Cascade 2 bottom to occupied Free Cell 0.")
    success, msg = game.validate_and_move('cascade', 2, 'freecell', 0)
    assert not success, "Expected move to fail, but it succeeded!"
    print(f"Invalid move correctly rejected. Error message: '{msg}'")

    # 5. Verify Undo functionality
    print("Undoing second move...")
    undo_success = game.undo()
    assert undo_success, "Undo failed"
    assert game.free_cells[1] is None, "Expected Free Cell 1 to be empty after undo"
    assert len(game.cascades[1]) == 7, "Expected Cascade 1 to restore its card"
    assert game.cascades[1][-1] == card_1_bottom, "Expected original card to return to bottom of Cascade 1"
    assert game.move_count == 1, f"Expected move count to revert to 1, got {game.move_count}"
    print("Undo functionality verified successfully.")

    # 6. Verify safe auto-collect (Aces are always auto-collected)
    # We can programmatically deal a game, find where Ace of Spades is,
    # and if it is at the bottom of a cascade, it should auto-collect immediately.
    # Let's find a seed where an Ace is at the bottom of a cascade, or construct one.
    # To keep it robust and independent of seeds, let's construct a small scenario.
    print("Verifying auto-collect of Aces...")
    game = FreeCellGame(seed=42)
    # Clear out an Ace manually to the bottom of cascade 0
    ace_spades = Card('S', 1)
    game.cascades[0].append(ace_spades)
    # Trigger auto-collect
    game.auto_collect()
    # Spades foundation is index 0. It should now contain the Ace of Spades.
    assert len(game.foundations[0]) >= 1, "Expected Ace of Spades to be auto-collected to foundation 0"
    assert game.foundations[0][0] == ace_spades, "Foundation 0's first card should be Ace of Spades"
    print("Auto-collect logic verified successfully.")

    print("\nSmoke test PASSED successfully!")
    sys.exit(0)


def run_curses_ui():
    """
    Launches the interactive curses terminal interface.
    """
    try:
        import curses
    except ImportError:
        print("Error: The standard-library 'curses' module is not available on this system.")
        sys.exit(1)

    def draw_card(stdscr, y, x, card, selected=False):
        if card is None:
            stdscr.addstr(y, x, "[   ]", curses.color_pair(5))
            return

        # Select color pair based on card color
        if card.color == 'red':
            color_pair = curses.color_pair(1)  # Red text
        else:
            color_pair = curses.color_pair(2)  # White/Black text

        if selected:
            color_pair = color_pair | curses.A_REVERSE

        rank_str = RANK_NAMES[card.rank]
        suit_sym = SUITS[card.suit]
        card_text = f"{rank_str}{suit_sym}"
        
        # Pad to exactly 3 characters for uniform alignment
        if len(card_text) == 2:
            card_text = " " + card_text

        stdscr.addstr(y, x, "[", curses.color_pair(5))
        stdscr.addstr(y, x + 1, card_text, color_pair)
        stdscr.addstr(y, x + 4, "]", curses.color_pair(5))

    def draw_foundation_placeholder(stdscr, y, x, suit):
        suit_sym = SUITS[suit]
        if SUIT_COLORS[suit] == 'red':
            color = curses.color_pair(1)
        else:
            color = curses.color_pair(2)
        stdscr.addstr(y, x, "[", curses.color_pair(5))
        stdscr.addstr(y, x + 1, f" {suit_sym} ", color | curses.A_DIM)
        stdscr.addstr(y, x + 4, "]", curses.color_pair(5))

    def curses_main(stdscr):
        # Configure curses environment
        curses.curs_set(0) # Hide blinking text cursor
        stdscr.timeout(500) # Update elapsed time every 500ms

        # Color setup
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)     # Red suits
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # Black/white suits
        curses.init_pair(3, curses.COLOR_GREEN, -1)   # Green labels
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Highlight / Warning
        curses.init_pair(5, curses.COLOR_CYAN, -1)    # Brackets/borders

        # Initialize a random game
        current_seed = random_seed()
        game = FreeCellGame(seed=current_seed)
        start_time = time.time()
        
        # Selection states
        src_type = None
        src_idx = None
        status_msg = "Game started! Enter Source key..."
        status_color_pair = curses.color_pair(3)

        # Key mappings
        key_to_pile = {
            'q': ('freecell', 0), 'w': ('freecell', 1), 'e': ('freecell', 2), 'r': ('freecell', 3),
            'a': ('foundation', 0), 's': ('foundation', 1), 'd': ('foundation', 2), 'f': ('foundation', 3),
            '1': ('cascade', 0), '2': ('cascade', 1), '3': ('cascade', 2), '4': ('cascade', 3),
            '5': ('cascade', 4), '6': ('cascade', 5), '7': ('cascade', 6), '8': ('cascade', 7)
        }

        while True:
            # Check terminal size
            height, width = stdscr.getmaxyx()
            if width < 80 or height < 24:
                stdscr.clear()
                stdscr.addstr(0, 0, "Terminal must be at least 80x24.", curses.color_pair(4))
                stdscr.addstr(1, 0, f"Current size: {width}x{height}", curses.color_pair(2))
                stdscr.addstr(3, 0, "Please resize your terminal window to continue.", curses.color_pair(2))
                stdscr.refresh()
                # Wait for resize
                ch = stdscr.getch()
                if ch in [ord('q'), ord('Q'), 27]: # ESC or Q
                    break
                continue

            stdscr.clear()

            # --- RENDER HEADER ---
            stdscr.addstr(0, 0, "┌" + "─" * 78 + "┐", curses.color_pair(5))
            
            # Formulate header statistics
            elapsed_sec = int(time.time() - start_time)
            min_part = elapsed_sec // 60
            sec_part = elapsed_sec % 60
            time_str = f"{min_part:02d}:{sec_part:02d}"
            
            stats_line = f" FREECELL SOLITAIRE   |   Moves: {game.move_count:<3}   |   Time: {time_str}   |   Seed: {current_seed:<10}"
            stdscr.addstr(1, 0, "│" + stats_line.ljust(78) + "│", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(2, 0, "└" + "─" * 78 + "┘", curses.color_pair(5))

            # --- RENDER TOP SECTION (Free Cells & Foundations) ---
            stdscr.addstr(4, 2, "FREE CELLS (Q-R)", curses.color_pair(3))
            stdscr.addstr(4, 40, "FOUNDATIONS (A-F)", curses.color_pair(3))

            # Render Labels for Free Cells
            labels_fc = ['Q', 'W', 'E', 'R']
            for i, label in enumerate(labels_fc):
                is_selected = (src_type == 'freecell' and src_idx == i)
                color = curses.color_pair(4) if is_selected else curses.color_pair(3)
                stdscr.addstr(5, 4 + i * 8, label, color | (curses.A_UNDERLINE if is_selected else 0))

            # Render Free Cells
            for i, card in enumerate(game.free_cells):
                is_selected = (src_type == 'freecell' and src_idx == i)
                draw_card(stdscr, 6, 2 + i * 8, card, selected=is_selected)

            # Render Labels for Foundations
            labels_fnd = ['A (♠)', 'S (♥)', 'D (♦)', 'F (♣)']
            for i, label in enumerate(labels_fnd):
                is_selected = (src_type == 'foundation' and src_idx == i)
                color = curses.color_pair(4) if is_selected else curses.color_pair(3)
                stdscr.addstr(5, 41 + i * 9, label, color)

            # Render Foundations
            for i, pile in enumerate(game.foundations):
                is_selected = (src_type == 'foundation' and src_idx == i)
                if not pile:
                    draw_foundation_placeholder(stdscr, 6, 40 + i * 9, game.foundation_suits[i])
                else:
                    draw_card(stdscr, 6, 40 + i * 9, pile[-1], selected=is_selected)

            # --- RENDER CASCADES (1-8) ---
            stdscr.addstr(9, 2, "CASCADES (1-8)", curses.color_pair(3))

            # Print cascade header labels
            for i in range(8):
                is_selected = (src_type == 'cascade' and src_idx == i)
                color = curses.color_pair(4) if is_selected else curses.color_pair(3)
                label_text = f"({i+1})"
                stdscr.addstr(10, 4 + i * 9, label_text, color | (curses.A_UNDERLINE if is_selected else 0))

            # Print the cards in each cascade
            max_col_height = max(len(col) for col in game.cascades)
            # Render up to the height of the terminal dynamically
            visible_rows = height - 16 # Reserve rows for headers/footers
            for row_idx in range(max_col_height):
                if row_idx >= visible_rows:
                    # Render indicators that more cards are hidden
                    stdscr.addstr(11 + visible_rows, 2, "... and more cards below ...", curses.color_pair(4))
                    break

                for col_idx in range(8):
                    cascade = game.cascades[col_idx]
                    if row_idx < len(cascade):
                        card = cascade[row_idx]
                        # A card is selected if it is the source and we are highlighting it.
                        # Note: for cascades, we highlight the source column's bottom cards/sequence if selected.
                        is_selected = False
                        if src_type == 'cascade' and src_idx == col_idx:
                            # Highlight the bottom sequence or bottom card
                            seq = game.get_bottom_sequence(cascade)
                            if card in seq:
                                is_selected = True

                        draw_card(stdscr, 11 + row_idx, 2 + col_idx * 9, card, selected=is_selected)

            # --- RENDER STATUS & FOOTER ---
            # Print status message
            status_y = height - 4
            stdscr.addstr(status_y, 2, "Status: ", curses.color_pair(3))
            stdscr.addstr(status_y, 10, status_msg.ljust(68)[:68], status_color_pair)

            # Print helpful key bindings list
            footer_y = height - 2
            bindings_line1 = "Keys: FreeCells (Q W E R) | Foundations (A S D F) | Cascades (1-8)"
            bindings_line2 = "[U] Undo | [C] Auto-Collect | [R] Restart | [N] New Game | [Q/Esc] Quit"
            stdscr.addstr(footer_y - 1, 2, bindings_line1, curses.color_pair(3) | curses.A_DIM)
            stdscr.addstr(footer_y, 2, bindings_line2, curses.color_pair(3) | curses.A_DIM)

            # Check if won
            if game.check_win():
                # Game is won! Show overlay
                stdscr.clear()
                win_msg = "★ CONGRATULATIONS! YOU WON! ★"
                stdscr.addstr(height // 2 - 2, (width - len(win_msg)) // 2, win_msg, curses.color_pair(3) | curses.A_BOLD | curses.A_BLINK)
                sub_msg = f"Completed in {game.move_count} moves and {time_str}!"
                stdscr.addstr(height // 2, (width - len(sub_msg)) // 2, sub_msg, curses.color_pair(2))
                prompt_msg = "Press [N] for a New Game, or [Q] to Quit."
                stdscr.addstr(height // 2 + 2, (width - len(prompt_msg)) // 2, prompt_msg, curses.color_pair(4))
                stdscr.refresh()
                
                # Victory loop
                while True:
                    ch = stdscr.getch()
                    if ch in [ord('q'), ord('Q'), 27]: # Q or ESC
                        return
                    elif ch in [ord('n'), ord('N')]:
                        current_seed = random_seed()
                        game = FreeCellGame(seed=current_seed)
                        start_time = time.time()
                        src_type = None
                        src_idx = None
                        status_msg = "New game started! Enter Source key..."
                        status_color_pair = curses.color_pair(3)
                        break
                continue

            stdscr.refresh()

            # Get user input
            try:
                ch = stdscr.getch()
            except KeyboardInterrupt:
                break

            if ch == -1:
                # Timeout, loop to update timer
                continue

            key = chr(ch).lower() if 0 <= ch < 256 else ""

            # Check for Quit
            if key == 'q' or ch == 27: # 'q' or ESC
                break

            # Handle global action keys
            if key == 'u':
                if game.undo():
                    status_msg = "Undo executed."
                    status_color_pair = curses.color_pair(3)
                else:
                    status_msg = "Nothing to undo."
                    status_color_pair = curses.color_pair(4)
                src_type, src_idx = None, None
                continue
            elif key == 'c' or ch == ord(' '):
                prev_moves = game.move_count
                game.auto_collect()
                collected = game.move_count - prev_moves # Wait, auto_collect doesn't increment move_count currently, or does it?
                # Actually, our auto_collect in engine.py does not increment move_count. Let's report simply
                status_msg = "Auto-collected safe cards to foundations."
                status_color_pair = curses.color_pair(3)
                src_type, src_idx = None, None
                continue
            elif key == 'r':
                game = FreeCellGame(seed=current_seed)
                start_time = time.time()
                status_msg = "Game restarted with same layout."
                status_color_pair = curses.color_pair(3)
                src_type, src_idx = None, None
                continue
            elif key == 'n':
                current_seed = random_seed()
                game = FreeCellGame(seed=current_seed)
                start_time = time.time()
                status_msg = f"New game started with seed {current_seed}."
                status_color_pair = curses.color_pair(3)
                src_type, src_idx = None, None
                continue

            # Process selection keys
            if key in key_to_pile:
                pile_type, pile_idx = key_to_pile[key]
                
                if src_type is None:
                    # Selecting source
                    # Verify source has a card
                    has_card = False
                    if pile_type == 'freecell' and game.free_cells[pile_idx] is not None:
                        has_card = True
                    elif pile_type == 'foundation' and game.foundations[pile_idx]:
                        has_card = True
                    elif pile_type == 'cascade' and game.cascades[pile_idx]:
                        has_card = True

                    if has_card:
                        src_type = pile_type
                        src_idx = pile_idx
                        status_msg = f"Selected {pile_type.upper()} {pile_idx + 1 if pile_type == 'cascade' else labels_fc[pile_idx] if pile_type == 'freecell' else labels_fnd[pile_idx][0]}. Choose destination..."
                        status_color_pair = curses.color_pair(3)
                    else:
                        status_msg = f"Selected source {pile_type.upper()} is empty!"
                        status_color_pair = curses.color_pair(4)
                else:
                    # Selecting destination
                    if pile_type == src_type and pile_idx == src_idx:
                        # Cancel selection
                        src_type, src_idx = None, None
                        status_msg = "Selection cancelled."
                        status_color_pair = curses.color_pair(3)
                    else:
                        success, msg = game.validate_and_move(src_type, src_idx, pile_type, pile_idx)
                        if success:
                            status_msg = msg
                            status_color_pair = curses.color_pair(3)
                        else:
                            status_msg = f"Invalid move: {msg}"
                            status_color_pair = curses.color_pair(4)
                        src_type, src_idx = None, None
            else:
                if ch != -1:
                    status_msg = f"Unknown key pressed: {key if key.printable() else ch}. Press bindings shown below."
                    status_color_pair = curses.color_pair(4)

    curses.wrapper(curses_main)


def random_seed():
    """Generates a random 5-digit seed."""
    import random
    return random.randint(10000, 99999)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Terminal-based FreeCell solitaire game in Python.")
    parser.add_argument('--smoke', action='store_true', help="Run non-interactive smoke test.")
    args = parser.parse_args()

    if args.smoke:
        run_smoke_test()
    else:
        run_curses_ui()

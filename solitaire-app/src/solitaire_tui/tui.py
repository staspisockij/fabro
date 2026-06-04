import os
import curses
from solitaire_tui.game_logic import Card, GameState

def init_colors():
    if curses.has_colors():
        curses.start_color()
        # Pair 1: Red cards on Black background
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        # Pair 2: Black cards/White text on Black background
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        # Pair 3: Cyan labels/decorations
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        # Pair 4: Black text on White/Cyan for highlights (Black cards)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
        # Pair 5: Red text on White/Cyan for highlights (Red cards)
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_WHITE)

def format_card(card: Card) -> str:
    if not card.face_up:
        return "[ ## ]"
    r_str = card.rank_str
    if len(r_str) == 1:
        return f"[ {card.suit}{r_str} ]"
    else:
        return f"[ {card.suit}{r_str}]"

def draw_board(stdscr, state: GameState, cursor_area: str, cursor_col: int, cursor_card_idx: int, selected_source):
    stdscr.erase()
    
    # 1. Draw Title and instructions
    stdscr.addstr(1, 2, "=== KLONDIKE SOLITAIRE ===", curses.color_pair(3) | curses.A_BOLD)
    stdscr.addstr(2, 2, "Controls: Arrows/WASD: Move | Space/Enter: Select/Move | U: Undo | R: New Game | Q: Quit | Esc/C: Cancel", curses.color_pair(3))
    
    # Draw selection status if any
    if selected_source:
        src_type, src_idx, card_idx = selected_source
        if src_type == "waste":
            status_str = "Selected: Waste"
        elif src_type == "foundation":
            status_str = f"Selected: Foundation {src_idx}"
        else:
            card_repr = state.tableau[src_idx][card_idx]
            status_str = f"Selected: {card_repr} in Column {src_idx + 1}"
        stdscr.addstr(3, 2, status_str, curses.color_pair(1) | curses.A_BOLD)
    else:
        stdscr.addstr(3, 2, "                                                                      ")

    # 2. Draw Stock & Waste
    # Stock label and card
    stdscr.addstr(5, 4, "STOCK", curses.color_pair(3))
    stock_focused = (cursor_area == "top" and cursor_col == 0)
    stock_card_str = "[ ## ]" if state.stock else "[    ]"
    stock_attr = curses.color_pair(4) if stock_focused else curses.color_pair(2)
    stdscr.addstr(6, 4, stock_card_str, stock_attr)
    
    # Waste label and card
    stdscr.addstr(5, 13, "WASTE", curses.color_pair(3))
    waste_focused = (cursor_area == "top" and cursor_col == 1)
    waste_selected = (selected_source and selected_source[0] == "waste")
    
    if state.waste:
        top_waste = state.waste[-1]
        waste_card_str = format_card(top_waste)
        is_red = top_waste.color == "red"
        if waste_focused or waste_selected:
            waste_attr = curses.color_pair(5) if is_red else curses.color_pair(4)
        else:
            waste_attr = curses.color_pair(1) if is_red else curses.color_pair(2)
    else:
        waste_card_str = "[    ]"
        waste_attr = curses.color_pair(4) if waste_focused else curses.color_pair(2)
        
    stdscr.addstr(6, 13, waste_card_str, waste_attr)
    
    # 3. Draw Foundations
    SUITS = GameState.SUITS
    stdscr.addstr(5, 31, "FOUNDATIONS", curses.color_pair(3))
    for i, suit in enumerate(SUITS):
        fx = 31 + i * 9
        f_focused = (cursor_area == "top" and cursor_col == 3 + i)
        f_selected = (selected_source and selected_source[0] == "foundation" and selected_source[1] == suit)
        
        found_pile = state.foundations[suit]
        if found_pile:
            top_card = found_pile[-1]
            card_str = format_card(top_card)
            is_red = top_card.color == "red"
            if f_focused or f_selected:
                f_attr = curses.color_pair(5) if is_red else curses.color_pair(4)
            else:
                f_attr = curses.color_pair(1) if is_red else curses.color_pair(2)
        else:
            # Empty foundation placeholder
            card_str = f"[  {suit} ]"
            is_red = suit in ("♥", "♦")
            if f_focused:
                f_attr = curses.color_pair(5) if is_red else curses.color_pair(4)
            else:
                f_attr = curses.color_pair(1) if is_red else curses.color_pair(2)
                
        stdscr.addstr(6, fx, card_str, f_attr)

    # 4. Draw Tableau Piles
    for col_idx in range(7):
        tx = 4 + col_idx * 9
        col = state.tableau[col_idx]
        
        # Draw Column Label
        stdscr.addstr(9, tx, f" Col {col_idx+1} ", curses.color_pair(3))
        
        if not col:
            # Draw empty placeholder
            col_focused = (cursor_area == "tableau" and cursor_col == col_idx)
            card_str = "[    ]"
            attr = curses.color_pair(4) if col_focused else curses.color_pair(2)
            stdscr.addstr(10, tx, card_str, attr)
        else:
            for card_idx, card in enumerate(col):
                ty = 10 + card_idx
                col_focused = (cursor_area == "tableau" and cursor_col == col_idx and cursor_card_idx == card_idx)
                
                # Check if this card is part of the selected stack
                card_selected = False
                if selected_source and selected_source[0] == "tableau" and selected_source[1] == col_idx:
                    if card_idx >= selected_source[2]:
                        card_selected = True
                
                card_str = format_card(card)
                is_red = card.face_up and card.color == "red"
                
                if col_focused or card_selected:
                    attr = curses.color_pair(5) if is_red else curses.color_pair(4)
                else:
                    if card.face_up:
                        attr = curses.color_pair(1) if is_red else curses.color_pair(2)
                    else:
                        attr = curses.color_pair(2) # Grey/white for face down
                
                stdscr.addstr(ty, tx, card_str, attr)

    # 5. Draw Win Message if won
    if state.check_win():
        stdscr.addstr(22, 15, "CONGRATULATIONS! YOU WON THE GAME! Press 'R' to play again.", curses.color_pair(1) | curses.A_BOLD | curses.A_BLINK)

    stdscr.refresh()

def main_loop(stdscr):
    # Setup Esc delay and options
    os.environ.setdefault('ESCDELAY', '25')
    curses.curs_set(0)
    stdscr.keypad(True)
    init_colors()
    
    state = GameState()
    
    # Cursor state
    cursor_area = "tableau" # "top" or "tableau"
    cursor_col = 0 # 0-6
    cursor_card_idx = 0 # within tableau column
    selected_source = None # (area, col, card_idx) or None
    
    SUITS = GameState.SUITS
    
    while True:
        # Validate and clamp cursor_card_idx
        if cursor_area == "tableau":
            col = state.tableau[cursor_col]
            if not col:
                cursor_card_idx = 0
            else:
                first_face_up = next((idx for idx, card in enumerate(col) if card.face_up), 0)
                last_card_idx = len(col) - 1
                if cursor_card_idx < first_face_up:
                    cursor_card_idx = first_face_up
                elif cursor_card_idx > last_card_idx:
                    cursor_card_idx = last_card_idx
                    
        # Check terminal size
        height, width = stdscr.getmaxyx()
        if height < 24 or width < 80:
            stdscr.erase()
            stdscr.addstr(0, 0, f"Terminal size too small: {width}x{height}", curses.color_pair(1))
            stdscr.addstr(1, 0, "Please resize your terminal to at least 80x24.", curses.color_pair(2))
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q')):
                break
            continue

        draw_board(stdscr, state, cursor_area, cursor_col, cursor_card_idx, selected_source)
        
        ch = stdscr.getch()
        if ch == -1:
            continue
            
        # Quit
        if ch in (ord('q'), ord('Q')):
            break
            
        # New Game
        elif ch in (ord('r'), ord('R')):
            state = GameState()
            cursor_area = "tableau"
            cursor_col = 0
            cursor_card_idx = 0
            selected_source = None
            
        # Undo
        elif ch in (ord('u'), ord('U')):
            state.undo()
            selected_source = None
            
        # Cancel selection
        elif ch in (27, ord('c'), ord('C')): # 27 is Escape
            selected_source = None
            
        # Navigation
        elif ch in (curses.KEY_LEFT, ord('a'), ord('A')):
            if cursor_col > 0:
                cursor_col -= 1
                if cursor_area == "tableau":
                    col = state.tableau[cursor_col]
                    if col:
                        cursor_card_idx = len(col) - 1
                    else:
                        cursor_card_idx = 0
                        
        elif ch in (curses.KEY_RIGHT, ord('d'), ord('D')):
            if cursor_col < 6:
                cursor_col += 1
                if cursor_area == "tableau":
                    col = state.tableau[cursor_col]
                    if col:
                        cursor_card_idx = len(col) - 1
                    else:
                        cursor_card_idx = 0
                        
        elif ch in (curses.KEY_UP, ord('w'), ord('W')):
            if cursor_area == "tableau":
                col = state.tableau[cursor_col]
                if not col:
                    cursor_area = "top"
                else:
                    first_face_up = next((idx for idx, card in enumerate(col) if card.face_up), 0)
                    if cursor_card_idx > first_face_up:
                        cursor_card_idx -= 1
                    else:
                        cursor_area = "top"
                        
        elif ch in (curses.KEY_DOWN, ord('s'), ord('S')):
            if cursor_area == "top":
                cursor_area = "tableau"
                col = state.tableau[cursor_col]
                if col:
                    cursor_card_idx = len(col) - 1
                else:
                    cursor_card_idx = 0
            elif cursor_area == "tableau":
                col = state.tableau[cursor_col]
                if col:
                    last_card_idx = len(col) - 1
                    if cursor_card_idx < last_card_idx:
                        cursor_card_idx += 1
                        
        # Selection / Movement Action
        elif ch in (ord(' '), 10, 13, curses.KEY_ENTER):
            if selected_source is None:
                # Select source
                if cursor_area == "top":
                    if cursor_col == 0:
                        state.draw_card()
                    elif cursor_col == 1:
                        if state.waste:
                            selected_source = ("waste", None, None)
                    elif cursor_col >= 3:
                        suit = SUITS[cursor_col - 3]
                        if state.foundations[suit]:
                            selected_source = ("foundation", suit, None)
                elif cursor_area == "tableau":
                    col = state.tableau[cursor_col]
                    if col:
                        selected_source = ("tableau", cursor_col, cursor_card_idx)
            else:
                # Attempt move to destination
                src_type, src_idx, card_idx = selected_source
                
                success = False
                if cursor_area == "tableau":
                    success = state.move_cards(src_type, src_idx, card_idx, "tableau", cursor_col)
                elif cursor_area == "top" and cursor_col >= 3:
                    suit = SUITS[cursor_col - 3]
                    success = state.move_cards(src_type, src_idx, card_idx, "foundation", suit)
                
                if success:
                    selected_source = None
                    if cursor_area == "tableau":
                        col = state.tableau[cursor_col]
                        cursor_card_idx = len(col) - 1 if col else 0
                else:
                    # Move failed. Select current position if valid source.
                    if cursor_area == "tableau" and state.tableau[cursor_col]:
                        selected_source = ("tableau", cursor_col, cursor_card_idx)
                    elif cursor_area == "top" and cursor_col == 1 and state.waste:
                        selected_source = ("waste", None, None)
                    elif cursor_area == "top" and cursor_col >= 3 and state.foundations[SUITS[cursor_col - 3]]:
                        selected_source = ("foundation", SUITS[cursor_col - 3], None)
                    else:
                        selected_source = None

def start_game():
    curses.wrapper(main_loop)

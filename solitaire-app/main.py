import sys
import os

# Add src to sys.path so we can import packages correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from solitaire_tui.game_logic import GameState, Card
from solitaire_tui.tui import start_game

def run_smoke_test():
    print("=== SOLITAIRE TUI SMOKE TEST ===")
    
    # 1. Initialize a deterministic game state
    print("Initializing GameState with seed=100...")
    state = GameState(seed=100)
    assert len(state.stock) == 24
    assert len(state.waste) == 0
    assert sum(len(col) for col in state.tableau) == 28
    print("Initialization check: PASSED")

    # 2. Verify stock drawing and recycling logic
    print("Drawing cards from stock...")
    initial_stock_len = len(state.stock)
    for _ in range(initial_stock_len):
        assert state.draw_card()
    assert len(state.stock) == 0
    assert len(state.waste) == initial_stock_len
    
    print("Recycling waste back to stock...")
    assert state.draw_card()
    assert len(state.stock) == initial_stock_len
    assert len(state.waste) == 0
    print("Draw & Recycle check: PASSED")

    # 3. Programmatically execute a valid move and assert state change
    print("Executing a mock valid move...")
    red_jack = Card("♥", 11, face_up=True)
    black_ten = Card("♠", 10, face_up=True)
    
    state.tableau[0] = [red_jack]
    state.tableau[1] = [black_ten]
    
    assert state.validate_move("tableau", 1, 0, "tableau", 0)
    assert state.move_cards("tableau", 1, 0, "tableau", 0)
    
    assert len(state.tableau[1]) == 0
    assert len(state.tableau[0]) == 2
    assert state.tableau[0][1] == black_ten
    print("Move execution check: PASSED")

    # 4. Verify undo reverts the mock state change
    print("Reverting the move with Undo...")
    assert state.undo()
    assert len(state.tableau[0]) == 1
    assert len(state.tableau[1]) == 1
    assert state.tableau[0][0] == red_jack
    assert state.tableau[1][0] == black_ten
    print("Undo check: PASSED")

    # 5. Create a nearly complete foundation set, execute final winning move, and assert win
    print("Simulating winning condition...")
    for suit in GameState.SUITS:
        state.foundations[suit] = [Card(suit, rank, face_up=True) for rank in range(1, 13)]
        
    assert not state.check_win()
    
    # Final winning move: Ace, then 2... now King (13) of each suit is placed on its foundation
    for suit in GameState.SUITS:
        king = Card(suit, 13, face_up=True)
        state.waste = [king]
        assert state.move_cards("waste", None, None, "foundation", suit)
        
    assert state.check_win()
    print("Win detection check: PASSED")

    print("\nText snapshot of winning state:")
    for suit, found in state.foundations.items():
        print(f"  Foundation {suit}: {found[-1] if found else 'empty'}")
    
    print("\n=== SMOKE TEST SUCCEEDED ===")
    sys.exit(0)

if __name__ == "__main__":
    if "--smoke" in sys.argv:
        run_smoke_test()
    else:
        start_game()

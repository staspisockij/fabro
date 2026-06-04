import pytest
from solitaire_tui.game_logic import Card, GameState

def test_game_initialization():
    state = GameState(seed=42)
    # Total cards in standard deck = 52
    # Tableau has 1 + 2 + 3 + 4 + 5 + 6 + 7 = 28 cards
    # Stock has 52 - 28 = 24 cards
    # Waste and foundations are empty
    assert len(state.stock) == 24
    assert len(state.waste) == 0
    assert sum(len(col) for col in state.tableau) == 28
    assert all(len(state.foundations[suit]) == 0 for suit in GameState.SUITS)

    # Check that tableau top cards are face-up and others are face-down
    for i, col in enumerate(state.tableau):
        assert len(col) == i + 1
        for j in range(i):
            assert not col[j].face_up
        assert col[-1].face_up

def test_draw_and_recycle():
    state = GameState(seed=42)
    initial_stock_count = len(state.stock)
    
    # Draw all cards
    for _ in range(initial_stock_count):
        assert state.draw_card()
    
    assert len(state.stock) == 0
    assert len(state.waste) == initial_stock_count
    assert all(card.face_up for card in state.waste)

    # Recycle
    assert state.draw_card()
    assert len(state.stock) == initial_stock_count
    assert len(state.waste) == 0
    assert all(not card.face_up for card in state.stock)

def test_legal_tableau_moves():
    # Setup state manually for controlled validation
    state = GameState(seed=42)
    
    # Let's create a red Jack and black 10
    red_jack = Card("♥", 11, face_up=True)
    black_ten = Card("♠", 10, face_up=True)

    state.tableau[0] = [red_jack]
    state.tableau[1] = [black_ten]

    # Valid move: black 10 (col 1) onto red Jack (col 0)
    assert state.validate_move("tableau", 1, 0, "tableau", 0)
    assert state.move_cards("tableau", 1, 0, "tableau", 0)

    assert len(state.tableau[1]) == 0
    assert len(state.tableau[0]) == 2
    assert state.tableau[0][0] == red_jack
    assert state.tableau[0][1] == black_ten

def test_king_on_empty_tableau():
    state = GameState(seed=42)
    state.tableau[0] = []
    
    king = Card("♦", 13, face_up=True)
    queen = Card("♦", 12, face_up=True)

    state.tableau[1] = [king]
    state.tableau[2] = [queen]

    # King can move to empty
    assert state.validate_move("tableau", 1, 0, "tableau", 0)
    # Queen cannot move to empty
    assert not state.validate_move("tableau", 2, 0, "tableau", 0)

    assert state.move_cards("tableau", 1, 0, "tableau", 0)
    assert state.tableau[0] == [king]

def test_foundation_moves():
    state = GameState(seed=42)
    
    ace = Card("♠", 1, face_up=True)
    two = Card("♠", 2, face_up=True)

    state.waste = [two, ace]

    # Ace of Spades to Spade foundation
    assert state.validate_move("waste", None, None, "foundation", "♠")
    assert state.move_cards("waste", None, None, "foundation", "♠")

    assert state.foundations["♠"] == [ace]
    assert state.waste == [two]

    # Now two of Spades to Spade foundation
    assert state.validate_move("waste", None, None, "foundation", "♠")
    assert state.move_cards("waste", None, None, "foundation", "♠")
    assert state.foundations["♠"] == [ace, two]
    assert len(state.waste) == 0

def test_invalid_moves():
    state = GameState(seed=42)
    
    red_ten = Card("♦", 10, face_up=True)
    red_nine = Card("♥", 9, face_up=True)
    black_ten = Card("♣", 10, face_up=True)

    state.tableau[0] = [red_ten]
    state.tableau[1] = [red_nine]  # same color
    state.tableau[2] = [black_ten] # same rank

    # Same color (red 9 on red 10) is invalid
    assert not state.validate_move("tableau", 1, 0, "tableau", 0)
    # Same rank (black 10 on red 10) is invalid
    assert not state.validate_move("tableau", 2, 0, "tableau", 0)

def test_undo():
    state = GameState(seed=42)
    
    # Record initial state
    initial_stock_len = len(state.stock)
    initial_waste_len = len(state.waste)

    # Action 1: Draw card
    assert state.draw_card()
    assert len(state.stock) == initial_stock_len - 1
    assert len(state.waste) == 1

    # Action 2: Undo
    assert state.undo()
    assert len(state.stock) == initial_stock_len
    assert len(state.waste) == initial_waste_len

    # Multi-step undo
    # Setup move
    red_jack = Card("♥", 11, face_up=True)
    black_ten = Card("♠", 10, face_up=True)
    state.tableau[0] = [red_jack]
    state.tableau[1] = [black_ten]

    state.move_cards("tableau", 1, 0, "tableau", 0)
    assert len(state.tableau[0]) == 2
    assert len(state.tableau[1]) == 0

    state.undo()
    assert len(state.tableau[0]) == 1
    assert len(state.tableau[1]) == 1
    assert state.tableau[0][0] == red_jack
    assert state.tableau[1][0] == black_ten

def test_win_detection():
    state = GameState(seed=42)
    
    # Fill foundations manually up to Queen (12)
    for suit in GameState.SUITS:
        state.foundations[suit] = [Card(suit, rank, face_up=True) for rank in range(1, 13)]

    assert not state.check_win()

    # Move King to each foundation
    for suit in GameState.SUITS:
        king = Card(suit, 13, face_up=True)
        state.waste = [king]
        assert state.move_cards("waste", None, None, "foundation", suit)

    assert state.check_win()

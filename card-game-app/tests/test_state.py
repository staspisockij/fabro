from card_game_tui.engine import GameState, Card, Rank, Suit, Move

def test_deal():
    state = GameState()
    state.deal(seed=42)
    assert sum(len(col) for col in state.tableau) == 52
    assert len(state.tableau[0]) == 7
    assert len(state.tableau[7]) == 6
    assert all(fc is None for fc in state.free_cells)

def test_undo_redo():
    state = GameState()
    state.deal(seed=42)
    
    # Push history
    state.push_history()
    
    # Modify state
    card = state.tableau[0].pop()
    state.free_cells[0] = card
    
    # Undo
    assert state.undo()
    assert state.free_cells[0] is None
    assert len(state.tableau[0]) == 7
    
    # Redo
    assert state.redo()
    assert state.free_cells[0] == card
    assert len(state.tableau[0]) == 6

def test_execute_move():
    state = GameState()
    state.tableau = [[] for _ in range(8)]
    state.free_cells = [None] * 4
    # Put J♥ at C0 and Q♠ at C1
    state.tableau[0] = [Card(Rank.JACK, Suit.HEARTS)]
    state.tableau[1] = [Card(Rank.QUEEN, Suit.SPADES)]

    # Attempt valid move: J♥ onto Q♠
    move = Move('C', 0, 'C', 1, 1)
    success, reason = state.execute_move(move)
    assert success
    assert not state.tableau[0]
    assert len(state.tableau[1]) == 2
    assert state.tableau[1][1] == Card(Rank.JACK, Suit.HEARTS)

    # Undo should restore J♥ to C0
    assert state.undo()
    assert len(state.tableau[0]) == 1
    assert len(state.tableau[1]) == 1

def test_auto_home():
    state = GameState()
    state.tableau = [[] for _ in range(8)]
    state.free_cells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # Ace of Spades (A♠) should auto-home immediately
    ace_spades = Card(Rank.ACE, Suit.SPADES)
    state.free_cells[0] = ace_spades
    state.auto_home()
    assert state.free_cells[0] is None
    assert len(state.foundations[Suit.SPADES]) == 1
    assert state.foundations[Suit.SPADES][0] == ace_spades

    # Two of Spades (2♠) is added. Should it auto-home?
    # opposite-color Aces (A♥, A♦) are NOT in foundation yet, so 2♠ should NOT auto-home.
    two_spades = Card(Rank.TWO, Suit.SPADES)
    state.free_cells[0] = two_spades
    state.auto_home()
    assert state.free_cells[0] == two_spades

    # Add opposite color Aces (A♥, A♦) to foundations.
    # Now, 2♠ should auto-home.
    state.foundations[Suit.HEARTS].append(Card(Rank.ACE, Suit.HEARTS))
    state.foundations[Suit.DIAMONDS].append(Card(Rank.ACE, Suit.DIAMONDS))
    state.auto_home()
    assert state.free_cells[0] is None
    assert len(state.foundations[Suit.SPADES]) == 2
    assert state.foundations[Suit.SPADES][1] == two_spades

def test_is_won():
    state = GameState()
    assert not state.is_won()

    # Fill foundations with all cards
    for suit in Suit:
        state.foundations[suit] = [Card(rank, suit) for rank in Rank]
    assert state.is_won()

def test_is_lost():
    state = GameState()
    state.tableau = [[] for _ in range(8)]
    state.free_cells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # No cards -> not lost because we won (wait, won is also checked inside is_lost to return False)
    # Let's populate foundations with 12 cards, and leave 4 Kings locked in tableau columns such that no moves can be made
    for suit in Suit:
        state.foundations[suit] = [Card(rank, suit) for rank in Rank if rank != Rank.KING]
    
    # 4 Kings are in the tableau but they cannot be moved to foundations because, say, they are stacked under each other or we just place them in columns
    # Actually, a King is a valid foundation move if Queen is in foundation, so putting King of Spades in C0 when Queen of Spades is in foundation is a valid move!
    # Let's create a genuinely locked state:
    # A single King is in C0, but it is Card(Rank.KING, Suit.SPADES) and Queen of Spades is NOT in foundation (it's in C1, but blocked by a Red King).
    # Even simpler:
    # Let's put a single 5♠ on C0 and 10♦ on C1.
    # No free cells available.
    state.foundations = {suit: [] for suit in Suit}
    state.free_cells = [Card(Rank.KING, Suit.HEARTS)] * 4  # All occupied
    state.tableau[0] = [Card(Rank.FIVE, Suit.SPADES)]
    state.tableau[1] = [Card(Rank.TEN, Suit.DIAMONDS)]
    # All other columns empty. F = 0, T = 6. Max movable card count to empty column is (1+0)*2^5 = 32.
    # But wait, we can move 5♠ to empty column C2! So it is not lost.
    # To prevent moving to empty columns, let's fill all 8 columns with 1 card each:
    state.tableau = [[Card(Rank.FIVE, Suit.SPADES)] for _ in range(8)]
    # FreeCells are all occupied:
    state.free_cells = [Card(Rank.KING, Suit.HEARTS)] * 4
    # Foundations empty:
    state.foundations = {suit: [] for suit in Suit}
    
    # In this state, we have 5♠ in all columns. No columns are empty.
    # No cards can be placed on each other (since they are all 5♠, which doesn't alternate color/rank-1).
    # No cards can be moved to free cells (occupied).
    # No cards can be moved to foundations (need Aces, but all have 5).
    # Thus, no legal moves are possible!
    assert state.is_lost()


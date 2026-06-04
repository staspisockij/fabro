import copy
from card_game_tui.domain import GameState, Suit, Rank, Card, Deck, LocationType, Position

def test_deck_deals_52_cards():
    deck = Deck()
    assert len(deck.cards) == 52

def test_game_state_initialization():
    state = GameState()
    assert len(state.tableaus) == 8
    # 4 columns should have 7 cards, 4 should have 6 cards
    lengths = [len(col) for col in state.tableaus]
    assert sorted(lengths) == [6, 6, 6, 6, 7, 7, 7, 7]

def test_get_card_at():
    state = GameState(seed=123)
    # Check if we can get cards correctly
    pos = Position(LocationType.TABLEAU, 0)
    card = state.get_card_at(pos)
    assert card is not None
    assert isinstance(card, Card)

def test_deck_deterministic_seeding():
    deck1 = Deck(seed=42)
    deck2 = Deck(seed=42)
    assert deck1.cards == deck2.cards

    # Verify uniqueness of 52 cards
    assert len(set(deck1.cards)) == 52

def test_moves_to_free_cells():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # Put a card in Tableau 0
    c_hearts = Card(Suit.HEARTS, Rank.TEN)
    state.tableaus[0] = [c_hearts]

    from_pos = Position(LocationType.TABLEAU, 0)
    to_pos = Position(LocationType.FREECELL, 0)

    # Valid single card move to empty freecell
    assert state.validate_move(from_pos, to_pos, count=1) is True
    
    # Try invalid sequence count to free cell
    assert state.validate_move(from_pos, to_pos, count=2) is False

    # Execute move
    assert state.execute_move(from_pos, to_pos, count=1) is True
    assert state.freecells[0] == c_hearts
    assert len(state.tableaus[0]) == 0

    # Try moving to occupied freecell
    state.tableaus[0] = [Card(Suit.SPADES, Rank.FIVE)]
    assert state.validate_move(from_pos, to_pos, count=1) is False

    # Try moving to invalid freecell index
    invalid_to_pos = Position(LocationType.FREECELL, 4)
    assert state.validate_move(from_pos, invalid_to_pos, count=1) is False

def test_moves_to_foundations():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    ace_hearts = Card(Suit.HEARTS, Rank.ACE)
    two_hearts = Card(Suit.HEARTS, Rank.TWO)
    three_hearts = Card(Suit.HEARTS, Rank.THREE)
    ace_diamonds = Card(Suit.DIAMONDS, Rank.ACE)

    state.tableaus[0] = [ace_hearts]
    state.tableaus[1] = [two_hearts]
    state.tableaus[2] = [three_hearts]
    state.tableaus[3] = [ace_diamonds]

    # Move Ace of Hearts to index 0 (HEARTS) foundation
    # list(Suit) indices: 0: HEARTS, 1: DIAMONDS, 2: CLUBS, 3: SPADES
    hearts_found = Position(LocationType.FOUNDATION, 0)
    diamonds_found = Position(LocationType.FOUNDATION, 1)

    # Valid Ace to empty foundation
    assert state.validate_move(Position(LocationType.TABLEAU, 0), hearts_found, count=1) is True
    # Invalid non-Ace to empty foundation
    assert state.validate_move(Position(LocationType.TABLEAU, 1), hearts_found, count=1) is False
    # Invalid Ace to wrong suit foundation
    assert state.validate_move(Position(LocationType.TABLEAU, 3), hearts_found, count=1) is False

    # Execute valid Ace move
    assert state.execute_move(Position(LocationType.TABLEAU, 0), hearts_found, count=1) is True
    assert state.foundations[Suit.HEARTS] == [ace_hearts]

    # Now Two of Hearts is on Tableau 1. Can it move to Hearts foundation? Yes.
    assert state.validate_move(Position(LocationType.TABLEAU, 1), hearts_found, count=1) is True
    # Can Three of Hearts move? No, since it needs Two of Hearts first.
    assert state.validate_move(Position(LocationType.TABLEAU, 2), hearts_found, count=1) is False

def test_moves_to_tableau_single_card():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # Red 8 (Hearts) on Black 9 (Spades)
    c_red8 = Card(Suit.HEARTS, Rank.EIGHT)
    c_black9 = Card(Suit.SPADES, Rank.NINE)
    
    state.tableaus[0] = [c_red8]
    state.tableaus[1] = [c_black9]

    # Test moving Red 8 onto Black 9
    assert state.validate_move(Position(LocationType.TABLEAU, 0), Position(LocationType.TABLEAU, 1), count=1) is True

    # Test same color invalid move: Red 8 (Hearts) on Red 9 (Diamonds)
    c_red9 = Card(Suit.DIAMONDS, Rank.NINE)
    state.tableaus[1] = [c_red9]
    assert state.validate_move(Position(LocationType.TABLEAU, 0), Position(LocationType.TABLEAU, 1), count=1) is False

    # Test wrong rank invalid move: Red 8 on Black 10 (Spades)
    c_black10 = Card(Suit.SPADES, Rank.TEN)
    state.tableaus[1] = [c_black10]
    assert state.validate_move(Position(LocationType.TABLEAU, 0), Position(LocationType.TABLEAU, 1), count=1) is False

    # Test moving to empty tableau
    state.tableaus[1] = []
    assert state.validate_move(Position(LocationType.TABLEAU, 0), Position(LocationType.TABLEAU, 1), count=1) is True

def test_sequence_moves_tableau_to_tableau():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}
    
    # Red 10, Black 9, Red 8, Black 7, Red 6
    c10 = Card(Suit.HEARTS, Rank.TEN)
    c9 = Card(Suit.SPADES, Rank.NINE)
    c8 = Card(Suit.DIAMONDS, Rank.EIGHT)
    c7 = Card(Suit.CLUBS, Rank.SEVEN)
    c6 = Card(Suit.HEARTS, Rank.SIX)
    
    state.tableaus[0] = [c10, c9, c8, c7, c6]
    state.tableaus[1] = [Card(Suit.SPADES, Rank.JACK)]
    
    # 4 empty freecells, 6 empty tableaus.
    # Exclude destination: no, destination is Col 1 which has 1 card (not empty).
    # Transit empty tableaus = 6
    # Max cards = (1 + 4) * 2^6 = 5 * 64 = 320 cards.
    # Moving 5 cards should be valid!
    from_pos = Position(LocationType.TABLEAU, 0)
    to_pos = Position(LocationType.TABLEAU, 1)
    assert state.validate_move(from_pos, to_pos, count=5) is True
    
    # Restrict capacity
    state.freecells = [Card(Suit.CLUBS, Rank.TWO)] * 4  # 0 empty freecells
    for i in range(2, 8):
        state.tableaus[i] = [Card(Suit.DIAMONDS, Rank.KING)]  # 0 empty tableaus
    # Now empty freecells = 0, empty tableaus = 0
    # Max cards = (1 + 0) * 2^0 = 1
    # Moving 5 cards should be invalid
    assert state.validate_move(from_pos, to_pos, count=5) is False

def test_sequence_moves_to_empty_tableau():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # Sequence of 3 cards on Col 0: Red 10, Black 9, Red 8
    c10 = Card(Suit.HEARTS, Rank.TEN)
    c9 = Card(Suit.SPADES, Rank.NINE)
    c8 = Card(Suit.DIAMONDS, Rank.EIGHT)
    state.tableaus[0] = [c10, c9, c8]

    # Destination is Col 1 (empty)
    # We want to move 2 cards: Black 9, Red 8
    # Capacity constraint:
    # Destination Col 1 is empty, so transit_empty_tableaus = empty_tableaus - 1.
    # Empty tableaus before move = 7.
    # Transit empty tableaus = 6.
    # Empty free cells = 4.
    # Max cards = (1 + 4) * 2^6 = 320.
    from_pos = Position(LocationType.TABLEAU, 0)
    to_pos = Position(LocationType.TABLEAU, 1)
    assert state.validate_move(from_pos, to_pos, count=2) is True

    # Restrict capacity so Max Cards is exactly 1
    state.freecells = [Card(Suit.CLUBS, Rank.TWO)] * 4  # 0 empty free cells
    for i in range(2, 8):
        state.tableaus[i] = [Card(Suit.DIAMONDS, Rank.KING)]  # 0 transit empty tableaus
    # Empty freecells = 0, empty tableaus = 1 (Col 1).
    # Since Col 1 is the destination, transit_empty_tableaus = 1 - 1 = 0.
    # Max cards = (1 + 0) * 2^0 = 1.
    # Moving 2 cards should be invalid, but 1 card should be valid.
    assert state.validate_move(from_pos, to_pos, count=2) is False
    assert state.validate_move(from_pos, to_pos, count=1) is True

def test_auto_homing_logic():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # Hearts is RED. Opposite suits are CLUBS and SPADES.
    # Put Ace of Hearts in Tableau 0.
    state.tableaus[0] = [Card(Suit.HEARTS, Rank.ACE)]
    # Put King of Spades in Tableau 1 to use as a dummy move trigger.
    state.tableaus[1] = [Card(Suit.SPADES, Rank.KING)]
    
    assert len(state.foundations[Suit.HEARTS]) == 0
    
    # Execute move of King of Spades to FreeCell 0. This should trigger auto-homing of Ace of Hearts.
    from_pos = Position(LocationType.TABLEAU, 1)
    to_pos = Position(LocationType.FREECELL, 0)
    success = state.execute_move(from_pos, to_pos, count=1)
    assert success is True
    
    assert state.freecells[0] == Card(Suit.SPADES, Rank.KING)
    assert len(state.tableaus[0]) == 0
    assert len(state.foundations[Suit.HEARTS]) == 1
    assert state.foundations[Suit.HEARTS][0] == Card(Suit.HEARTS, Rank.ACE)
    
    # Two of Hearts is put in Tableau 0.
    # Foundations: Hearts has Ace. CLUBS has [], SPADES has [].
    # Opposite color (Black) lower cards are Ace of Clubs and Ace of Spades.
    # Since they are NOT in the foundations, Two of Hearts should NOT auto-home.
    state.tableaus[0] = [Card(Suit.HEARTS, Rank.TWO)]
    
    # Move King of Spades from FreeCell 0 to Tableau 1 to trigger auto-homing checks
    from_pos = Position(LocationType.FREECELL, 0)
    to_pos = Position(LocationType.TABLEAU, 1)
    success = state.execute_move(from_pos, to_pos, count=1)
    assert success is True
    
    # Two of Hearts should still be in Tableau 0 (not auto-homed)
    assert len(state.tableaus[0]) == 1
    assert state.tableaus[0][0] == Card(Suit.HEARTS, Rank.TWO)
    assert len(state.foundations[Suit.HEARTS]) == 1
    
    # Place Ace of Clubs and Ace of Spades in their foundations.
    state.foundations[Suit.CLUBS] = [Card(Suit.CLUBS, Rank.ACE)]
    state.foundations[Suit.SPADES] = [Card(Suit.SPADES, Rank.ACE)]
    
    # Move King of Spades back to FreeCell 0 to trigger auto-homing checks
    from_pos = Position(LocationType.TABLEAU, 1)
    to_pos = Position(LocationType.FREECELL, 0)
    success = state.execute_move(from_pos, to_pos, count=1)
    assert success is True
    
    # Two of Hearts should now have auto-homed!
    assert len(state.tableaus[0]) == 0
    assert len(state.foundations[Suit.HEARTS]) == 2
    assert state.foundations[Suit.HEARTS][1] == Card(Suit.HEARTS, Rank.TWO)

def test_undo_redo_system():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # Col 0: [Red 10 (Hearts)]
    # Col 1: [Black J (Spades)]
    c10 = Card(Suit.HEARTS, Rank.TEN)
    cJ = Card(Suit.SPADES, Rank.JACK)
    state.tableaus[0] = [c10]
    state.tableaus[1] = [cJ]

    # Save original state for verification
    orig_tableaus = copy.deepcopy(state.tableaus)
    orig_freecells = copy.deepcopy(state.freecells)
    orig_foundations = copy.deepcopy(state.foundations)

    # 1. Execute a move
    from_pos = Position(LocationType.TABLEAU, 0)
    to_pos = Position(LocationType.TABLEAU, 1)
    success = state.execute_move(from_pos, to_pos, count=1)
    assert success is True
    
    assert state.tableaus[0] == []
    assert state.tableaus[1] == [cJ, c10]
    
    # 2. Undo the move
    undo_success = state.undo()
    assert undo_success is True
    assert state.tableaus == orig_tableaus
    assert state.freecells == orig_freecells
    assert state.foundations == orig_foundations

    # 3. Redo the move
    redo_success = state.redo()
    assert redo_success is True
    assert state.tableaus[0] == []
    assert state.tableaus[1] == [cJ, c10]

    # 4. Undo again to restore
    assert state.undo() is True
    assert state.tableaus == orig_tableaus

def test_undo_with_auto_homing():
    state = GameState()
    state.tableaus = [[] for _ in range(8)]
    state.freecells = [None] * 4
    state.foundations = {suit: [] for suit in Suit}

    # Tableau 0: Ace of Hearts
    # Tableau 1: King of Spades
    # Move King of Spades to FreeCell 0. This will trigger auto-homing of Ace of Hearts to foundation.
    state.tableaus[0] = [Card(Suit.HEARTS, Rank.ACE)]
    state.tableaus[1] = [Card(Suit.SPADES, Rank.KING)]

    orig_tableaus = copy.deepcopy(state.tableaus)
    orig_freecells = copy.deepcopy(state.freecells)
    orig_foundations = copy.deepcopy(state.foundations)

    from_pos = Position(LocationType.TABLEAU, 1)
    to_pos = Position(LocationType.FREECELL, 0)
    success = state.execute_move(from_pos, to_pos, count=1)
    assert success is True

    # Check state after move and auto-homing
    assert state.freecells[0] == Card(Suit.SPADES, Rank.KING)
    assert len(state.tableaus[0]) == 0
    assert len(state.foundations[Suit.HEARTS]) == 1

    # Undo the move! This should revert both King of Spades and Ace of Hearts!
    undo_success = state.undo()
    assert undo_success is True
    assert state.tableaus == orig_tableaus
    assert state.freecells == orig_freecells
    assert state.foundations == orig_foundations

    # Redo the move!
    redo_success = state.redo()
    assert redo_success is True
    assert state.freecells[0] == Card(Suit.SPADES, Rank.KING)
    assert len(state.tableaus[0]) == 0
    assert len(state.foundations[Suit.HEARTS]) == 1

def test_win_detection():
    state = GameState()
    # Fill foundations
    for suit in Suit:
        state.foundations[suit] = [Card(suit, rank) for rank in Rank]
    assert state.check_win() is True

    # Remove one card
    state.foundations[Suit.HEARTS].pop()
    assert state.check_win() is False

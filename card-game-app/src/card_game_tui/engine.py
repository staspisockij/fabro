import random
import copy

# Ranks mapping for display
RANK_NAMES = {
    1: 'A',
    2: '2',
    3: '3',
    4: '4',
    5: '5',
    6: '6',
    7: '7',
    8: '8',
    9: '9',
    10: '10',
    11: 'J',
    12: 'Q',
    13: 'K'
}

SUIT_SYMBOLS = {
    'S': '♠',  # Spades
    'H': '♥',  # Hearts
    'D': '♦',  # Diamonds
    'C': '♣'   # Clubs
}

class Card:
    def __init__(self, rank: int, suit: str, face_up: bool = False):
        self.rank = rank      # 1 (Ace) to 13 (King)
        self.suit = suit      # 'S', 'H', 'D', 'C'
        self.face_up = face_up

    def __repr__(self):
        status = "up" if self.face_up else "down"
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]} ({status})"

    def display_str(self) -> str:
        if self.face_up:
            return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"
        return "[░░░]"

    def to_dict(self):
        return {
            'rank': self.rank,
            'suit': self.suit,
            'face_up': self.face_up
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['rank'], data['suit'], data['face_up'])


class GameState:
    def __init__(self, difficulty: int = 1):
        """
        difficulty: 1 (1-Suit: Spades), 2 (2-Suit: Spades, Hearts), 4 (4-Suit: Standard)
        """
        if difficulty not in (1, 2, 4):
            difficulty = 1
        self.difficulty = difficulty
        self.tableau = [[] for _ in range(10)]  # 10 columns
        self.stock = []                        # stock pile
        self.completed_sequences = 0           # Count of completed K-A runs (0-8)
        self.completed_suits = []              # Track exact suits of completed runs
        self.score = 500                       # Standard starting score
        self.moves_count = 0
        self.history = []                      # Undo history
        
        self.initialize_game()

    def initialize_game(self):
        # Determine suits to use based on difficulty
        if self.difficulty == 1:
            suits = ['S'] * 8
        elif self.difficulty == 2:
            suits = ['S', 'H'] * 4
        else:
            suits = ['S', 'H', 'D', 'C'] * 2

        # Create 104 cards (8 full 13-card runs)
        deck = []
        for suit in suits:
            for rank in range(1, 14):
                deck.append(Card(rank, suit, face_up=False))

        # Shuffle deck
        random.shuffle(deck)

        # Distribute cards to 10 columns
        # Columns 0-3: 6 cards each (5 face down, 1 face up)
        # Columns 4-9: 5 cards each (4 face down, 1 face up)
        self.tableau = [[] for _ in range(10)]
        for i in range(10):
            num_cards = 6 if i < 4 else 5
            for _ in range(num_cards):
                card = deck.pop()
                self.tableau[i].append(card)
            # Turn top card face up
            if self.tableau[i]:
                self.tableau[i][-1].face_up = True

        # Remaining 50 cards go to stock
        self.stock = deck
        self.completed_sequences = 0
        self.completed_suits = []
        self.score = 500
        self.moves_count = 0
        self.history = []

    def save_state_to_history(self):
        """Save a deep-ish copy of state to allow undo"""
        state_copy = {
            'tableau': [[Card(c.rank, c.suit, c.face_up) for c in col] for col in self.tableau],
            'stock': [Card(c.rank, c.suit, c.face_up) for c in self.stock],
            'completed_sequences': self.completed_sequences,
            'completed_suits': list(self.completed_suits),
            'score': self.score,
            'moves_count': self.moves_count
        }
        self.history.append(state_copy)

    def undo(self) -> bool:
        """Revert to the last saved state"""
        if not self.history:
            return False
        prev_state = self.history.pop()
        self.tableau = prev_state['tableau']
        self.stock = prev_state['stock']
        self.completed_sequences = prev_state['completed_sequences']
        self.completed_suits = prev_state['completed_suits']
        self.score = prev_state['score']
        self.moves_count = prev_state['moves_count']
        return True

    def can_deal_from_stock(self) -> bool:
        """
        Stock deals 10 cards.
        Standard rules: stock cannot be dealt if any column is empty.
        Must also have at least 10 cards left in the stock.
        """
        if len(self.stock) < 10:
            return False
        for col in self.tableau:
            if not col:
                return False
        return True

    def deal_from_stock(self) -> bool:
        """Deals 1 card to each of the 10 columns."""
        if not self.can_deal_from_stock():
            return False

        self.save_state_to_history()
        
        # Deal 10 cards
        for col_idx in range(10):
            card = self.stock.pop()
            card.face_up = True
            self.tableau[col_idx].append(card)

        # After deal, check for any newly completed sequences in columns
        self.check_and_clear_all_completed_sequences()
        
        self.score -= 1
        self.moves_count += 1
        return True

    def get_movable_sequence_start_indices(self, col_idx: int) -> list:
        """
        Returns a list of starting indices of all valid movable sequences in a column.
        A sequence is movable if:
          1. All cards in the sequence are face_up.
          2. The cards are in consecutive descending ranks (e.g. 7, 6, 5).
          3. All cards in the sequence have the SAME suit.
        """
        col = self.tableau[col_idx]
        if not col:
            return []

        movable_indices = []
        n = len(col)
        
        # Check from the bottom-most card upwards
        for start_idx in range(n - 1, -1, -1):
            # If the starting card is not face-up, we cannot start a sequence here
            if not col[start_idx].face_up:
                break
            
            # Verify sequence from start_idx to the end of the column
            is_valid = True
            current_suit = col[start_idx].suit
            for i in range(start_idx, n - 1):
                card1 = col[i]
                card2 = col[i+1]
                # Conditions: same suit, and rank of card2 is exactly card1 - 1
                if not card2.face_up or card2.suit != current_suit or card2.rank != card1.rank - 1:
                    is_valid = False
                    break
            
            if is_valid:
                movable_indices.append(start_idx)
            else:
                # If a sequence from start_idx is not valid, any larger sequence containing it won't be valid either
                break

        # Return indices sorted ascending (e.g., from top of sequence down to bottom)
        return sorted(movable_indices)

    def can_move(self, from_col: int, start_idx: int, to_col: int) -> bool:
        """
        Validates if moving the sequence starting at start_idx from from_col to to_col is legal.
        """
        if from_col < 0 or from_col >= 10 or to_col < 0 or to_col >= 10:
            return False
        if from_col == to_col:
            return False
        
        col_from = self.tableau[from_col]
        col_to = self.tableau[to_col]

        # Valid range check
        if not col_from or start_idx < 0 or start_idx >= len(col_from):
            return False

        # Is the sequence itself valid (descending, same suit, all face up)?
        valid_starts = self.get_movable_sequence_start_indices(from_col)
        if start_idx not in valid_starts:
            return False

        # Can it be placed on target column?
        if not col_to:
            # Empty column can accept any valid sequence
            return True

        # Target column is not empty; top card must be rank of moving_card + 1 (suit doesn't matter)
        target_card = col_to[-1]
        moving_card = col_from[start_idx]
        if target_card.rank == moving_card.rank + 1:
            return True

        return False

    def move_cards(self, from_col: int, start_idx: int, to_col: int) -> bool:
        """Executes a move from from_col to to_col, handling score, revealing, and completions."""
        if not self.can_move(from_col, start_idx, to_col):
            return False

        self.save_state_to_history()

        col_from = self.tableau[from_col]
        col_to = self.tableau[to_col]

        # Extract sequence
        moving_cards = col_from[start_idx:]
        self.tableau[from_col] = col_from[:start_idx]
        
        # Place on target
        col_to.extend(moving_cards)

        # Flip the new bottom card of the source column if it's facedown
        if self.tableau[from_col] and not self.tableau[from_col][-1].face_up:
            self.tableau[from_col][-1].face_up = True

        # Check for sequence completions across all columns
        self.check_and_clear_all_completed_sequences()

        self.score -= 1
        self.moves_count += 1
        return True

    def check_and_clear_all_completed_sequences(self):
        """
        Scan all 10 columns. If the bottom 13 cards of a column form a complete
        descending same-suit sequence from King (13) down to Ace (1), remove them
        and increment completed count.
        Repeat until no more completed sequences are found.
        """
        cleared_any = True
        while cleared_any:
            cleared_any = False
            for col_idx in range(10):
                col = self.tableau[col_idx]
                if len(col) < 13:
                    continue
                
                # Check bottom 13 cards
                candidate_cards = col[-13:]
                
                # Check if all 13 cards are face_up, same suit, and descending from 13 to 1
                suit = candidate_cards[0].suit
                is_completed = True
                for i, card in enumerate(candidate_cards):
                    expected_rank = 13 - i
                    if not card.face_up or card.suit != suit or card.rank != expected_rank:
                        is_completed = False
                        break
                
                if is_completed:
                    # Remove the completed sequence
                    self.tableau[col_idx] = col[:-13]
                    self.completed_sequences += 1
                    self.completed_suits.append(suit)
                    self.score += 100
                    
                    # Reveal the newly exposed bottom card of the column
                    if self.tableau[col_idx] and not self.tableau[col_idx][-1].face_up:
                        self.tableau[col_idx][-1].face_up = True
                        
                    cleared_any = True
                    break # Restart scan since tableau state has changed

    def has_any_moves(self) -> bool:
        """
        Detects if there is any valid move available on the board.
        Does not check stock deals (stock deal is always an option if stock not empty).
        """
        # If stock is not empty, there is a potential action (even if we need to clear empty cols first)
        if len(self.stock) >= 10:
            return True
            
        # Check all possible from/to column combinations
        for from_col in range(10):
            valid_starts = self.get_movable_sequence_start_indices(from_col)
            for start_idx in valid_starts:
                for to_col in range(10):
                    if from_col == to_col:
                        continue
                    if self.can_move(from_col, start_idx, to_col):
                        return True
        return False

    def is_won(self) -> bool:
        return self.completed_sequences == 8

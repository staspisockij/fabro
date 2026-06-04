import random
import copy

class Card:
    def __init__(self, suit: str, rank: int, face_up: bool = False):
        self.suit = suit  # ♠, ♥, ♦, ♣
        self.rank = rank  # 1 to 13
        self.face_up = face_up

    @property
    def color(self) -> str:
        return "red" if self.suit in ("♥", "♦") else "black"

    @property
    def rank_str(self) -> str:
        if self.rank == 1:
            return "A"
        elif self.rank == 11:
            return "J"
        elif self.rank == 12:
            return "Q"
        elif self.rank == 13:
            return "K"
        else:
            return str(self.rank)

    def copy(self):
        return Card(self.suit, self.rank, self.face_up)

    def __repr__(self) -> str:
        return f"{self.suit}{self.rank_str}" if self.face_up else "##"

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank and self.face_up == other.face_up


class GameState:
    SUITS = ["♠", "♥", "♦", "♣"]

    def __init__(self, seed=None):
        self.seed = seed
        self.stock = []
        self.waste = []
        self.tableau = [[] for _ in range(7)]
        self.foundations = {suit: [] for suit in self.SUITS}
        self.undo_stack = []
        self.deal()

    def deal(self):
        # Create deck
        deck = [Card(suit, rank) for suit in self.SUITS for rank in range(1, 14)]
        
        # Shuffle
        rng = random.Random(self.seed)
        rng.shuffle(deck)

        # Clear existing piles
        self.stock = []
        self.waste = []
        self.tableau = [[] for _ in range(7)]
        self.foundations = {suit: [] for suit in self.SUITS}
        self.undo_stack = []

        # Deal to tableau
        for i in range(7):
            for j in range(i + 1):
                card = deck.pop()
                if j == i:
                    card.face_up = True
                self.tableau[i].append(card)

        # Remaining to stock
        self.stock = deck

    def save_state(self):
        snapshot = {
            'stock': [card.copy() for card in self.stock],
            'waste': [card.copy() for card in self.waste],
            'tableau': [[card.copy() for card in col] for col in self.tableau],
            'foundations': {suit: [card.copy() for card in col] for suit, col in self.foundations.items()}
        }
        self.undo_stack.append(snapshot)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        snapshot = self.undo_stack.pop()
        self.stock = [card.copy() for card in snapshot['stock']]
        self.waste = [card.copy() for card in snapshot['waste']]
        self.tableau = [[card.copy() for card in col] for col in snapshot['tableau']]
        self.foundations = {suit: [card.copy() for card in col] for suit, col in snapshot['foundations'].items()}
        return True

    def draw_card(self) -> bool:
        self.save_state()
        if self.stock:
            card = self.stock.pop()
            card.face_up = True
            self.waste.append(card)
            return True
        elif self.waste:
            # Recycle
            self.stock = [card.copy() for card in reversed(self.waste)]
            for card in self.stock:
                card.face_up = False
            self.waste = []
            return True
        return False

    def check_win(self) -> bool:
        return all(len(self.foundations[suit]) == 13 for suit in self.SUITS)

    def validate_move(self, src_type: str, src_idx, card_idx, dst_type: str, dst_idx) -> bool:
        # Validate source
        if src_type == "waste":
            if not self.waste:
                return False
            moving_cards = [self.waste[-1]]
        elif src_type == "tableau":
            if src_idx < 0 or src_idx >= 7:
                return False
            col = self.tableau[src_idx]
            if not col or card_idx < 0 or card_idx >= len(col):
                return False
            if not col[card_idx].face_up:
                return False
            moving_cards = col[card_idx:]
        elif src_type == "foundation":
            if src_idx not in self.SUITS:
                return False
            found = self.foundations[src_idx]
            if not found:
                return False
            moving_cards = [found[-1]]
        else:
            return False

        # Validate destination
        first_moving = moving_cards[0]

        if dst_type == "tableau":
            if dst_idx < 0 or dst_idx >= 7:
                return False
            # Self-move is invalid
            if src_type == "tableau" and src_idx == dst_idx:
                return False
            dst_col = self.tableau[dst_idx]
            if not dst_col:
                # Empty tableau can only accept a King (13)
                return first_moving.rank == 13
            else:
                dst_card = dst_col[-1]
                return first_moving.color != dst_card.color and first_moving.rank == dst_card.rank - 1

        elif dst_type == "foundation":
            if dst_idx not in self.SUITS:
                return False
            # Can only move 1 card to foundation at a time
            if len(moving_cards) > 1:
                return False
            # Self-move is invalid
            if src_type == "foundation" and src_idx == dst_idx:
                return False
            if first_moving.suit != dst_idx:
                return False
            found = self.foundations[dst_idx]
            if not found:
                return first_moving.rank == 1  # Ace
            else:
                return first_moving.rank == found[-1].rank + 1

        return False

    def move_cards(self, src_type: str, src_idx, card_idx, dst_type: str, dst_idx) -> bool:
        if not self.validate_move(src_type, src_idx, card_idx, dst_type, dst_idx):
            return False

        self.save_state()

        # Extract card(s)
        if src_type == "waste":
            card = self.waste.pop()
            moving_cards = [card]
        elif src_type == "tableau":
            col = self.tableau[src_idx]
            moving_cards = col[card_idx:]
            self.tableau[src_idx] = col[:card_idx]
            # Auto-reveal top card of source column
            if self.tableau[src_idx] and not self.tableau[src_idx][-1].face_up:
                self.tableau[src_idx][-1].face_up = True
        elif src_type == "foundation":
            card = self.foundations[src_idx].pop()
            moving_cards = [card]

        # Insert cards
        if dst_type == "tableau":
            self.tableau[dst_idx].extend(moving_cards)
        elif dst_type == "foundation":
            self.foundations[dst_idx].extend(moving_cards)

        return True

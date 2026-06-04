import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import copy

@dataclass
class Card:
    suit: str       # 'H' (Hearts), 'D' (Diamonds), 'C' (Clubs), 'S' (Spades)
    rank: int       # 1 (Ace) to 13 (King)
    is_face_up: bool = False

    @property
    def is_red(self) -> bool:
        return self.suit in ('H', 'D')

    @property
    def color(self) -> str:
        return "red" if self.is_red else "black"

    @property
    def label(self) -> str:
        ranks = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return ranks.get(self.rank, str(self.rank))

    def display_str(self) -> str:
        """Returns string representation of card depending on whether it is face up."""
        if self.is_face_up:
            suit_syms = {'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠'}
            sym = suit_syms.get(self.suit, self.suit)
            return f"{self.label}{sym}"
        else:
            return "##"

    def __repr__(self) -> str:
        face = self.display_str()
        return f"[{face}]"


class Deck:
    def __init__(self, seed: Optional[int] = None) -> None:
        self.cards: List[Card] = []
        self.seed = seed
        self.reset()

    def reset(self) -> None:
        """Creates standard 52-card deck, face down."""
        self.cards = [
            Card(suit=s, rank=r, is_face_up=False)
            for s in ['H', 'D', 'C', 'S']
            for r in range(1, 14)
        ]

    def shuffle(self) -> None:
        """Shuffles the deck using random or seed."""
        if self.seed is not None:
            random.seed(self.seed)
        else:
            random.seed()
        random.shuffle(self.cards)

    def draw(self) -> Card:
        """Draws/pops a card from the deck."""
        return self.cards.pop()

    def __len__(self) -> int:
        return len(self.cards)


class Pile(list):
    """Base pile representation."""
    @property
    def top_card(self) -> Optional[Card]:
        return self[-1] if self else None


class StockPile(Pile):
    """Stock pile representation (face-down draw pile)."""
    pass


class WastePile(Pile):
    """Waste pile representation (face-up drawn cards)."""
    pass


class FoundationPile(Pile):
    """Foundation pile representation (builds up from Ace to King by suit)."""
    pass


class TableauPile(Pile):
    """Tableau pile representation (7 columns of cards)."""
    pass


class GameState:
    def __init__(self, seed: Optional[int] = None) -> None:
        self.stock: StockPile = StockPile()
        self.waste: WastePile = WastePile()
        self.foundations: List[FoundationPile] = [FoundationPile() for _ in range(4)]
        self.tableau: List[TableauPile] = [TableauPile() for _ in range(7)]
        self.history: List[Dict[str, Any]] = []
        self.seed = seed
        self.deal()

    def serialize_state(self) -> Dict[str, Any]:
        """Returns a deep copy of the current state of all piles."""
        return {
            "stock": copy.deepcopy(self.stock),
            "waste": copy.deepcopy(self.waste),
            "foundations": copy.deepcopy(self.foundations),
            "tableau": copy.deepcopy(self.tableau),
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restores the state from a serialized state dictionary."""
        self.stock = copy.deepcopy(state["stock"])
        self.waste = copy.deepcopy(state["waste"])
        self.foundations = copy.deepcopy(state["foundations"])
        self.tableau = copy.deepcopy(state["tableau"])

    def record_history(self) -> None:
        """Saves current state to history before a mutating operation."""
        self.history.append(self.serialize_state())

    def undo(self) -> bool:
        """Undoes the last recorded move. Returns True if successful."""
        if not self.history:
            return False
        previous_state = self.history.pop()
        self.restore_state(previous_state)
        return True

    def deal(self) -> None:
        """Creates a standard 52-card deck, shuffles, and deals a new game."""
        deck = Deck(seed=self.seed)
        deck.shuffle()

        self.stock = StockPile()
        self.waste = WastePile()
        self.foundations = [FoundationPile() for _ in range(4)]
        self.tableau = [TableauPile() for _ in range(7)]
        self.history = []

        # Deal to Tableau
        # Col 0 gets 1 card, Col 1 gets 2 cards, ..., Col 6 gets 7 cards
        for i in range(7):
            for j in range(i + 1):
                card = deck.draw()
                if j == i:
                    card.is_face_up = True
                self.tableau[i].append(card)

        # Remaining cards go to Stock (face-down)
        self.stock = StockPile(deck.cards)

    def draw(self) -> bool:
        """Draws one card from Stock to Waste. Recycles Waste to Stock if Stock is empty."""
        self.record_history()
        
        if not self.stock:
            if not self.waste:
                # Both empty, nothing to do
                self.history.pop()  # don't save useless history
                return False
            # Recycle Waste back to Stock
            # When we flip waste back to stock, we preserve order by reversing
            self.stock = StockPile(reversed(self.waste))
            for card in self.stock:
                card.is_face_up = False
            self.waste = WastePile()
            return True

        card = self.stock.pop()
        card.is_face_up = True
        self.waste.append(card)
        return True

    def can_move_tableau_to_tableau(self, src_col: int, dest_col: int, card_idx: int) -> bool:
        if not (0 <= src_col < 7) or not (0 <= dest_col < 7):
            return False
        if src_col == dest_col:
            return False
        
        src_pile = self.tableau[src_col]
        if not src_pile or card_idx < 0 or card_idx >= len(src_pile):
            return False
        
        moving_card = src_pile[card_idx]
        if not moving_card.is_face_up:
            return False

        # Validate that the entire stack from card_idx to the end is face-up, alternating, and descending
        for i in range(card_idx, len(src_pile) - 1):
            c1 = src_pile[i]
            c2 = src_pile[i+1]
            if not c1.is_face_up or not c2.is_face_up:
                return False
            if (c1.is_red == c2.is_red) or (c1.rank != c2.rank + 1):
                return False

        # If dest is empty, moving card must be a King (rank 13)
        dest_pile = self.tableau[dest_col]
        if not dest_pile:
            return moving_card.rank == 13

        dest_card = dest_pile[-1]
        if not dest_card.is_face_up:
            return False

        # Opposite color and rank exactly one less
        return (moving_card.is_red != dest_card.is_red) and (moving_card.rank == dest_card.rank - 1)

    def can_move_waste_to_tableau(self, dest_col: int) -> bool:
        if not self.waste:
            return False
        if not (0 <= dest_col < 7):
            return False

        moving_card = self.waste[-1]
        dest_pile = self.tableau[dest_col]
        
        if not dest_pile:
            return moving_card.rank == 13

        dest_card = dest_pile[-1]
        if not dest_card.is_face_up:
            return False
        return (moving_card.is_red != dest_card.is_red) and (moving_card.rank == dest_card.rank - 1)

    def can_move_waste_to_foundation(self, dest_found: int) -> bool:
        if not self.waste:
            return False
        if not (0 <= dest_found < 4):
            return False

        moving_card = self.waste[-1]
        found_pile = self.foundations[dest_found]

        if not found_pile:
            return moving_card.rank == 1  # Ace

        top_found_card = found_pile[-1]
        return (moving_card.suit == top_found_card.suit) and (moving_card.rank == top_found_card.rank + 1)

    def can_move_tableau_to_foundation(self, src_col: int, dest_found: int) -> bool:
        if not (0 <= src_col < 7) or not (0 <= dest_found < 4):
            return False

        src_pile = self.tableau[src_col]
        if not src_pile:
            return False

        moving_card = src_pile[-1]
        if not moving_card.is_face_up:
            return False

        found_pile = self.foundations[dest_found]

        if not found_pile:
            return moving_card.rank == 1  # Ace

        top_found_card = found_pile[-1]
        return (moving_card.suit == top_found_card.suit) and (moving_card.rank == top_found_card.rank + 1)

    def can_move_foundation_to_tableau(self, src_found: int, dest_col: int) -> bool:
        if not (0 <= src_found < 4) or not (0 <= dest_col < 7):
            return False

        found_pile = self.foundations[src_found]
        if not found_pile:
            return False

        moving_card = found_pile[-1]
        dest_pile = self.tableau[dest_col]

        if not dest_pile:
            return moving_card.rank == 13

        dest_card = dest_pile[-1]
        if not dest_card.is_face_up:
            return False
        return (moving_card.is_red != dest_card.is_red) and (moving_card.rank == dest_card.rank - 1)

    def auto_reveal(self, col_idx: int) -> None:
        """Reveals the top card of a Tableau column if it is face-down."""
        pile = self.tableau[col_idx]
        if pile and not pile[-1].is_face_up:
            pile[-1].is_face_up = True

    def move_tableau_to_tableau(self, src_col: int, dest_col: int, card_idx: int) -> bool:
        if not self.can_move_tableau_to_tableau(src_col, dest_col, card_idx):
            return False
        
        self.record_history()
        src_pile = self.tableau[src_col]
        dest_pile = self.tableau[dest_col]
        
        moving_stack = src_pile[card_idx:]
        self.tableau[src_col] = TableauPile(src_pile[:card_idx])
        dest_pile.extend(moving_stack)
        
        self.auto_reveal(src_col)
        return True

    def move_waste_to_tableau(self, dest_col: int) -> bool:
        if not self.can_move_waste_to_tableau(dest_col):
            return False
        
        self.record_history()
        card = self.waste.pop()
        self.tableau[dest_col].append(card)
        return True

    def move_waste_to_foundation(self, dest_found: int) -> bool:
        if not self.can_move_waste_to_foundation(dest_found):
            return False

        self.record_history()
        card = self.waste.pop()
        self.foundations[dest_found].append(card)
        return True

    def move_tableau_to_foundation(self, src_col: int, dest_found: int) -> bool:
        if not self.can_move_tableau_to_foundation(src_col, dest_found):
            return False

        self.record_history()
        card = self.tableau[src_col].pop()
        self.foundations[dest_found].append(card)
        
        self.auto_reveal(src_col)
        return True

    def move_foundation_to_tableau(self, src_found: int, dest_col: int) -> bool:
        if not self.can_move_foundation_to_tableau(src_found, dest_col):
            return False

        self.record_history()
        card = self.foundations[src_found].pop()
        self.tableau[dest_col].append(card)
        return True

    def check_win(self) -> bool:
        """Check if all four foundation piles are fully built up to Kings."""
        for found_pile in self.foundations:
            if len(found_pile) != 13:
                return False
            if found_pile[-1].rank != 13:
                return False
        return True

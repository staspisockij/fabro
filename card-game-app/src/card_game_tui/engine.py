from enum import Enum
from typing import List, Optional, Dict, Tuple, NamedTuple
import random

class Suit(Enum):
    SPADES = "♠"
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"

    @property
    def color(self) -> str:
        if self in (Suit.HEARTS, Suit.DIAMONDS):
            return "RED"
        return "BLACK"

class Rank(Enum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

    @property
    def symbol(self) -> str:
        mapping = {
            Rank.ACE: "A",
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K"
        }
        return mapping.get(self, str(self.value))

class Card:
    def __init__(self, rank: Rank, suit: Suit):
        self.rank: Rank = rank
        self.suit: Suit = suit

    @property
    def color(self) -> str:
        return self.suit.color

    def is_opposite_color(self, other: "Card") -> bool:
        return self.color != other.color

    def can_be_placed_on_tableau(self, other: "Card") -> bool:
        """Checks if self can be placed on other (which is on top of a Tableau column)."""
        return self.is_opposite_color(other) and self.rank.value == other.rank.value - 1

    def __repr__(self) -> str:
        return f"{self.rank.symbol}{self.suit.value}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

class Move(NamedTuple):
    src_type: str  # 'C' (Tableau), 'F' (Freecell)
    src_idx: int   # 0-indexed
    dst_type: str  # 'C' (Tableau), 'F' (Freecell), 'A' (Foundation)
    dst_idx: int   # 0-indexed
    card_count: int = 1  # For sequence moves

class GameState:
    def __init__(self):
        self.tableau: List[List[Card]] = [[] for _ in range(8)]
        self.free_cells: List[Optional[Card]] = [None] * 4
        self.foundations: Dict[Suit, List[Card]] = {
            Suit.SPADES: [],
            Suit.HEARTS: [],
            Suit.DIAMONDS: [],
            Suit.CLUBS: []
        }
        self.history: List[Tuple[List[List[Card]], List[Optional[Card]], Dict[Suit, List[Card]]]] = []
        self.redo_history: List[Tuple[List[List[Card]], List[Optional[Card]], Dict[Suit, List[Card]]]] = []

    def deal(self, seed: Optional[int] = None) -> None:
        """Generates, shuffles, and distributes a standard 52-card deck."""
        deck = [Card(rank, suit) for suit in Suit for rank in Rank]
        if seed is not None:
            random.seed(seed)
        else:
            random.seed()
        random.shuffle(deck)

        self.tableau = [[] for _ in range(8)]
        self.free_cells = [None] * 4
        self.foundations = {s: [] for s in Suit}
        self.history.clear()
        self.redo_history.clear()

        # Deal cards: 7 to columns 0-3, 6 to columns 4-7
        for idx, card in enumerate(deck):
            col = idx % 8
            self.tableau[col].append(card)

    def save_state(self) -> Tuple[List[List[Card]], List[Optional[Card]], Dict[Suit, List[Card]]]:
        """Creates a deep copy of current piles to push to history."""
        tableau_copy = [col.copy() for col in self.tableau]
        free_cells_copy = list(self.free_cells)
        foundations_copy = {suit: pile.copy() for suit, pile in self.foundations.items()}
        return (tableau_copy, free_cells_copy, foundations_copy)

    def restore_state(self, state_tuple: Tuple[List[List[Card]], List[Optional[Card]], Dict[Suit, List[Card]]]) -> None:
        self.tableau, self.free_cells, self.foundations = state_tuple

    def push_history(self) -> None:
        self.history.append(self.save_state())
        self.redo_history.clear()

    def undo(self) -> bool:
        if not self.history:
            return False
        self.redo_history.append(self.save_state())
        self.restore_state(self.history.pop())
        return True

    def redo(self) -> bool:
        if not self.redo_history:
            return False
        self.history.append(self.save_state())
        self.restore_state(self.redo_history.pop())
        return True

    def execute_move(self, move: Move) -> Tuple[bool, str]:
        """
        Validates and executes a move.
        Automatically saves state to history before execution and clears redo history.
        Runs auto-home after a successful move.
        Returns (True, "") if successful, or (False, reason) if invalid.
        """
        valid, reason = validate_move(self, move)
        if not valid:
            return False, reason

        # Save state to history for undo
        self.push_history()

        # Retrieve source cards
        src_cards = get_source_cards(self, move.src_type, move.src_idx, move.card_count)

        # Remove card(s) from source
        if move.src_type == 'C':
            for _ in range(move.card_count):
                self.tableau[move.src_idx].pop()
        elif move.src_type == 'F':
            self.free_cells[move.src_idx] = None

        # Add card(s) to destination
        if move.dst_type == 'C':
            self.tableau[move.dst_idx].extend(src_cards)
        elif move.dst_type == 'F':
            self.free_cells[move.dst_idx] = src_cards[0]
        elif move.dst_type == 'A':
            card = src_cards[0]
            self.foundations[card.suit].append(card)

        # Automatically run auto-homing
        self.auto_home()

        return True, ""

    def is_safe_to_auto_home(self, card: Card) -> bool:
        """
        A card of rank R and suit S can be safely moved to its foundation if:
        1. It is a legal foundation move.
        2. All cards of rank R-1 of the opposite color are already in the foundation piles.
        3. All cards of rank R-2 of the same color are already in the foundation piles.
        """
        # 1. Must be a legal foundation move
        f_pile = self.foundations[card.suit]
        if not f_pile:
            if card.rank != Rank.ACE:
                return False
        else:
            top_card = f_pile[-1]
            if card.rank.value != top_card.rank.value + 1:
                return False

        # 2. Opposite color suits must have reached at least rank R - 1
        opp_suits = [s for s in Suit if s.color != card.suit.color]
        for os in opp_suits:
            os_pile = self.foundations[os]
            os_rank = os_pile[-1].rank.value if os_pile else 0
            if os_rank < card.rank.value - 1:
                return False

        # 3. Same color other suit must have reached at least rank R - 2
        same_suits = [s for s in Suit if s.color == card.suit.color and s != card.suit]
        for ss in same_suits:
            ss_pile = self.foundations[ss]
            ss_rank = ss_pile[-1].rank.value if ss_pile else 0
            if ss_rank < card.rank.value - 2:
                return False

        return True

    def auto_home(self) -> bool:
        """
        Automatically moves safe cards to foundations.
        Returns True if at least one card was auto-homed.
        """
        homed_any = False
        while True:
            moved_this_pass = False
            # Check FreeCells
            for i, card in enumerate(self.free_cells):
                if card is not None and self.is_safe_to_auto_home(card):
                    self.foundations[card.suit].append(card)
                    self.free_cells[i] = None
                    moved_this_pass = True
                    homed_any = True
                    break
            if moved_this_pass:
                continue

            # Check Tableau columns
            for i, col in enumerate(self.tableau):
                if col:
                    card = col[-1]
                    if self.is_safe_to_auto_home(card):
                        col.pop()
                        self.foundations[card.suit].append(card)
                        moved_this_pass = True
                        homed_any = True
                        break
            if not moved_this_pass:
                break
        return homed_any

    def is_won(self) -> bool:
        """
        Returns True if the game is won (all 52 cards are in the foundations).
        """
        return all(len(self.foundations[suit]) == 13 for suit in Suit)

    def is_lost(self) -> bool:
        """
        Returns True if no legal moves are possible and the game is not won.
        """
        if self.is_won():
            return False

        # We need to check if there is ANY legal move possible.
        # Sources from Tableau
        for src_idx in range(8):
            col = self.tableau[src_idx]
            if not col:
                continue
            
            # We can try moving sequences of length 1 up to len(col)
            for card_count in range(1, len(col) + 1):
                src_cards = col[-card_count:]
                if len(src_cards) > 1 and not is_valid_sequence(src_cards):
                    break  # Sequence gets increasingly invalid, so no longer sequences can be valid
                
                # Try destination: other Tableau columns
                for dst_idx in range(8):
                    if src_idx == dst_idx:
                        continue
                    move = Move('C', src_idx, 'C', dst_idx, card_count)
                    valid, _ = validate_move(self, move)
                    if valid:
                        return False
                
                # FreeCells (only valid for card_count == 1)
                if card_count == 1:
                    for dst_idx in range(4):
                        move = Move('C', src_idx, 'F', dst_idx, 1)
                        valid, _ = validate_move(self, move)
                        if valid:
                            return False
                            
                # Foundations (only valid for card_count == 1)
                if card_count == 1:
                    for dst_idx in range(4):
                        move = Move('C', src_idx, 'A', dst_idx, 1)
                        valid, _ = validate_move(self, move)
                        if valid:
                            return False
                            
        # Sources from FreeCells
        for src_idx in range(4):
            if self.free_cells[src_idx] is None:
                continue
            # Try destination: Tableau
            for dst_idx in range(8):
                move = Move('F', src_idx, 'C', dst_idx, 1)
                valid, _ = validate_move(self, move)
                if valid:
                    return False
            # Try destination: other FreeCells
            for dst_idx in range(4):
                if src_idx == dst_idx:
                    continue
                move = Move('F', src_idx, 'F', dst_idx, 1)
                valid, _ = validate_move(self, move)
                if valid:
                    return False
            # Try destination: Foundations
            for dst_idx in range(4):
                move = Move('F', src_idx, 'A', dst_idx, 1)
                valid, _ = validate_move(self, move)
                if valid:
                    return False
                     
        return True

def get_source_cards(state: GameState, src_type: str, src_idx: int, card_count: int) -> List[Card]:
    if src_type == 'C':
        col = state.tableau[src_idx]
        if len(col) < card_count:
            return []
        return col[-card_count:]
    elif src_type == 'F':
        if card_count != 1:
            return []
        card = state.free_cells[src_idx]
        return [card] if card is not None else []
    return []

def is_valid_sequence(cards: List[Card]) -> bool:
    if not cards:
        return False
    for i in range(len(cards) - 1):
        curr = cards[i]
        nxt = cards[i + 1]
        if not nxt.can_be_placed_on_tableau(curr):
            return False
    return True

def get_max_movable_cards(state: GameState, target_is_empty_col: bool) -> int:
    F = sum(1 for fc in state.free_cells if fc is None)
    T = sum(1 for col in state.tableau if not col)
    if target_is_empty_col and T > 0:
        T -= 1
    return (1 + F) * (2 ** T)

def validate_move(state: GameState, move: Move) -> Tuple[bool, str]:
    """
    Returns (True, "") if the move is legal, or (False, "reason") if illegal.
    """
    # 1. Fetch source card(s)
    src_cards = get_source_cards(state, move.src_type, move.src_idx, move.card_count)
    if not src_cards:
        return False, "Source is empty or invalid."

    # 2. If moving multiple cards, verify they form a valid alternating descending sequence
    if len(src_cards) > 1:
        if not is_valid_sequence(src_cards):
            return False, "Selected cards do not form a valid alternating color descending sequence."

    # 3. Validate Destination
    if move.dst_type == 'F':  # Destination is FreeCell
        if move.card_count > 1:
            return False, "Cannot move a sequence to a FreeCell."
        if state.free_cells[move.dst_idx] is not None:
            return False, "Target FreeCell is occupied."

    elif move.dst_type == 'A':  # Destination is Foundation
        if move.card_count > 1:
            return False, "Cannot move a sequence to a Foundation."
        card = src_cards[0]
        f_pile = state.foundations[card.suit]
        if not f_pile:
            if card.rank != Rank.ACE:
                return False, "Foundations must start with an Ace."
        else:
            top_card = f_pile[-1]
            if card.rank.value != top_card.rank.value + 1:
                return False, f"Cannot place {card} on {top_card}. Must be next rank up."

    elif move.dst_type == 'C':  # Destination is Tableau
        dest_col = state.tableau[move.dst_idx]
        first_src_card = src_cards[0]  # The highest rank card in the sequence being moved

        if not dest_col:
            # Moving sequence/card to empty tableau column
            # Verify supermove capacity limit
            max_allowed = get_max_movable_cards(state, target_is_empty_col=True)
            if len(src_cards) > max_allowed:
                return False, f"Insufficient empty FreeCells/Columns to move {len(src_cards)} cards (Max: {max_allowed})."
        else:
            dest_card = dest_col[-1]
            if not first_src_card.can_be_placed_on_tableau(dest_card):
                return False, f"Cannot place {first_src_card} on {dest_card}. Must be alternating color and rank-1."
            # Verify supermove capacity limit
            max_allowed = get_max_movable_cards(state, target_is_empty_col=False)
            if len(src_cards) > max_allowed:
                return False, f"Insufficient empty FreeCells/Columns to move {len(src_cards)} cards (Max: {max_allowed})."

    return True, ""

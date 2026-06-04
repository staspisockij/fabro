import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Union, Dict

class Suit(Enum):
    HEARTS = "H"
    DIAMONDS = "D"
    CLUBS = "C"
    SPADES = "S"

    @property
    def color(self) -> str:
        return "RED" if self in (Suit.HEARTS, Suit.DIAMONDS) else "BLACK"

    @property
    def symbol(self) -> str:
        return {
            Suit.HEARTS: "♥",
            Suit.DIAMONDS: "♦",
            Suit.CLUBS: "♣",
            Suit.SPADES: "♠"
        }[self]

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
    def label(self) -> str:
        if self.value == 1: return "A"
        if self.value == 11: return "J"
        if self.value == 12: return "Q"
        if self.value == 13: return "K"
        return str(self.value)

@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: Rank

    def __repr__(self) -> str:
        return f"{self.rank.label}{self.suit.symbol}"

class Deck:
    def __init__(self, seed: int = None):
        self.cards = [Card(suit, rank) for suit in Suit for rank in Rank]
        if seed is not None:
            random.seed(seed)
        random.shuffle(self.cards)

    def deal(self) -> List[List[Card]]:
        """Deals 52 cards into 8 columns."""
        tableaus: List[List[Card]] = [[] for _ in range(8)]
        for i, card in enumerate(self.cards):
            tableaus[i % 8].append(card)
        return tableaus

class LocationType(Enum):
    TABLEAU = auto()
    FREECELL = auto()
    FOUNDATION = auto()

@dataclass(frozen=True)
class Position:
    type: LocationType
    index: int  # 0-7 for Tableau, 0-3 for FreeCell, 0-3 for Foundation

@dataclass
class MoveRecord:
    from_pos: Position
    to_pos: Position
    cards: List[Card]  # Captured for single or sequence moves
    auto_moves: List['MoveRecord'] = None  # Nested moves triggered by auto-homing

    def __post_init__(self):
        if self.auto_moves is None:
            self.auto_moves = []

class GameState:
    def __init__(self, seed: int = None):
        self.tableaus: List[List[Card]] = Deck(seed).deal()
        self.freecells: List[Union[Card, None]] = [None] * 4
        self.foundations: Dict[Suit, List[Card]] = {suit: [] for suit in Suit}
        self.undo_stack: List[MoveRecord] = []
        self.redo_stack: List[MoveRecord] = []

    def get_card_at(self, position: Position) -> Union[Card, None]:
        if position.type == LocationType.FREECELL:
            return self.freecells[position.index]
        elif position.type == LocationType.FOUNDATION:
            pile = self.foundations[list(Suit)[position.index]]
            return pile[-1] if pile else None
        elif position.type == LocationType.TABLEAU:
            col = self.tableaus[position.index]
            return col[-1] if col else None
        return None

    def validate_move(self, from_pos: Position, to_pos: Position, count: int = 1) -> bool:
        """
        Calculates whether moving 'count' cards from from_pos to to_pos is legal.
        """
        if count < 1:
            return False

        if from_pos == to_pos:
            return False

        # Validate index boundaries
        if from_pos.type == LocationType.TABLEAU:
            if not (0 <= from_pos.index < 8):
                return False
        elif from_pos.type == LocationType.FREECELL:
            if not (0 <= from_pos.index < 4):
                return False
            if count != 1:
                return False
        elif from_pos.type == LocationType.FOUNDATION:
            return False
        else:
            return False

        if to_pos.type == LocationType.TABLEAU:
            if not (0 <= to_pos.index < 8):
                return False
        elif to_pos.type == LocationType.FREECELL:
            if not (0 <= to_pos.index < 4):
                return False
            if count != 1:
                return False
        elif to_pos.type == LocationType.FOUNDATION:
            if not (0 <= to_pos.index < 4):
                return False
            if count != 1:
                return False
        else:
            return False

        # Extract moving cards
        if from_pos.type == LocationType.FREECELL:
            card = self.freecells[from_pos.index]
            if card is None:
                return False
            moving_cards = [card]
        elif from_pos.type == LocationType.TABLEAU:
            col = self.tableaus[from_pos.index]
            if len(col) < count:
                return False
            moving_cards = col[-count:]
        else:
            return False

        # Validate sequence if moving multiple cards
        if count > 1:
            for i in range(count - 1):
                c1 = moving_cards[i]
                c2 = moving_cards[i+1]
                if c2.rank.value != c1.rank.value - 1:
                    return False
                if c2.suit.color == c1.suit.color:
                    return False

        # Validate destination constraints
        if to_pos.type == LocationType.FREECELL:
            if self.freecells[to_pos.index] is not None:
                return False

        elif to_pos.type == LocationType.FOUNDATION:
            target_suit = list(Suit)[to_pos.index]
            card = moving_cards[0]
            if card.suit != target_suit:
                return False
            
            foundation_pile = self.foundations[target_suit]
            if card.rank == Rank.ACE:
                if len(foundation_pile) != 0:
                    return False
            else:
                if len(foundation_pile) != card.rank.value - 1:
                    return False

        elif to_pos.type == LocationType.TABLEAU:
            dest_col = self.tableaus[to_pos.index]
            first_moving_card = moving_cards[0]
            if len(dest_col) > 0:
                dest_top_card = dest_col[-1]
                if first_moving_card.rank.value != dest_top_card.rank.value - 1:
                    return False
                if first_moving_card.suit.color == dest_top_card.suit.color:
                    return False

            # Capacity constraint
            empty_freecells = sum(1 for c in self.freecells if c is None)
            empty_tableaus = sum(1 for col in self.tableaus if len(col) == 0)

            if len(dest_col) == 0:
                transit_empty_tableaus = max(0, empty_tableaus - 1)
            else:
                transit_empty_tableaus = empty_tableaus

            max_cards = (1 + empty_freecells) * (2 ** transit_empty_tableaus)
            if count > max_cards:
                return False

        return True

    def execute_move(self, from_pos: Position, to_pos: Position, count: int = 1) -> bool:
        """
        Executes a move, saves it to the undo stack, runs auto-homing, and clears the redo stack.
        """
        if not self.validate_move(from_pos, to_pos, count):
            return False

        # Extract moving cards
        if from_pos.type == LocationType.FREECELL:
            moving_cards = [self.freecells[from_pos.index]]
        elif from_pos.type == LocationType.TABLEAU:
            moving_cards = self.tableaus[from_pos.index][-count:]
        else:
            return False

        move_record = MoveRecord(from_pos=from_pos, to_pos=to_pos, cards=moving_cards)
        
        # Apply the move
        self._apply_single_move(move_record)
        
        # Run auto-homing
        self._run_auto_homing(move_record)
        
        # Record on stacks
        self.undo_stack.append(move_record)
        self.redo_stack.clear()
        return True

    def _apply_single_move(self, record: MoveRecord):
        # Remove from from_pos
        if record.from_pos.type == LocationType.FREECELL:
            self.freecells[record.from_pos.index] = None
        elif record.from_pos.type == LocationType.TABLEAU:
            count = len(record.cards)
            self.tableaus[record.from_pos.index] = self.tableaus[record.from_pos.index][:-count]

        # Put to to_pos
        if record.to_pos.type == LocationType.FREECELL:
            self.freecells[record.to_pos.index] = record.cards[0]
        elif record.to_pos.type == LocationType.FOUNDATION:
            target_suit = list(Suit)[record.to_pos.index]
            self.foundations[target_suit].append(record.cards[0])
        elif record.to_pos.type == LocationType.TABLEAU:
            self.tableaus[record.to_pos.index].extend(record.cards)

    def _revert_single_move(self, record: MoveRecord):
        # Remove from to_pos
        if record.to_pos.type == LocationType.FREECELL:
            self.freecells[record.to_pos.index] = None
        elif record.to_pos.type == LocationType.FOUNDATION:
            target_suit = list(Suit)[record.to_pos.index]
            self.foundations[target_suit].pop()
        elif record.to_pos.type == LocationType.TABLEAU:
            count = len(record.cards)
            self.tableaus[record.to_pos.index] = self.tableaus[record.to_pos.index][:-count]

        # Put to from_pos
        if record.from_pos.type == LocationType.FREECELL:
            self.freecells[record.from_pos.index] = record.cards[0]
        elif record.from_pos.type == LocationType.TABLEAU:
            self.tableaus[record.from_pos.index].extend(record.cards)

    def _should_auto_home(self, card: Card) -> bool:
        """
        Checks if a card can be safely auto-homed to the foundations.
        """
        target_foundation = self.foundations[card.suit]
        if card.rank.value != len(target_foundation) + 1:
            return False

        # Opposite color suits must have all lower cards in the foundations
        if card.suit.color == "RED":
            opp_suits = [Suit.CLUBS, Suit.SPADES]
        else:
            opp_suits = [Suit.HEARTS, Suit.DIAMONDS]

        for s_opp in opp_suits:
            if len(self.foundations[s_opp]) < card.rank.value - 1:
                return False

        return True

    def _run_auto_homing(self, move_record: MoveRecord):
        """
        Scans freecells and tableau tops, moving eligible cards to foundations.
        Repeats until no more cards can be auto-homed.
        """
        any_homed = True
        while any_homed:
            any_homed = False
            
            # Check free cells
            for i, card in enumerate(self.freecells):
                if card is not None and self._should_auto_home(card):
                    from_p = Position(LocationType.FREECELL, i)
                    suit_idx = list(Suit).index(card.suit)
                    to_p = Position(LocationType.FOUNDATION, suit_idx)
                    
                    auto_rec = MoveRecord(from_pos=from_p, to_pos=to_p, cards=[card])
                    self._apply_single_move(auto_rec)
                    move_record.auto_moves.append(auto_rec)
                    
                    any_homed = True
                    break
            
            if any_homed:
                continue

            # Check tableaus
            for i, col in enumerate(self.tableaus):
                if col:
                    card = col[-1]
                    if self._should_auto_home(card):
                        from_p = Position(LocationType.TABLEAU, i)
                        suit_idx = list(Suit).index(card.suit)
                        to_p = Position(LocationType.FOUNDATION, suit_idx)
                        
                        auto_rec = MoveRecord(from_pos=from_p, to_pos=to_p, cards=[card])
                        self._apply_single_move(auto_rec)
                        move_record.auto_moves.append(auto_rec)
                        
                        any_homed = True
                        break

    def undo(self) -> bool:
        """Reverts the last move, including nested auto-homing steps."""
        if not self.undo_stack:
            return False
        
        move_record = self.undo_stack.pop()
        
        # Revert auto moves in reverse order
        for auto_move in reversed(move_record.auto_moves):
            self._revert_single_move(auto_move)
            
        # Revert the main move
        self._revert_single_move(move_record)
        
        self.redo_stack.append(move_record)
        return True

    def redo(self) -> bool:
        """Reapplies the last undone move."""
        if not self.redo_stack:
            return False
            
        move_record = self.redo_stack.pop()
        
        # Apply the main move
        self._apply_single_move(move_record)
        
        # Re-apply auto moves
        for auto_move in move_record.auto_moves:
            self._apply_single_move(auto_move)
            
        self.undo_stack.append(move_record)
        return True

    def check_win(self) -> bool:
        """Returns True if all 52 cards are in the Foundations."""
        return all(len(self.foundations[suit]) == 13 for suit in Suit)

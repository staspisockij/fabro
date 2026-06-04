import random
import copy

SUITS = {
    'S': '♠',  # Spades
    'H': '♥',  # Hearts
    'D': '♦',  # Diamonds
    'C': '♣'   # Clubs
}

SUIT_COLORS = {
    'S': 'black',
    'H': 'red',
    'D': 'red',
    'C': 'black'
}

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

class Card:
    def __init__(self, suit, rank):
        if suit not in SUITS:
            raise ValueError(f"Invalid suit: {suit}")
        if rank not in RANK_NAMES:
            raise ValueError(f"Invalid rank: {rank}")
        self.suit = suit
        self.rank = rank
        self.color = SUIT_COLORS[suit]

    def __repr__(self):
        return f"{RANK_NAMES[self.rank]}{SUITS[self.suit]}"

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank

    def to_dict(self):
        return {'suit': self.suit, 'rank': self.rank}

    @staticmethod
    def from_dict(d):
        if d is None:
            return None
        return Card(d['suit'], d['rank'])


class FreeCellGame:
    def __init__(self, seed=None):
        self.seed = seed
        self.cascades = [[] for _ in range(8)]
        self.free_cells = [None] * 4
        # Foundations: 0=Spades, 1=Hearts, 2=Diamonds, 3=Clubs
        self.foundations = [[] for _ in range(4)]
        self.foundation_suits = ['S', 'H', 'D', 'C']
        self.history = []
        self.move_count = 0
        self.deal()

    def deal(self):
        # Create deck of 52 cards
        deck = [Card(suit, rank) for suit in SUITS for rank in RANK_NAMES]
        
        # Shuffle
        rng = random.Random(self.seed)
        rng.shuffle(deck)

        # Reset state
        self.cascades = [[] for _ in range(8)]
        self.free_cells = [None] * 4
        self.foundations = [[] for _ in range(4)]
        self.history = []
        self.move_count = 0

        # Deal to cascades
        for i, card in enumerate(deck):
            col = i % 8
            self.cascades[col].append(card)

    def save_state(self):
        # Save deep copy of the state to history stack
        state = {
            'cascades': [[c.to_dict() for c in col] for col in self.cascades],
            'free_cells': [c.to_dict() if c else None for c in self.free_cells],
            'foundations': [[c.to_dict() for c in col] for col in self.foundations],
            'move_count': self.move_count
        }
        self.history.append(state)

    def undo(self):
        if not self.history:
            return False
        state = self.history.pop()
        self.cascades = [[Card.from_dict(c) for c in col] for col in state['cascades']]
        self.free_cells = [Card.from_dict(c) if c else None for c in state['free_cells']]
        self.foundations = [[Card.from_dict(c) for c in col] for col in state['foundations']]
        self.move_count = state['move_count']
        return True

    def check_win(self):
        # Won if all foundations have 13 cards
        return all(len(f) == 13 for f in self.foundations)

    def get_max_move_size(self, exclude_src_idx=None, exclude_dest_idx=None):
        F = sum(1 for cell in self.free_cells if cell is None)
        E = 0
        for idx, cascade in enumerate(self.cascades):
            if idx != exclude_src_idx and idx != exclude_dest_idx and not cascade:
                E += 1
        return (F + 1) * (2 ** E)

    @staticmethod
    def get_bottom_sequence(cascade):
        if not cascade:
            return []
        seq = [cascade[-1]]
        for i in range(len(cascade) - 2, -1, -1):
            card = cascade[i]
            prev = seq[-1]
            if card.rank == prev.rank + 1 and card.color != prev.color:
                seq.append(card)
            else:
                break
        seq.reverse()
        return seq

    def validate_and_move(self, src_type, src_idx, dest_type, dest_idx):
        """
        Executes a move if valid.
        src_type/dest_type can be 'cascade', 'freecell', or 'foundation'.
        src_idx/dest_idx are 0-based integers.
        Returns: (success_bool, message)
        """
        # Validate indices
        if src_type == 'cascade' and not (0 <= src_idx < 8):
            return False, "Invalid source cascade index"
        if src_type == 'freecell' and not (0 <= src_idx < 4):
            return False, "Invalid source free cell index"
        if src_type == 'foundation' and not (0 <= src_idx < 4):
            return False, "Invalid source foundation index"
        if dest_type == 'cascade' and not (0 <= dest_idx < 8):
            return False, "Invalid destination cascade index"
        if dest_type == 'freecell' and not (0 <= dest_idx < 4):
            return False, "Invalid destination free cell index"
        if dest_type == 'foundation' and not (0 <= dest_idx < 4):
            return False, "Invalid destination foundation index"

        # Disallow moving to the exact same pile
        if src_type == dest_type and src_idx == dest_idx:
            return False, "Cannot move to the same pile"

        # Get source cards/card
        if src_type == 'freecell':
            src_card = self.free_cells[src_idx]
            if src_card is None:
                return False, "Source free cell is empty"
            src_cards = [src_card]
        elif src_type == 'foundation':
            if not self.foundations[src_idx]:
                return False, "Source foundation is empty"
            src_cards = [self.foundations[src_idx][-1]]
        elif src_type == 'cascade':
            if not self.cascades[src_idx]:
                return False, "Source cascade is empty"
            # We will figure out how many cards to move based on the destination
            src_cards = []  # Will populate below based on destination
        else:
            return False, "Invalid source type"

        # Validate based on destination
        if dest_type == 'freecell':
            if self.free_cells[dest_idx] is not None:
                return False, "Destination free cell is already occupied"
            
            # If moving from cascade, we can only move the single bottom card
            if src_type == 'cascade':
                src_cards = [self.cascades[src_idx][-1]]

            # Execute move
            self.save_state()
            card_to_move = src_cards[0]
            # Remove from source
            if src_type == 'freecell':
                self.free_cells[src_idx] = None
            elif src_type == 'foundation':
                self.foundations[src_idx].pop()
            elif src_type == 'cascade':
                self.cascades[src_idx].pop()
            # Place in destination
            self.free_cells[dest_idx] = card_to_move
            self.move_count += 1
            self.auto_collect()
            return True, "Moved card to free cell"

        elif dest_type == 'foundation':
            # Target suit for this foundation slot
            target_suit = self.foundation_suits[dest_idx]

            # If moving from cascade, we can only move the single bottom card
            if src_type == 'cascade':
                src_cards = [self.cascades[src_idx][-1]]

            card_to_move = src_cards[0]
            if card_to_move.suit != target_suit:
                return False, f"Foundation is for {SUITS[target_suit]}, but card is {card_to_move}"

            dest_pile = self.foundations[dest_idx]
            if not dest_pile:
                if card_to_move.rank != 1:
                    return False, "Only an Ace can be placed on an empty foundation"
            else:
                top_card = dest_pile[-1]
                if card_to_move.rank != top_card.rank + 1:
                    return False, f"Cannot place {card_to_move} on {top_card} (must be consecutive rank)"

            # Execute move
            self.save_state()
            # Remove from source
            if src_type == 'freecell':
                self.free_cells[src_idx] = None
            elif src_type == 'foundation':
                self.foundations[src_idx].pop()
            elif src_type == 'cascade':
                self.cascades[src_idx].pop()
            # Place in destination
            self.foundations[dest_idx].append(card_to_move)
            self.move_count += 1
            self.auto_collect()
            return True, "Moved card to foundation"

        elif dest_type == 'cascade':
            dest_cascade = self.cascades[dest_idx]

            if src_type == 'freecell' or src_type == 'foundation':
                card_to_move = src_cards[0]
                if dest_cascade:
                    top_card = dest_cascade[-1]
                    if card_to_move.rank != top_card.rank - 1 or card_to_move.color == top_card.color:
                        return False, f"Cannot place {card_to_move} on {top_card} (must be alternating color and rank - 1)"
                # Execute move
                self.save_state()
                if src_type == 'freecell':
                    self.free_cells[src_idx] = None
                elif src_type == 'foundation':
                    self.foundations[src_idx].pop()
                dest_cascade.append(card_to_move)
                self.move_count += 1
                self.auto_collect()
                return True, "Moved card to cascade"

            elif src_type == 'cascade':
                # Move from cascade to cascade (potential sequence move)
                bottom_seq = self.get_bottom_sequence(self.cascades[src_idx])
                
                if not dest_cascade:
                    # Destination is empty. Move largest allowed sequence.
                    max_allowed = self.get_max_move_size(src_idx, dest_idx)
                    num_to_move = min(len(bottom_seq), max_allowed)
                    if num_to_move == 0:
                        return False, "No cards to move"
                    
                    self.save_state()
                    # Pop num_to_move cards from source, and append to dest
                    cards_to_move = self.cascades[src_idx][-num_to_move:]
                    self.cascades[src_idx] = self.cascades[src_idx][:-num_to_move]
                    self.cascades[dest_idx].extend(cards_to_move)
                    self.move_count += 1
                    self.auto_collect()
                    return True, f"Moved sequence of {num_to_move} cards to empty cascade"
                else:
                    # Destination is not empty. We must match the destination's top card.
                    dest_top = dest_cascade[-1]
                    # We need a card in bottom_seq of rank dest_top.rank - 1 and opposite color
                    match_card_idx = -1
                    for i, card in enumerate(bottom_seq):
                        if card.rank == dest_top.rank - 1 and card.color != dest_top.color:
                            match_card_idx = i
                            break
                    
                    if match_card_idx == -1:
                        return False, f"No valid card in sequence to place on {dest_top}"
                    
                    # Sequence to move is bottom_seq[match_card_idx:]
                    seq_to_move = bottom_seq[match_card_idx:]
                    num_to_move = len(seq_to_move)

                    max_allowed = self.get_max_move_size(src_idx, dest_idx)
                    if num_to_move > max_allowed:
                        return False, f"Cannot move {num_to_move} cards. Max allowed is {max_allowed}."

                    self.save_state()
                    self.cascades[src_idx] = self.cascades[src_idx][:-num_to_move]
                    self.cascades[dest_idx].extend(seq_to_move)
                    self.move_count += 1
                    self.auto_collect()
                    return True, f"Moved sequence of {num_to_move} cards to cascade"

        return False, "Unknown destination error"

    def auto_collect(self):
        """
        Scan all top cards (bottom of cascades and free cells) and move any safely collectible cards
        to the foundation. Repeat until no more cards can be collected.
        """
        while True:
            collected_any = False
            
            # Helper to check if card is safe to collect
            def is_safe_to_collect(card):
                if card.rank <= 2:
                    return True
                # Opposite suit colors must be at least card.rank - 1
                if card.color == 'red':
                    opposite_suits = ['S', 'C']
                else:
                    opposite_suits = ['H', 'D']

                opp_ranks = []
                for opp_suit in opposite_suits:
                    # Find corresponding foundation slot rank
                    found_idx = self.foundation_suits.index(opp_suit)
                    found_pile = self.foundations[found_idx]
                    opp_rank = found_pile[-1].rank if found_pile else 0
                    opp_ranks.append(opp_rank)
                
                return all(r >= card.rank - 1 for r in opp_ranks)

            # 1. Check Free Cells
            for idx, card in enumerate(self.free_cells):
                if card is not None:
                    found_idx = self.foundation_suits.index(card.suit)
                    found_pile = self.foundations[found_idx]
                    next_rank = found_pile[-1].rank + 1 if found_pile else 1
                    if card.rank == next_rank and is_safe_to_collect(card):
                        # Move to foundation
                        self.foundations[found_idx].append(card)
                        self.free_cells[idx] = None
                        collected_any = True
                        break # Start outer loop over to respect state changes

            if collected_any:
                continue

            # 2. Check Cascades
            for idx, cascade in enumerate(self.cascades):
                if cascade:
                    card = cascade[-1]
                    found_idx = self.foundation_suits.index(card.suit)
                    found_pile = self.foundations[found_idx]
                    next_rank = found_pile[-1].rank + 1 if found_pile else 1
                    if card.rank == next_rank and is_safe_to_collect(card):
                        # Move to foundation
                        self.foundations[found_idx].append(card)
                        cascade.pop()
                        collected_any = True
                        break # Start outer loop over

            if not collected_any:
                break

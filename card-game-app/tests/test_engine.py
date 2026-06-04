import unittest
from card_game_tui.engine import GameState, Card, RANK_NAMES, SUIT_SYMBOLS

class TestSpiderSolitaireEngine(unittest.TestCase):
    def test_initialization_1_suit(self):
        state = GameState(difficulty=1)
        # Check initial totals
        self.assertEqual(len(state.stock), 50)
        total_tableau_cards = sum(len(col) for col in state.tableau)
        self.assertEqual(total_tableau_cards, 54)
        self.assertEqual(state.completed_sequences, 0)
        self.assertEqual(state.score, 500)
        self.assertEqual(state.moves_count, 0)

        # Columns 1-4 (indices 0-3) should have 6 cards, last is face-up
        for i in range(4):
            self.assertEqual(len(state.tableau[i]), 6)
            self.assertTrue(state.tableau[i][-1].face_up)
            self.assertFalse(state.tableau[i][0].face_up)

        # Columns 5-10 (indices 4-9) should have 5 cards, last is face-up
        for i in range(4, 10):
            self.assertEqual(len(state.tableau[i]), 5)
            self.assertTrue(state.tableau[i][-1].face_up)
            self.assertFalse(state.tableau[i][0].face_up)

        # Verify all cards are Spades ('S')
        for col in state.tableau:
            for card in col:
                self.assertEqual(card.suit, 'S')
        for card in state.stock:
            self.assertEqual(card.suit, 'S')

    def test_initialization_2_suit(self):
        state = GameState(difficulty=2)
        suits = set()
        for col in state.tableau:
            for card in col:
                suits.add(card.suit)
        for card in state.stock:
            suits.add(card.suit)
        self.assertEqual(suits, {'S', 'H'})

    def test_initialization_4_suit(self):
        state = GameState(difficulty=4)
        suits = set()
        for col in state.tableau:
            for card in col:
                suits.add(card.suit)
        for card in state.stock:
            suits.add(card.suit)
        self.assertEqual(suits, {'S', 'H', 'D', 'C'})

    def test_can_deal_from_stock_restrictions(self):
        state = GameState(difficulty=1)
        # Initially, all columns have cards, so deal should be allowed
        self.assertTrue(state.can_deal_from_stock())

        # If we empty a column, deal is blocked
        state.tableau[0] = []
        self.assertFalse(state.can_deal_from_stock())

    def test_deal_from_stock_execution(self):
        state = GameState(difficulty=1)
        initial_stock_len = len(state.stock)
        self.assertTrue(state.deal_from_stock())
        self.assertEqual(len(state.stock), initial_stock_len - 10)
        self.assertEqual(state.score, 499)
        self.assertEqual(state.moves_count, 1)
        for col in state.tableau:
            self.assertTrue(col[-1].face_up)

    def test_movable_sequence_start_indices(self):
        state = GameState(difficulty=1)
        # Construct a known column state:
        # facedown, facedown, 8S (faceup), 7S (faceup), 6S (faceup)
        state.tableau[0] = [
            Card(10, 'S', face_up=False),
            Card(9, 'S', face_up=False),
            Card(8, 'S', face_up=True),
            Card(7, 'S', face_up=True),
            Card(6, 'S', face_up=True),
        ]
        indices = state.get_movable_sequence_start_indices(0)
        # Expected movable starts are indices 2, 3, 4 (because [8,7,6], [7,6], [6] are all valid descending)
        self.assertEqual(indices, [2, 3, 4])

        # If ranks don't match, sequence breaks
        state.tableau[0] = [
            Card(8, 'S', face_up=True),
            Card(6, 'S', face_up=True), # Break descending order
            Card(5, 'S', face_up=True),
        ]
        indices = state.get_movable_sequence_start_indices(0)
        self.assertEqual(indices, [1, 2]) # 6, 5 is valid sequence, but 8 is broken

        # If suits don't match, sequence breaks (even with descending ranks)
        state.tableau[0] = [
            Card(8, 'S', face_up=True),
            Card(7, 'H', face_up=True), # Suit break
            Card(6, 'H', face_up=True),
        ]
        indices = state.get_movable_sequence_start_indices(0)
        self.assertEqual(indices, [1, 2]) # 7H, 6H is valid, but 8S is broken because of suit

    def test_move_cards_validation_and_execution(self):
        state = GameState(difficulty=1)
        # Col 0: 6S (face_up)
        # Col 1: 7S (face_up)
        state.tableau[0] = [Card(10, 'S', False), Card(6, 'S', True)]
        state.tableau[1] = [Card(10, 'S', False), Card(7, 'S', True)]

        # Move 6S on top of 7S
        self.assertTrue(state.can_move(0, 1, 1))
        self.assertTrue(state.move_cards(0, 1, 1))

        # Check results
        self.assertEqual(len(state.tableau[0]), 1)
        # The facedown 10S in Col 0 should have been flipped faceup
        self.assertTrue(state.tableau[0][0].face_up)

        # Col 1 should now have 7S, 6S
        self.assertEqual(len(state.tableau[1]), 3)
        self.assertEqual(state.tableau[1][-2].rank, 7)
        self.assertEqual(state.tableau[1][-1].rank, 6)

        # Move details
        self.assertEqual(state.score, 499)
        self.assertEqual(state.moves_count, 1)

    def test_undo_functionality(self):
        state = GameState(difficulty=1)
        state.tableau[0] = [Card(10, 'S', False), Card(6, 'S', True)]
        state.tableau[1] = [Card(10, 'S', False), Card(7, 'S', True)]

        # Move
        state.move_cards(0, 1, 1)
        self.assertEqual(state.moves_count, 1)
        self.assertEqual(state.score, 499)

        # Undo
        self.assertTrue(state.undo())
        self.assertEqual(state.moves_count, 0)
        self.assertEqual(state.score, 500)
        self.assertEqual(len(state.tableau[0]), 2)
        self.assertFalse(state.tableau[0][0].face_up)
        self.assertTrue(state.tableau[0][1].face_up)
        self.assertEqual(len(state.tableau[1]), 2)

    def test_sequence_completion_and_clearing(self):
        state = GameState(difficulty=1)
        # Construct a complete run of King down to Ace
        run = [Card(rank, 'S', face_up=True) for rank in range(13, 0, -1)]
        # Put it in col 0 with 2 facedown cards underneath
        state.tableau[0] = [
            Card(2, 'S', face_up=False),
            Card(3, 'S', face_up=False),
        ] + run

        # Trigger completion check (ordinarily done inside moves/deals, but we call it directly here)
        state.check_and_clear_all_completed_sequences()

        # Completed sequences should be 1
        self.assertEqual(state.completed_sequences, 1)
        # The run of 13 cards should be removed from col 0
        self.assertEqual(len(state.tableau[0]), 2)
        # The top card of col 0 should now be faceup
        self.assertTrue(state.tableau[0][-1].face_up)
        # Score increases by 100 for completed sequence
        self.assertEqual(state.score, 600)

if __name__ == '__main__':
    unittest.main()

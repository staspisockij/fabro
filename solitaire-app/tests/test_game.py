import unittest
from solitaire_tui.game import GameState, Card

class TestSolitaireGame(unittest.TestCase):
    def setUp(self):
        # Use a fixed seed for reproducible tests
        self.game = GameState(seed=42)

    def test_initial_deal(self):
        # Verify 7 tableau columns have correct card counts (1 to 7)
        for i in range(7):
            self.assertEqual(len(self.game.tableau[i]), i + 1)
            # Top card of each column must be face-up
            self.assertTrue(self.game.tableau[i][-1].is_face_up)
            # Other cards in column must be face-down
            for j in range(i):
                self.assertFalse(self.game.tableau[i][j].is_face_up)

        # Foundations must be empty initially
        for f in self.game.foundations:
            self.assertEqual(len(f), 0)

        # Stock must contain the remaining cards (52 - 28 = 24)
        self.assertEqual(len(self.game.stock), 24)
        # Waste should be empty initially
        self.assertEqual(len(self.game.waste), 0)

    def test_draw_and_recycle(self):
        initial_stock_len = len(self.game.stock)
        
        # Draw all cards
        for _ in range(initial_stock_len):
            success = self.game.draw()
            self.assertTrue(success)

        self.assertEqual(len(self.game.stock), 0)
        self.assertEqual(len(self.game.waste), initial_stock_len)

        # Draw again to recycle
        success = self.game.draw()
        self.assertTrue(success)
        self.assertEqual(len(self.game.stock), initial_stock_len)
        self.assertEqual(len(self.game.waste), 0)

    def test_cannot_move_invalid_tableau_to_tableau(self):
        # Try to move a card to an empty slot or invalid card
        # Setup specific tableau configuration manually to test rules
        self.game.tableau[0] = [Card(suit='H', rank=5, is_face_up=True)]
        self.game.tableau[1] = [Card(suit='S', rank=7, is_face_up=True)]
        
        # Moving 5 of Hearts onto 7 of Spades is invalid (rank diff != 1)
        self.assertFalse(self.game.can_move_tableau_to_tableau(src_col=0, dest_col=1, card_idx=0))

        # Moving 5 of Hearts onto an empty column is invalid (must be King)
        self.game.tableau[2] = []
        self.assertFalse(self.game.can_move_tableau_to_tableau(src_col=0, dest_col=2, card_idx=0))

    def test_valid_tableau_to_tableau_move(self):
        self.game.tableau[0] = [Card(suit='H', rank=6, is_face_up=True)]
        self.game.tableau[1] = [
            Card(suit='C', rank=8, is_face_up=False),
            Card(suit='S', rank=7, is_face_up=True)
        ]

        # 6 of Hearts onto 7 of Spades: valid! (opposite color, rank = 7 - 1)
        self.assertTrue(self.game.can_move_tableau_to_tableau(src_col=0, dest_col=1, card_idx=0))

        # Perform the move
        success = self.game.move_tableau_to_tableau(src_col=0, dest_col=1, card_idx=0)
        self.assertTrue(success)
        self.assertEqual(len(self.game.tableau[0]), 0)
        self.assertEqual(len(self.game.tableau[1]), 3)
        self.assertEqual(self.game.tableau[1][-1].rank, 6)

    def test_auto_reveal(self):
        self.game.tableau[0] = [Card(suit='H', rank=6, is_face_up=True)]
        self.game.tableau[1] = [
            Card(suit='C', rank=8, is_face_up=False),
            Card(suit='S', rank=7, is_face_up=True)
        ]

        # Move 7 of Spades from tableau[1] to tableau[0] is invalid due to colors/ranks,
        # let's set up a valid case where a face-down card gets exposed and revealed.
        self.game.tableau[0] = [Card(suit='D', rank=8, is_face_up=True)]
        self.game.tableau[1] = [
            Card(suit='C', rank=10, is_face_up=False),
            Card(suit='S', rank=7, is_face_up=True)
        ]

        # Let's change tableau[0] top card to 8 of Diamonds (Red) and tableau[1] to 7 of Spades (Black)
        success = self.game.move_tableau_to_tableau(src_col=1, dest_col=0, card_idx=1)
        self.assertTrue(success)
        # Check that the face-down card left in tableau[1] (10 of Clubs) is now face-up!
        self.assertTrue(self.game.tableau[1][0].is_face_up)

    def test_undo_functionality(self):
        self.game.tableau[0] = [Card(suit='D', rank=8, is_face_up=True)]
        self.game.tableau[1] = [
            Card(suit='C', rank=10, is_face_up=False),
            Card(suit='S', rank=7, is_face_up=True)
        ]

        initial_state = self.game.serialize_state()

        success = self.game.move_tableau_to_tableau(src_col=1, dest_col=0, card_idx=1)
        self.assertTrue(success)

        # Undo the move
        undo_success = self.game.undo()
        self.assertTrue(undo_success)

        # Verify state is restored
        self.assertEqual(len(self.game.tableau[1]), 2)
        self.assertFalse(self.game.tableau[1][0].is_face_up)
        self.assertTrue(self.game.tableau[1][1].is_face_up)
        self.assertEqual(len(self.game.tableau[0]), 1)

    def test_win_condition(self):
        # Empty game state check_win should be False
        self.assertFalse(self.game.check_win())

        # Set up a winning board state
        suits = ['H', 'D', 'C', 'S']
        for i, suit in enumerate(suits):
            self.game.foundations[i] = [Card(suit=suit, rank=r, is_face_up=True) for r in range(1, 14)]

        self.assertTrue(self.game.check_win())

if __name__ == '__main__':
    unittest.main()

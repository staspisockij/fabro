import unittest
from engine import Card, FreeCellGame

class TestFreeCellEngine(unittest.TestCase):
    def test_card_creation(self):
        card = Card('H', 1)
        self.assertEqual(card.suit, 'H')
        self.assertEqual(card.rank, 1)
        self.assertEqual(card.color, 'red')
        self.assertEqual(str(card), "A♥")

    def test_deal(self):
        game = FreeCellGame(seed=42)
        # Check that 52 cards were dealt correctly
        total_cards = sum(len(c) for c in game.cascades)
        self.assertEqual(total_cards, 52)
        self.assertEqual(len(game.cascades[0]), 7)
        self.assertEqual(len(game.cascades[4]), 6)

    def test_get_bottom_sequence(self):
        # Create custom cascades to test sequence identification
        c1 = [
            Card('H', 13), # K♥
            Card('S', 12), # Q♠
            Card('H', 11), # J♥
            Card('C', 10), # 10♣
        ]
        seq = FreeCellGame.get_bottom_sequence(c1)
        self.assertEqual(len(seq), 4)
        self.assertEqual(seq[0].rank, 13)

        # Break sequence in middle
        c2 = [
            Card('H', 13), # K♥
            Card('H', 12), # Q♥ (same color, breaks sequence)
            Card('S', 11), # J♠
            Card('H', 10), # 10♥
        ]
        seq = FreeCellGame.get_bottom_sequence(c2)
        self.assertEqual(len(seq), 3)
        self.assertEqual(seq[0].rank, 12)

    def test_validate_and_move_to_free_cell(self):
        game = FreeCellGame(seed=42)
        # Try moving bottom card of first cascade to first free cell
        bottom_card = game.cascades[0][-1]
        success, msg = game.validate_and_move('cascade', 0, 'freecell', 0)
        self.assertTrue(success)
        self.assertEqual(game.free_cells[0], bottom_card)
        self.assertEqual(len(game.cascades[0]), 6)

    def test_undo(self):
        game = FreeCellGame(seed=42)
        original_cascade_len = len(game.cascades[0])
        success, msg = game.validate_and_move('cascade', 0, 'freecell', 0)
        self.assertTrue(success)
        
        self.assertEqual(len(game.cascades[0]), original_cascade_len - 1)
        self.assertIsNotNone(game.free_cells[0])

        undo_success = game.undo()
        self.assertTrue(undo_success)
        self.assertEqual(len(game.cascades[0]), original_cascade_len)
        self.assertIsNone(game.free_cells[0])

if __name__ == '__main__':
    unittest.main()

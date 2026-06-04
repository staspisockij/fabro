import sys
import os

# Add src to python path to import card_game_tui package correctly
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from card_game_tui.main import main

if __name__ == "__main__":
    main()

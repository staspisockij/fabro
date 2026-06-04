#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    # Get the directory of this script and point to card-game-app/main.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_main = os.path.join(current_dir, "card-game-app", "main.py")
    
    if not os.path.exists(app_main):
        print(f"Error: {app_main} not found.", file=sys.stderr)
        sys.exit(1)
        
    # Execute card-game-app/main.py with the same arguments
    os.execv(sys.executable, [sys.executable, app_main] + sys.argv[1:])

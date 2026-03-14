"""
MapleBot — Vision-Based MapleStory Grinding Bot
Entry point with hotkey controls.

Controls:
  F10  — Start / Resume grinding
  F11  — Pause / Unpause
  F12  — Stop and exit
  
Usage:
  python main.py              # Normal start
  python main.py --dry-run    # Test capture + bar reading without sending inputs
"""

import sys
import os
import time
import threading
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from core.window import WindowManager
from core.capture import capture_window
from core.config import load_config
from vision.bars import read_all_bars, calibrate_bars
from brain.state_machine import BotEngine


def dry_run(hwnd, config):
    """Test mode: capture screen and read bars without sending any inputs."""
    print("\n" + "="*50)
    print("  MapleBot — DRY RUN MODE")
    print("  (No inputs will be sent)")
    print("="*50)

    while True:
        try:
            frame = capture_window(hwnd)
            if frame is None:
                print("[DryRun] Capture failed!")
                time.sleep(1)
                continue

            bars = read_all_bars(frame)
            hp = bars.get("hp", -1)
            mp = bars.get("mp", -1)
            exp = bars.get("exp", -1)

            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] HP={hp:.1f}% | MP={mp:.1f}% | EXP={exp:.1f}%")

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n[DryRun] Stopped.")
            break


def main():
    parser = argparse.ArgumentParser(description="MapleBot — Vision-Based MapleStory Bot")
    parser.add_argument("--dry-run", action="store_true", help="Read-only mode (no inputs)")
    parser.add_argument("--calibrate", action="store_true", help="Run bar calibration and exit")
    args = parser.parse_args()

    # Load config
    config = load_config()

    # Find MapleStory window
    print("[MapleBot] Looking for MapleStory window...")
    wm = WindowManager()
    hwnd = wm.find_window()

    if not hwnd:
        print("[MapleBot] ERROR: MapleStory window not found!")
        print("[MapleBot] Make sure the game is running in windowed mode.")
        sys.exit(1)

    # Position window
    wm.position_window()

    # Calibration mode
    if args.calibrate:
        frame = capture_window(hwnd)
        if frame is not None:
            calibrate_bars(frame)
            print("\n[MapleBot] Calibration complete! Check debug_frames/ folder.")
        else:
            print("[MapleBot] Capture failed!")
        return

    # Dry run mode
    if args.dry_run:
        dry_run(hwnd, config)
        return

    # Full bot mode
    print("\n" + "="*50)
    print("  MapleBot — Vision Grinder")
    print("="*50)
    print()
    print("  Controls:")
    print("    Ctrl+C  — Stop bot")
    print()
    print("  Starting in 3 seconds...")
    print("  Make sure MapleStory is in a grinding map!")
    print()

    time.sleep(3)

    # Create and start engine
    engine = BotEngine(hwnd, config, verbose=True)

    # Create logs directory
    log_dir = config.get("logging", {}).get("log_dir", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Start the bot
    engine.start()


if __name__ == "__main__":
    main()

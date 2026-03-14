"""
MapleBot — Grind Brain for Kerning City Subway
Automated grinding loop: patrol platforms, attack monsters, loot drops.

Usage:
  C:\\Python312-32\\python.exe brain\\grind.py

Architecture:
  1. Memory hooks trick game into thinking it has focus (background movement)
  2. PostMessage sends attack/loot keys (already works in background)
  3. Detector finds monsters via color detection
  4. Brain decides: patrol → find mobs → attack → loot → repeat
"""
import sys
import time
import random

sys.path.insert(0, ".")

from core.window import WindowManager
from core.capture import capture_window
from core.detector import Detector
from core.memory_input import MemoryHook
from core.input import InputSender
from core.minimap import learn_map, detect_map


class GrindBrain:
    """Automated grinding loop for Kerning Subway."""

    # Character attack range (approximate pixels, Magic Claw range)
    ATTACK_RANGE_X = 120     # Horizontal attack reach
    ATTACK_RANGE_Y = 30      # Vertical tolerance

    # Platform Y positions (calibrated from live game analysis)
    PLATFORMS = {
        "ground":    {"y": 540, "x_min": 50,  "x_max": 780},
        "platform1": {"y": 390, "x_min": 50,  "x_max": 750},
        "platform2": {"y": 270, "x_min": 200, "x_max": 700},
        "platform3": {"y": 180, "x_min": 300, "x_max": 650},
    }

    # Timing constants
    WALK_SPEED = 0.5        # Seconds to walk ~100 pixels
    ATTACK_COOLDOWN = 0.6   # Seconds between attacks
    LOOT_DELAY = 0.3        # Seconds between loot attempts

    def __init__(self):
        self.wm = WindowManager()
        self.hwnd = None
        self.hook = None
        self.inp = None
        self.det = Detector()
        self.running = False

        # Stats
        self.kills = 0
        self.attacks = 0
        self.patrol_cycles = 0
        self.start_time = 0

    def setup(self):
        """Initialize all systems."""
        # Find game
        self.hwnd = self.wm.find_window()
        if not self.hwnd:
            print("[Brain] Game not found!")
            return False

        # Set up memory hooks for background movement
        self.hook = MemoryHook()
        if not self.hook.attach():
            return False
        if not self.hook.install():
            return False

        # Set up input sender with memory hook
        self.inp = InputSender(self.hwnd, memory_hook=self.hook)

        # Learn current map
        frame = capture_window(self.hwnd)
        if frame is not None:
            learn_map(frame, "subway_line1_area1",
                      "Kerning City Subway Line 1 <Area 1>")

        print("[Brain] All systems ready!")
        return True

    def teardown(self):
        """Clean up all hooks."""
        if self.hook:
            self.hook.release_all()
            self.hook.uninstall()
        self.running = False

    # ----------------------------------------------------------
    # Detection helpers
    # ----------------------------------------------------------
    def _get_state(self):
        """Capture frame and detect everything."""
        frame = capture_window(self.hwnd)
        if frame is None:
            return None, [], None

        detections = self.det.detect(frame)
        char = self.det.find_character(frame)

        return frame, detections, char

    def _find_nearby_monsters(self, detections, char):
        """Find monsters within attack range."""
        if char is None:
            return []

        nearby = []
        for d in detections:
            if d.type != "monster":
                continue
            dx = abs(d.center_x - char.center_x)
            dy = abs(d.center_y - char.center_y)
            if dx < self.ATTACK_RANGE_X and dy < self.ATTACK_RANGE_Y:
                nearby.append(d)

        return nearby

    def _find_closest_monster(self, detections, char):
        """Find the closest monster to the character."""
        if char is None:
            return None

        monsters = [d for d in detections if d.type == "monster"]
        if not monsters:
            return None

        # Sort by distance
        def dist(m):
            return abs(m.center_x - char.center_x) + abs(m.center_y - char.center_y) * 2
        
        return min(monsters, key=dist)

    # ----------------------------------------------------------
    # Actions
    # ----------------------------------------------------------
    def _attack(self):
        """Attack with ctrl (basic attack / Magic Claw)."""
        self.inp.press_key("ctrl", hold_time=0.05)
        self.attacks += 1

    def _loot(self, times=3):
        """Press Z to pick up items."""
        for _ in range(times):
            self.inp.press_key("z", hold_time=0.04)
            time.sleep(0.1)

    def _walk_toward(self, target_x, char_x, duration_cap=2.0):
        """Walk toward a target X position."""
        dx = target_x - char_x
        if abs(dx) < 20:
            return  # Already close enough

        walk_time = min(duration_cap, abs(dx) * self.WALK_SPEED / 100.0)
        walk_time = max(0.15, walk_time)

        if dx > 0:
            self.inp.hold_key("right", walk_time)
        else:
            self.inp.hold_key("left", walk_time)

    def _walk_and_attack(self, direction, duration=1.5):
        """Walk in a direction while attacking periodically."""
        key = "right" if direction > 0 else "left"
        self.inp.key_down(key)

        steps = int(duration / self.ATTACK_COOLDOWN)
        for _ in range(max(1, steps)):
            self._attack()
            time.sleep(self.ATTACK_COOLDOWN)

        self.inp.key_up(key)

    # ----------------------------------------------------------
    # Main grind loop
    # ----------------------------------------------------------
    def grind(self, max_minutes=60):
        """Main grinding loop."""
        self.running = True
        self.start_time = time.time()
        max_seconds = max_minutes * 60

        print(f"[Brain] Starting grind! Max time: {max_minutes} min")
        print("[Brain] Press Ctrl+C to stop.\n")

        try:
            while self.running:
                elapsed = time.time() - self.start_time
                if elapsed > max_seconds:
                    print(f"[Brain] Time limit reached ({max_minutes} min)")
                    break

                # Get current state
                frame, detections, char = self._get_state()
                if frame is None:
                    time.sleep(0.5)
                    continue

                monsters = [d for d in detections if d.type == "monster"]
                nearby = self._find_nearby_monsters(detections, char) if char else []

                # === DECISION TREE ===

                if nearby:
                    # Monsters in range! Attack!
                    self._attack()
                    time.sleep(self.ATTACK_COOLDOWN * 0.8)
                    # Attack a few more times to be sure
                    self._attack()
                    time.sleep(0.3)

                elif monsters and char:
                    # Monsters exist but not in range — walk toward closest
                    closest = self._find_closest_monster(detections, char)
                    if closest:
                        self._walk_toward(closest.center_x, char.center_x)
                        # Attack when we get there
                        self._attack()
                        time.sleep(0.3)

                else:
                    # No monsters visible — patrol!
                    self.patrol_cycles += 1
                    self._patrol_platform()

                # Loot periodically
                if self.attacks > 0 and self.attacks % 6 == 0:
                    self._loot(4)

                # Status every 20 attacks
                if self.attacks > 0 and self.attacks % 20 == 0:
                    mins = (time.time() - self.start_time) / 60
                    print(f"[Brain] {mins:.1f}m | Attacks: {self.attacks} | "
                          f"Patrols: {self.patrol_cycles} | "
                          f"Mobs visible: {len(monsters)}")

        except KeyboardInterrupt:
            print("\n[Brain] Interrupted!")
        finally:
            self.hook.release_all()
            elapsed = (time.time() - self.start_time) / 60
            print(f"\n[Brain] Session ended: {elapsed:.1f} minutes")
            print(f"  Attacks: {self.attacks}")
            print(f"  Patrol cycles: {self.patrol_cycles}")

    def _patrol_platform(self):
        """Patrol the current platform: walk right, attack, walk left, attack."""
        # Simple patrol: walk right → attack → walk left → attack
        self._walk_and_attack(direction=1, duration=2.0)
        time.sleep(0.2)
        self._loot(3)
        time.sleep(0.2)
        self._walk_and_attack(direction=-1, duration=2.0)
        time.sleep(0.2)
        self._loot(3)


# ============================================================
# Entry point
# ============================================================
def main():
    print("=" * 50)
    print("  MapleBot Grind — Kerning Subway")
    print("=" * 50)
    print()
    print("This will grind Bubblings in the background!")
    print("You can use your computer normally.")
    print()

    brain = GrindBrain()
    if not brain.setup():
        print("Setup failed!")
        return

    print("\n>>> CLICK YOUR IDE — Starting in 5 seconds <<<")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    try:
        brain.grind(max_minutes=60)
    finally:
        brain.teardown()
        print("[Brain] Cleaned up!")


if __name__ == "__main__":
    main()

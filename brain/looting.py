"""
MapleBot - Loot Collector
Handles item pickup by pressing the loot key while moving.
Walks short distances to pick up drops scattered on the ground.
"""

import time
import random


class LootCollector:
    """Handles item collection during grinding."""

    def __init__(self, input_sender, config, humanizer=None):
        self.input = input_sender
        self.humanizer = humanizer
        self.cfg = config

        keys = config.get("keys", {})
        self.loot_key = keys.get("loot", "z")
        self._loot_count = 0

    def quick_loot(self):
        """Quick loot — press Z several times in place."""
        presses = random.randint(4, 8)
        for _ in range(presses):
            self.input.press_key(self.loot_key, hold_time=0.04)
            time.sleep(random.uniform(0.06, 0.12))
        self._loot_count += presses

    def sweep_loot(self):
        """
        Sweep loot — move slightly left and right while looting.
        Covers more ground to pick up scattered drops.
        """
        # Walk right while looting
        self.input.key_down("right")
        for _ in range(4):
            self.input.press_key(self.loot_key, hold_time=0.04)
            time.sleep(random.uniform(0.08, 0.14))
        self.input.key_up("right")
        time.sleep(0.1)

        # Walk left while looting (back to original position)
        self.input.key_down("left")
        for _ in range(4):
            self.input.press_key(self.loot_key, hold_time=0.04)
            time.sleep(random.uniform(0.08, 0.14))
        self.input.key_up("left")

        self._loot_count += 8

    @property
    def stats(self):
        return {"loot_attempts": self._loot_count}

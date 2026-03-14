"""
MapleBot - Auto-Potion System
Monitors HP/MP bars and automatically uses potions when below thresholds.
Includes cooldown management to prevent potion spam.
"""

import time


class AutoPot:
    """Automatic potion system based on HP/MP bar readings."""

    def __init__(self, input_sender, config):
        self.input = input_sender
        self.cfg = config

        keys = config.get("keys", {})
        thresh = config.get("thresholds", {})
        timers = config.get("timers", {})

        self.hp_key = keys.get("pot_hp", "delete")
        self.mp_key = keys.get("pot_mp", "end")
        self.hp_threshold = thresh.get("hp_pot", 55)
        self.mp_threshold = thresh.get("mp_pot", 30)
        self.safe_hp = thresh.get("safe_hp", 20)
        self.pot_cooldown = timers.get("pot_cooldown", 1.2)

        self._last_hp_pot = 0
        self._last_mp_pot = 0
        self._hp_pot_count = 0
        self._mp_pot_count = 0

    def check_and_pot(self, hp_pct, mp_pct):
        """
        Check HP/MP levels and use potions if needed.
        
        Args:
            hp_pct: Current HP percentage (0-100)
            mp_pct: Current MP percentage (0-100)
        
        Returns:
            str describing what was done, or None
        """
        now = time.time()
        action = None

        # Emergency HP pot — instant, ignore cooldown
        if 0 < hp_pct < self.safe_hp:
            self.input.press_key(self.hp_key, hold_time=0.04)
            self._last_hp_pot = now
            self._hp_pot_count += 1
            time.sleep(0.15)
            # Spam a second pot for safety
            self.input.press_key(self.hp_key, hold_time=0.04)
            return "EMERGENCY_HP_POT"

        # Normal HP pot
        if 0 < hp_pct < self.hp_threshold:
            if now - self._last_hp_pot >= self.pot_cooldown:
                self.input.press_key(self.hp_key, hold_time=0.05)
                self._last_hp_pot = now
                self._hp_pot_count += 1
                action = "HP_POT"
                time.sleep(0.2)

        # MP pot
        if 0 < mp_pct < self.mp_threshold:
            if now - self._last_mp_pot >= self.pot_cooldown:
                self.input.press_key(self.mp_key, hold_time=0.05)
                self._last_mp_pot = now
                self._mp_pot_count += 1
                action = "MP_POT" if action is None else "HP_MP_POT"
                time.sleep(0.2)

        return action

    @property
    def stats(self):
        return {
            "hp_pots_used": self._hp_pot_count,
            "mp_pots_used": self._mp_pot_count,
        }

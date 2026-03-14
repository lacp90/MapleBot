"""
MapleBot - Buff Manager
Tracks buff timers and automatically rebuffs when they expire.
For I/L Mage: Magic Guard, Meditation, Booster, etc.
"""

import time


class BuffManager:
    """Timer-based buff management system."""

    def __init__(self, input_sender, config):
        self.input = input_sender
        self.cfg = config

        keys = config.get("keys", {})
        timers = config.get("timers", {})

        self.buff_interval = timers.get("buff_interval", 180)

        # Collect all buff keys from config
        self.buff_keys = []
        for i in range(1, 9):
            key_name = f"buff_{i}"
            if key_name in keys and keys[key_name]:
                self.buff_keys.append(keys[key_name])

        self._last_buff_time = 0
        self._buff_count = 0
        self._initial_buffs_done = False

    def needs_rebuff(self):
        """Check if it's time to rebuff."""
        if not self._initial_buffs_done:
            return True
        return time.time() - self._last_buff_time >= self.buff_interval

    def apply_buffs(self, humanizer=None):
        """
        Apply all configured buffs in sequence.
        
        Args:
            humanizer: Optional Humanizer instance for natural delays
        
        Returns:
            Number of buffs applied
        """
        if not self.buff_keys:
            return 0

        print(f"[Buffs] Applying {len(self.buff_keys)} buffs...")

        for key in self.buff_keys:
            self.input.press_key(key, hold_time=0.06)
            # Buff casting animation takes time
            delay = 0.8
            if humanizer:
                delay = humanizer.walk_duration(delay)
            time.sleep(delay)

        self._last_buff_time = time.time()
        self._buff_count += 1
        self._initial_buffs_done = True
        print(f"[Buffs] All buffs applied (session total: {self._buff_count})")
        return len(self.buff_keys)

    @property
    def time_until_rebuff(self):
        """Seconds until next rebuff is needed."""
        if not self._initial_buffs_done:
            return 0
        elapsed = time.time() - self._last_buff_time
        return max(0, self.buff_interval - elapsed)

    @property
    def stats(self):
        return {
            "buff_cycles": self._buff_count,
            "time_until_rebuff": round(self.time_until_rebuff),
        }

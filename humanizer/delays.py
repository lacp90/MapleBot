"""
MapleBot - Humanizer
Anti-detection timing layer. Adds natural human-like randomness to all actions.
No human presses keys with machine-perfect timing — this module ensures the bot
behaves with realistic variance.
"""

import time
import random
import math


class Humanizer:
    """Adds human-like randomness to bot actions."""

    def __init__(self, config):
        h = config.get("humanizer", {})
        self.enabled = h.get("enabled", True)
        self.delay_min = h.get("delay_min", 0.04)
        self.delay_max = h.get("delay_max", 0.18)
        self.pause_chance = h.get("pause_chance", 0.03)
        self.pause_min = h.get("pause_min", 0.5)
        self.pause_max = h.get("pause_max", 2.0)
        self.key_jitter_ms = h.get("key_jitter_ms", 15)
        self.walk_jitter = h.get("walk_jitter", 0.3)
        self.break_after_min = h.get("break_after_min", 45) * 60  # to seconds
        self.break_after_max = h.get("break_after_max", 90) * 60
        self.break_dur_min = h.get("break_duration_min", 3) * 60
        self.break_dur_max = h.get("break_duration_max", 10) * 60

        self._session_start = time.time()
        self._next_break = self._schedule_break()
        self._action_count = 0

    def _schedule_break(self):
        """Schedule the next break at a random future time."""
        return time.time() + random.uniform(self.break_after_min, self.break_after_max)

    def action_delay(self):
        """Wait a natural delay between actions. Uses gaussian distribution."""
        if not self.enabled:
            return
        
        # Gaussian centered between min/max for natural feel
        mean = (self.delay_min + self.delay_max) / 2
        std = (self.delay_max - self.delay_min) / 4
        delay = max(self.delay_min, random.gauss(mean, std))
        delay = min(delay, self.delay_max * 1.5)  # Cap outliers
        time.sleep(delay)

        self._action_count += 1

        # Random "thinking" pause
        if random.random() < self.pause_chance:
            pause = random.uniform(self.pause_min, self.pause_max)
            time.sleep(pause)

    def key_hold_time(self, base=0.05):
        """Add jitter to key hold duration."""
        if not self.enabled:
            return base
        jitter = random.uniform(-self.key_jitter_ms, self.key_jitter_ms) / 1000
        return max(0.02, base + jitter)

    def walk_duration(self, base):
        """Add jitter to walk duration."""
        if not self.enabled:
            return base
        jitter = random.uniform(-self.walk_jitter, self.walk_jitter)
        return max(0.5, base + jitter)

    def should_take_break(self):
        """Check if it's time for a periodic break."""
        if not self.enabled:
            return False
        return time.time() >= self._next_break

    def take_break(self):
        """Take a natural break. Returns the break duration in seconds."""
        duration = random.uniform(self.break_dur_min, self.break_dur_max)
        mins = duration / 60
        print(f"[Humanizer] Taking a {mins:.1f} minute break...")
        time.sleep(duration)
        self._next_break = self._schedule_break()
        self._action_count = 0
        print("[Humanizer] Break over, resuming.")
        return duration

    def random_micro_move(self):
        """Occasionally do a tiny random movement (fidget)."""
        if not self.enabled:
            return None
        if random.random() < 0.02:  # 2% chance
            direction = random.choice(["left", "right"])
            duration = random.uniform(0.1, 0.3)
            return (direction, duration)
        return None

    @property
    def session_minutes(self):
        """How long this session has been running."""
        return (time.time() - self._session_start) / 60

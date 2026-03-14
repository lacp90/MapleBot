"""
MapleBot - Attack Rotation Engine
Handles class-specific attack patterns for efficient grinding.
Currently optimized for I/L Mage but designed to be extensible.

I/L Mage rotation (low level):
  - Spam basic attack (Ctrl) or Energy Bolt
  - Use AoE skills when available (Cold Beam, Thunder Bolt, etc.)
  
I/L Mage rotation (mid level, 3rd job+):
  - Chain Lightning spam (main AoE)
  - Ice Strike / Thunder Spear for grouped mobs
  - Blizzard on cooldown (ultimate)
"""

import time
import random


class AttackRotation:
    """Manages the attack rotation pattern for grinding."""

    def __init__(self, input_sender, config, humanizer=None):
        self.input = input_sender
        self.humanizer = humanizer
        self.cfg = config

        keys = config.get("keys", {})
        grinding = config.get("grinding", {})
        timers = config.get("timers", {})

        # Key bindings
        self.attack_key = keys.get("attack", "ctrl")
        self.skill_1 = keys.get("skill_1", "shift")
        self.skill_2 = keys.get("skill_2", "a")
        self.skill_3 = keys.get("skill_3", "s")
        self.loot_key = keys.get("loot", "z")
        self.jump_key = keys.get("jump", "alt")

        # Timing
        self.attack_delay = timers.get("attack_delay", 0.35)
        self.loot_interval = timers.get("loot_interval", 8)
        self.attacks_per_spot = grinding.get("attacks_per_spot", 3)

        # Skill cooldowns
        self.skill_1_cd = grinding.get("skill_1_cooldown", 0)
        self.skill_2_cd = grinding.get("skill_2_cooldown", 0)
        self._last_skill_1 = 0
        self._last_skill_2 = 0
        self._last_loot = time.time()

        # Stats
        self._attack_count = 0
        self._skill_count = 0

    def attack_once(self):
        """Perform a single attack action."""
        now = time.time()

        # Decide: use skill or basic attack
        use_skill = False

        # Try skill_1 (main skill) if off cooldown
        if self.skill_1_cd == 0 or (now - self._last_skill_1 >= self.skill_1_cd):
            # Use main skill most of the time
            if random.random() < 0.7:
                use_skill = True
                self.input.press_key(self.skill_1, hold_time=self._hold())
                self._last_skill_1 = now
                self._skill_count += 1
            else:
                self.input.press_key(self.attack_key, hold_time=self._hold())
                self._attack_count += 1
        else:
            self.input.press_key(self.attack_key, hold_time=self._hold())
            self._attack_count += 1

        # Wait for attack animation
        delay = self.attack_delay
        if self.humanizer:
            delay += random.uniform(-0.05, 0.08)
        time.sleep(max(0.15, delay))

    def attack_combo(self, count=None):
        """
        Perform multiple attacks at current position.
        
        Args:
            count: Number of attacks. If None, uses config.
        
        Returns:
            Number of attacks performed
        """
        if count is None:
            count = self.attacks_per_spot
            # Add some variance
            count += random.randint(-1, 1)
            count = max(1, count)

        for i in range(count):
            self.attack_once()
            if self.humanizer:
                self.humanizer.action_delay()

        return count

    def should_loot(self):
        """Check if it's time for a loot pass."""
        return time.time() - self._last_loot >= self.loot_interval

    def loot_pass(self):
        """Do a loot pass — press loot key multiple times."""
        print("[Attack] Loot pass...")
        for _ in range(6):
            self.input.press_key(self.loot_key, hold_time=0.04)
            time.sleep(random.uniform(0.08, 0.15))
        self._last_loot = time.time()

    def jump_attack(self, direction=None):
        """Jump while attacking — good for aerial mobs or mobility."""
        if direction == "right":
            self.input.key_down("right")
            time.sleep(0.03)
        elif direction == "left":
            self.input.key_down("left")
            time.sleep(0.03)

        self.input.key_down(self.jump_key)
        time.sleep(0.05)
        self.input.press_key(self.attack_key, hold_time=self._hold())
        time.sleep(0.1)
        self.input.key_up(self.jump_key)

        if direction:
            time.sleep(0.1)
            self.input.key_up(direction)

        time.sleep(0.3)

    def _hold(self):
        """Get humanized key hold time."""
        base = 0.05
        if self.humanizer:
            return self.humanizer.key_hold_time(base)
        return base

    @property
    def stats(self):
        return {
            "attacks": self._attack_count,
            "skills": self._skill_count,
            "total_actions": self._attack_count + self._skill_count,
        }

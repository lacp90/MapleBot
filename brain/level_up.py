"""
MapleBot - Auto Level-Up Handler
Detects level-ups and automatically:
  1. Assigns ALL AP (ability points) to INT — pure mage build
  2. Assigns SP (skill points) following the optimal I/L mage build

How it works:
  - Level-up detection: EXP bar goes from ~99% → small% (wrap around)
  - AP allocation: Opens stat window (S key), clicks INT '+' button
  - SP allocation: Opens skill window (K key), clicks the correct skill's '+' button

Button positions are relative to the stat/skill window positions.
In MapleRoyals v62, the stat window and skill window are movable panels,
so we detect them by their title bar colors and content.

Alternative approach used here:
  Since clicking UI buttons is fragile (window position changes),
  we use a more reliable method:
  - For AP: Use the "Auto-Assign" button which dumps all AP into main stat
  - For SP: Click the '+' button next to each skill in priority order

  In v62 MapleRoyals, there's NO auto-assign for AP. We must click the
  '+' button next to INT manually. The stat window has a known layout.
"""

import time
import random
import cv2
import numpy as np


# =====================================================
# I/L MAGE SKILL POINT BUILD — EXACT ORDER
# Each entry: (skill_name, max_level, skill_index_in_window)
# skill_index = position from top in the skill window
# =====================================================

SKILL_BUILD_ORDER = {
    # === 1st Job (Magician) — Levels 8-30 ===
    "1st_job": {
        "job_level_range": (8, 30),
        "skills": [
            # (skill_name, points_to_add, notes)
            ("Energy Bolt", 1, "Initial attack — just 1 point"),
            ("Improving MaxMP Increase", 10, "MAX first — more MP pool"),
            ("Improving MP Recovery", 16, "MAX — saves potion money"),
            ("Magic Claw", 20, "MAX — main 1st job attack"),
            ("Magic Guard", 20, "MAX — critical survivability"),
            ("Magic Armor", 20, "MAX last"),
        ],
    },

    # === 2nd Job (I/L Wizard) — Levels 30-70 ===
    "2nd_job": {
        "job_level_range": (30, 70),
        "skills": [
            ("Teleport", 1, "Essential mobility — 1 point first"),
            ("Thunder Bolt", 1, "Start leveling with this"),
            ("Meditation", 20, "MAX early — party MA buff"),
            ("Spell Booster", 20, "MAX — faster casting"),
            ("Thunder Bolt", 30, "MAX — main AoE attack"),
            ("Cold Beam", 20, "MAX — freeze utility"),
            ("MP Eater", 20, "MAX — MP conservation"),
            ("Teleport", 20, "MAX — better mobility"),
            ("Slow", 20, "Leftover points"),
        ],
    },

    # === 3rd Job (I/L Mage) — Levels 70-120 ===
    "3rd_job": {
        "job_level_range": (70, 120),
        "skills": [
            ("Ice Strike", 1, "Start using immediately"),
            ("Elemental Amplification", 30, "MAX first — huge damage boost"),
            ("Ice Strike", 30, "MAX — main grinding skill 70-120"),
            ("Seal", 20, "MAX or skip"),
            ("Element Composition", 30, "MAX for bossing"),
            ("Ifrit", 30, "MAX summon for extra DPS"),
        ],
    },

    # === 4th Job (I/L Archmage) — Levels 120-200 ===
    "4th_job": {
        "job_level_range": (120, 200),
        "skills": [
            ("Chain Lightning", 30, "MAX first — main attack"),
            ("Blizzard", 30, "MAX — full map attack, NO cooldown"),
            ("Infinity", 30, "MAX — unlimited MP for 40s"),
            ("Maple Warrior", 30, "MAX — party stat boost"),
        ],
    },
}


class LevelUpHandler:
    """
    Handles level-up events:
    - Detects level-up from EXP bar reset
    - Allocates AP to INT
    - Allocates SP to the correct skill
    """

    def __init__(self, input_sender, config):
        self.input = input_sender
        self.config = config
        self._last_exp = -1
        self._level = config.get("character", {}).get("start_level", 7)
        self._total_ap_allocated = 0
        self._total_sp_allocated = 0
        self._sp_tracker = {}  # skill_name → points allocated so far

        # How many AP per level (always 5 in v62)
        self._ap_per_level = 5
        # How many SP per level (always 3 in v62)
        self._sp_per_level = 3

    def check_level_up(self, exp_current):
        """
        Detect level-up by watching EXP bar.
        Level up = EXP goes from high value down to low value.
        
        Returns True if level-up detected.
        """
        if self._last_exp < 0:
            self._last_exp = exp_current
            return False

        # Level up: EXP was high (>80%), now it's low (<30%)
        leveled_up = (self._last_exp > 80 and exp_current < 30)
        self._last_exp = exp_current

        if leveled_up:
            self._level += 1
            return True

        return False

    def allocate_ap(self):
        """
        Allocate all available AP to INT.
        Opens stat window → clicks INT '+' button 5 times → closes.
        """
        try:
            print(f"[LevelUp] Allocating {self._ap_per_level} AP → INT")

            # Open stat window
            self.input.press_key("s", hold_time=0.05)
            time.sleep(0.5)

            # Click INT '+' button 5 times (one for each AP)
            for i in range(self._ap_per_level):
                self._click_stat_button("int")
                time.sleep(random.uniform(0.15, 0.3))

            # Close stat window
            time.sleep(0.3)
            self.input.press_key("s", hold_time=0.05)
            time.sleep(0.3)

            self._total_ap_allocated += self._ap_per_level
            print(f"[LevelUp] AP done! Total INT allocated: {self._total_ap_allocated}")
        except Exception as e:
            print(f"[LevelUp] AP allocation failed: {e}")

    def allocate_sp(self):
        """
        Allocate SP to the next skill in the build order.
        Opens skill window → clicks the correct skill's '+' button.
        """
        try:
            job = self._get_current_job()
            if not job:
                return

            build = SKILL_BUILD_ORDER.get(job, {})
            skills = build.get("skills", [])

            # Find what skill needs points next
            target_skill = None
            for skill_name, max_pts, _notes in skills:
                current_pts = self._sp_tracker.get(skill_name, 0)
                if current_pts < max_pts:
                    target_skill = skill_name
                    break

            if not target_skill:
                return

            print(f"[LevelUp] Allocating {self._sp_per_level} SP → {target_skill}")

            # Open skill window
            self.input.press_key("k", hold_time=0.05)
            time.sleep(0.5)

            # Click '+' button for target skill (3 SP per level)
            for i in range(self._sp_per_level):
                current = self._sp_tracker.get(target_skill, 0)
                target_max = None
                for sn, mx, _ in skills:
                    if sn == target_skill:
                        target_max = mx
                        break
                if target_max and current >= target_max:
                    # This skill is maxed, find next
                    for sn, mx, _ in skills:
                        if self._sp_tracker.get(sn, 0) < mx:
                            target_skill = sn
                            print(f"[LevelUp] Skill maxed, switching to {target_skill}")
                            break

                self._click_skill_button(target_skill)
                self._sp_tracker[target_skill] = self._sp_tracker.get(target_skill, 0) + 1
                time.sleep(random.uniform(0.15, 0.3))

            # Close skill window
            time.sleep(0.3)
            self.input.press_key("k", hold_time=0.05)
            time.sleep(0.3)

            self._total_sp_allocated += self._sp_per_level
            print(f"[LevelUp] SP done! {target_skill} now at {self._sp_tracker.get(target_skill, 0)} pts")
        except Exception as e:
            print(f"[LevelUp] SP allocation failed: {e}")

    def handle_level_up(self, exp_current):
        """
        Full level-up handling: detect, allocate AP, allocate SP.
        Returns True if level-up was handled.
        """
        if not self.check_level_up(exp_current):
            return False

        # Wait a moment for the level-up animation
        time.sleep(random.uniform(1.0, 2.0))

        # Dismiss any level-up popup/text
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # Allocate AP (all to INT)
        self.allocate_ap()

        # Allocate SP (follows build order)
        self.allocate_sp()

        return True

    def _get_current_job(self):
        """Determine current job based on level."""
        if self._level < 30:
            return "1st_job"
        elif self._level < 70:
            return "2nd_job"
        elif self._level < 120:
            return "3rd_job"
        elif self._level >= 120:
            return "4th_job"
        return None

    def _click_stat_button(self, stat):
        """
        Click the '+' button for a specific stat in the stat window.
        Uses foreground_click (SendInput) — PostMessage doesn't work
        on MapleStory's UI buttons.
        """
        from core.input import foreground_click

        # Stat window '+' button positions (calibrated from live game, DPI-aware 1024x768)
        # Measured 2026-03-14 with stat window at default position
        STAT_BUTTONS = {
            "str": (390, 395),
            "dex": (390, 413),
            "int": (390, 432),
            "luk": (390, 450),
        }

        if stat not in STAT_BUTTONS:
            return

        x, y = STAT_BUTTONS[stat]
        foreground_click(self.input.hwnd, x, y)

    def _click_skill_button(self, skill_name):
        """
        Click the '+' button for a specific skill in the skill window.
        Uses foreground_click (SendInput) for real cursor movement.
        """
        from core.input import foreground_click

        job = self._get_current_job()
        skill_index = self._get_skill_index(skill_name, job)
        if skill_index < 0:
            return

        # Skill window '+' button positions (calibrated from screenshot)
        # Window: "SKILL INVENTORY" panel
        # Skills listed top to bottom, '+' button on right side
        # Row 1 at y=224, each row ~40px apart, x=726
        base_x = 726
        base_y = 224
        row_height = 40

        x = base_x
        y = base_y + (skill_index * row_height)
        foreground_click(self.input.hwnd, x, y)

    def _get_skill_index(self, skill_name, job):
        """Get the visual position index of a skill in the skill window."""
        SKILL_POSITIONS = {
            "1st_job": [
                "Improving MaxMP Increase", "Improving MP Recovery",
                "Magic Guard", "Magic Armor", "Magic Claw", "Energy Bolt",
            ],
            "2nd_job": [
                "MP Eater", "Meditation", "Teleport",
                "Spell Booster", "Cold Beam", "Thunder Bolt", "Slow",
            ],
            "3rd_job": [
                "Elemental Amplification", "Ice Strike",
                "Seal", "Element Composition", "Ifrit",
            ],
            "4th_job": [
                "Chain Lightning", "Blizzard",
                "Infinity", "Maple Warrior",
            ],
        }

        positions = SKILL_POSITIONS.get(job, [])
        try:
            return positions.index(skill_name)
        except ValueError:
            return -1

    @property
    def level(self):
        return self._level

    @property
    def stats(self):
        return {
            "level": self._level,
            "ap_allocated": self._total_ap_allocated,
            "sp_allocated": self._total_sp_allocated,
            "sp_distribution": dict(self._sp_tracker),
        }


# =====================================================
# I/L MAGE TRAINING PLAN — WHERE TO GRIND AT EACH LEVEL
# =====================================================

TRAINING_PLAN = {
    # Level range → (map, monsters, skill to use, notes)
    (8, 12): {
        "map": "Ellinia: Dungeon, Southern Forest I",
        "monsters": "Slime, Green Slime",
        "skill": "Energy Bolt → Magic Claw",
        "notes": "Stay near Ellinia, grind slimes. Use Magic Claw once maxed.",
    },
    (12, 18): {
        "map": "Henesys Pig Farm",
        "monsters": "Pig, Ribbon Pig",
        "skill": "Magic Claw",
        "notes": "Flat map, easy mobs. Good EXP for 1st job.",
    },
    (18, 25): {
        "map": "Kerning City Subway: Line 1",
        "monsters": "Bubbling, Jr. Necki",
        "skill": "Magic Claw",
        "notes": "Good density, stay until 25 or until you feel strong.",
    },
    (25, 30): {
        "map": "Land of Wild Boar 2",
        "monsters": "Wild Boar, Iron Boar",
        "skill": "Magic Claw",
        "notes": "Great EXP, push to 30 for 2nd job advancement!",
    },
    (30, 35): {
        "map": "Carnival Party Quest (CPQ)",
        "monsters": "Party Quest - join parties via All Chat",
        "skill": "Thunder Bolt (once you have it)",
        "notes": "FASTEST EXP 30-50. Type 'J> CPQ' in All Chat to find parties.",
    },
    (35, 50): {
        "map": "Ghost Ship 2 (GS2) or CPQ",
        "monsters": "Slimy, Ghost Pirate (LIGHTNING WEAK!)",
        "skill": "Thunder Bolt",
        "notes": "GS2 monsters are weak to lightning — AMAZING for I/L mage!",
    },
    (50, 70): {
        "map": "Ghost Ship 2/5 → Forest of Golem",
        "monsters": "GS mobs → Golems",
        "skill": "Thunder Bolt",
        "notes": "GS for EXP, Forest of Golem for GFA 60% scroll drops ($$)",
    },
    (70, 90): {
        "map": "Wolf Spider Cavern or Himes",
        "monsters": "Wolf Spider, Hime",
        "skill": "Ice Strike",
        "notes": "Ice Strike is your new main skill. Massive AoE + freeze.",
    },
    (90, 120): {
        "map": "Petrifighters (Singapore) or Skelegon (Leafre)",
        "monsters": "Petrifighter, Skelegon",
        "skill": "Ice Strike",
        "notes": "Need ~1200 MA to one-shot Petrifighters. Top EXP to 4th job.",
    },
    (120, 200): {
        "map": "Skelegon → Temple of Time → LHC",
        "monsters": "Various endgame mobs",
        "skill": "Blizzard + Chain Lightning",
        "notes": "Blizzard = full map attack with NO cooldown. Absolute god mode.",
    },
}


def get_training_plan(level):
    """Get the recommended training plan for the current level."""
    for (low, high), plan in TRAINING_PLAN.items():
        if low <= level < high:
            return plan
    return {"map": "Unknown", "monsters": "Unknown", "skill": "Unknown", "notes": "No plan for this level"}


if __name__ == "__main__":
    print("=== I/L Mage Training Plan ===\n")
    for lvl in [8, 15, 25, 30, 40, 55, 75, 100, 130]:
        plan = get_training_plan(lvl)
        print(f"Level {lvl}: {plan['map']}")
        print(f"  Mobs: {plan['monsters']}")
        print(f"  Skill: {plan['skill']}")
        print(f"  Tip: {plan['notes']}")
        print()

    print("=== Skill Build Order ===\n")
    for job, data in SKILL_BUILD_ORDER.items():
        print(f"{job} ({data['job_level_range'][0]}-{data['job_level_range'][1]}):")
        for skill, pts, notes in data["skills"]:
            print(f"  {skill} → {pts} pts ({notes})")
        print()

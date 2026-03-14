"""
MapleBot - Quest Handler
Manages quests: detects lightbulb indicators, navigates NPC dialogs,
accepts quests, tracks completion, and delivers completed quests.

Quest system in MapleRoyals v62:
  - Lightbulb icon above head/NPC: yellow = new quest available
  - Click lightbulb or press UP near NPC to start dialog
  - Enter/Y to advance dialog, select options
  - Quest Helper panel (right side) shows active quest progress
  - Press Q to open quest log

Quest types we handle:
  1. Kill quests — hunt X amount of monsters (done while grinding)
  2. Fetch quests — collect drops (also done while grinding)
  3. Travel quests — go talk to NPC (job advancement, deliveries)
  4. Job advancement — special quest chain at level 8/30/70/120

Detection methods:
  - Lightbulb: yellow circle above character ~(460, 540) area
  - Quest Helper panel: right side of screen, tracks progress
  - Quest complete: panel shows all items collected (green text)
"""

import time
import random
import cv2
import numpy as np


# =====================================================
# QUEST DATABASE — Magician path quests in MapleRoyals
# Each quest: name, level, npc, type, objective, reward
# =====================================================

MAGICIAN_QUESTS = {
    # === Pre-Job Advancement (Beginner) ===
    "marias_nutritious_juice": {
        "name": "Maria's Nutritious Juice",
        "level_req": 3,
        "npc": "Maria",
        "type": "fetch",
        "objectives": {"Mushroom Spore": 5, "Squishy Liquid": 1},
        "reward": "EXP + potions",
        "priority": 2,
    },
    "lucas_reply": {
        "name": "Lucas' Reply",
        "level_req": 3,
        "npc": "Lucas",
        "type": "delivery",
        "objectives": {"Lucas' Letter": 1},
        "reward": "EXP",
        "priority": 3,
    },
    "mais_first_training": {
        "name": "Mai's First Training",
        "level_req": 4,
        "npc": "Mai",
        "type": "fetch",
        "objectives": {"Tree Branch": 3, "Stump": 5},
        "reward": "EXP + equipment",
        "priority": 2,
    },
    "new_life": {
        "name": "New Life",
        "level_req": 3,
        "npc": "Olaf",
        "type": "fetch",
        "objectives": {"Red Snail Shell": 10, "Mushroom Spore": 10, "Snail Shell": 10},
        "reward": "EXP + mesos",
        "priority": 1,
    },

    # === Job Advancement ===
    "path_of_magician": {
        "name": "The Path of Magician",
        "level_req": 8,
        "npc": "Grendel the Really Old",
        "location": "Ellinia Magic Library",
        "type": "advancement",
        "objectives": {"Talk to Grendel": 1},
        "reward": "Job advancement to Magician + MP boost",
        "priority": 0,  # Highest priority
        "dialog_steps": [
            "enter",  # Start conversation
            "enter",  # Accept advancement
            "enter",  # Confirm
        ],
    },

    # === Post-Advancement Training Quests ===
    "beginner_mage_training_1": {
        "name": "Beginner Magician's 1st Training Session",
        "level_req": 8,
        "npc": "Grendel the Really Old",
        "type": "kill",
        "objectives": {"Slime": 8},
        "reward": "EXP",
        "priority": 2,
    },
    "beginner_mage_training_2": {
        "name": "Beginner Magician's 2nd Training Session",
        "level_req": 8,
        "npc": "Grendel the Really Old",
        "type": "kill",
        "objectives": {"Slime": 20},
        "reward": "EXP",
        "priority": 2,
    },
    "beginner_mage_training_3": {
        "name": "Beginner Magician's 3rd Training Session",
        "level_req": 10,
        "npc": "Grendel the Really Old",
        "type": "kill",
        "objectives": {"Slime": 35},
        "reward": "EXP + equipment",
        "priority": 2,
    },

    # === 2nd Job Advancement ===
    "2nd_job_advancement": {
        "name": "2nd Job Advancement - I/L Wizard",
        "level_req": 30,
        "npc": "Grendel the Really Old",
        "location": "Ellinia Magic Library",
        "type": "advancement",
        "objectives": {"Proof of Hero": 1},
        "reward": "Job advancement to I/L Wizard",
        "priority": 0,
        "notes": "Need to enter special map, kill mobs for proof",
    },

    # === 3rd Job Advancement ===
    "3rd_job_advancement": {
        "name": "3rd Job Advancement - I/L Mage",
        "level_req": 70,
        "npc": "Grendel the Really Old",
        "location": "Ellinia Magic Library → El Nath",
        "type": "advancement",
        "objectives": {"Dark Crystal": 1, "Talk to Holy Stone": 1},
        "reward": "Job advancement to I/L Mage",
        "priority": 0,
    },

    # === 4th Job Advancement ===
    "4th_job_advancement": {
        "name": "4th Job Advancement - I/L Archmage",
        "level_req": 120,
        "npc": "Grendel the Really Old",
        "location": "Leafre",
        "type": "advancement",
        "objectives": {"Heroic Star": 1, "Heroic Pentagon": 1},
        "reward": "Job advancement to I/L Archmage",
        "priority": 0,
    },
}


# Lightbulb detection — the bright circle icon above character
# From live screenshot: bulb at approximately (505, 475) — white/bright
LIGHTBULB_COLOR_WHITE = {
    "lower": np.array([200, 200, 200]),  # BGR — bright white
    "upper": np.array([255, 255, 255]),
}
LIGHTBULB_COLOR_YELLOW = {
    "lower": np.array([0, 180, 200]),    # BGR — bright yellow
    "upper": np.array([50, 255, 255]),
}
LIGHTBULB_REGION = {
    "x": 430,    # Area above character (slightly left of center)
    "y": 430,    # Above character head (calibrated from live at y=475)
    "w": 160,
    "h": 80,
}

# Quest Helper panel region (right side)
QUEST_HELPER_REGION = {
    "x": 720,
    "y": 50,
    "w": 300,
    "h": 400,
}


class QuestHandler:
    """
    Handles quest detection, acceptance, and completion.
    Works alongside the grinding system — kill/fetch quests
    complete naturally while grinding.
    """

    def __init__(self, input_sender, config, level=7):
        self.input = input_sender
        self.config = config
        self._level = level
        self._active_quests = []
        self._completed_quests = set()
        self._lightbulb_detected = False
        self._last_check_time = 0
        self._check_interval = 10  # Check every 10 seconds
        self._dialog_active = False

    def update_level(self, level):
        """Update character level for quest eligibility."""
        self._level = level

    def check_for_lightbulb(self, frame):
        """
        Detect the yellow lightbulb icon above the character's head.
        The lightbulb means a quest is available.
        
        Returns: True if lightbulb detected
        """
        lr = LIGHTBULB_REGION
        region = frame[lr["y"]:lr["y"]+lr["h"], lr["x"]:lr["x"]+lr["w"]]

        if region.size == 0:
            return False

        # Look for bright lightbulb pixels (white circle or yellow bulb)
        mask_white = cv2.inRange(region, 
                                 LIGHTBULB_COLOR_WHITE["lower"], 
                                 LIGHTBULB_COLOR_WHITE["upper"])
        mask_yellow = cv2.inRange(region,
                                  LIGHTBULB_COLOR_YELLOW["lower"],
                                  LIGHTBULB_COLOR_YELLOW["upper"])
        
        # Combine both masks
        mask = cv2.bitwise_or(mask_white, mask_yellow)
        
        # Look for circular bright region (the lightbulb shape)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            # Lightbulb icon is roughly 10-100 pixels area, circular
            if 10 < area < 200:
                # Check circularity
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * 3.14159 * area / (perimeter * perimeter)
                    if circularity > 0.3:  # Roughly circular
                        self._lightbulb_detected = True
                        return True
        
        self._lightbulb_detected = False
        return False

    def check_quest_helper(self, frame):
        """
        Read the Quest Helper panel on the right side.
        Detects if quests are shown and if any are completed.
        
        Returns: dict with quest_count and has_completed
        """
        qh = QUEST_HELPER_REGION
        panel = frame[qh["y"]:qh["y"]+qh["h"], qh["x"]:qh["x"]+qh["w"]]

        # Look for green text (completed objectives) in quest helper
        # Green text in quest helper: bright green like RGB(0, 255, 0)
        green_mask = cv2.inRange(panel, 
                                 np.array([0, 200, 0]),     # BGR lower
                                 np.array([80, 255, 80]))   # BGR upper
        green_count = np.sum(green_mask > 0)

        # Look for red text (incomplete objectives)
        red_mask = cv2.inRange(panel,
                                np.array([0, 0, 200]),
                                np.array([80, 80, 255]))
        red_count = np.sum(red_mask > 0)

        return {
            "visible": green_count + red_count > 50,
            "has_completed": green_count > 100 and red_count < 20,
            "green_pixels": green_count,
            "red_pixels": red_count,
        }

    def interact_with_lightbulb(self):
        """
        Click the lightbulb / interact with quest NPC.
        The lightbulb appears above the character's head.
        """
        # Click on the lightbulb area
        import win32gui
        import win32con
        import win32api

        # Lightbulb position (above character's head, center of screen)
        x = LIGHTBULB_REGION["x"] + LIGHTBULB_REGION["w"] // 2
        y = LIGHTBULB_REGION["y"] + LIGHTBULB_REGION["h"] // 2

        lparam = win32api.MAKELONG(x, y)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.05)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONUP, 0, lparam)
        time.sleep(1.0)

    def navigate_dialog(self, steps=5):
        """
        Navigate through an NPC dialog by pressing Enter.
        Most quest dialogs have 3-6 pages.
        
        Args:
            steps: Number of Enter presses to navigate through
        """
        self._dialog_active = True

        for i in range(steps):
            time.sleep(random.uniform(0.8, 1.5))  # Human reading speed
            self.input.press_key("enter", hold_time=0.05)

        time.sleep(0.5)
        self._dialog_active = False

    def accept_quest(self):
        """
        Accept a quest from the current NPC dialog.
        In v62, the Accept button is usually on the left side of the dialog.
        Click it or press Enter when highlighted.
        """
        # Most dialogs: Enter to accept
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

    def complete_quest(self):
        """
        Complete/deliver a quest to the NPC.
        In v62: talk to NPC, dialog shows completion text, press Enter.
        """
        # Walk up to NPC and interact
        self.input.press_key("up", hold_time=0.1)
        time.sleep(1.0)

        # Navigate through completion dialog
        self.navigate_dialog(steps=4)

        # Accept reward
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

    def handle_lightbulb(self, frame):
        """
        Full lightbulb handling flow:
        1. Detect lightbulb
        2. Click it
        3. Navigate dialog
        4. Accept quest
        
        Returns True if a quest was accepted.
        """
        now = time.time()
        if now - self._last_check_time < self._check_interval:
            return False
        self._last_check_time = now

        if not self.check_for_lightbulb(frame):
            return False

        # Found lightbulb — interact
        self.interact_with_lightbulb()
        time.sleep(1.0)

        # Navigate through dialog
        self.navigate_dialog(steps=4)

        # Accept the quest
        self.accept_quest()

        self._lightbulb_detected = False
        return True

    def get_available_quests(self):
        """Get quests available for current level."""
        available = []
        for qid, quest in MAGICIAN_QUESTS.items():
            if (quest["level_req"] <= self._level and 
                qid not in self._completed_quests):
                available.append(quest)

        # Sort by priority (0 = highest)
        available.sort(key=lambda q: q["priority"])
        return available

    def get_job_advancement_quest(self):
        """Check if a job advancement quest is available."""
        advancement_levels = {8: "path_of_magician", 30: "2nd_job_advancement", 
                             70: "3rd_job_advancement", 120: "4th_job_advancement"}
        for level, qid in advancement_levels.items():
            if self._level >= level and qid not in self._completed_quests:
                return MAGICIAN_QUESTS.get(qid)
        return None

    def should_handle_quests(self):
        """Check if we should pause grinding to handle quests."""
        # Job advancement is always priority
        adv = self.get_job_advancement_quest()
        if adv and adv["level_req"] == self._level:
            return True

        # Lightbulb is visible
        if self._lightbulb_detected:
            return True

        return False

    @property
    def stats(self):
        return {
            "level": self._level,
            "completed_quests": len(self._completed_quests),
            "lightbulb_detected": self._lightbulb_detected,
            "available_quests": len(self.get_available_quests()),
        }


if __name__ == "__main__":
    print("=== Magician Quest Database ===\n")

    # Show quests by level
    for level in [3, 8, 10, 30, 70, 120]:
        print(f"--- Level {level} ---")
        for qid, quest in MAGICIAN_QUESTS.items():
            if quest["level_req"] <= level:
                status = "★" if quest["priority"] == 0 else "·"
                print(f"  {status} {quest['name']} (Lv.{quest['level_req']}) — {quest['type']}")
                if quest.get("objectives"):
                    for obj, count in quest["objectives"].items():
                        print(f"      → {obj} x{count}")
        print()

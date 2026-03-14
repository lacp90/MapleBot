"""
MapleBot - Town Trip Manager
Handles the full cycle of going to town, selling, restocking, and returning:

Flow:
  1. Detect inventory nearing full (too many drops picked up)
  2. Use Nearest Town Scroll from inventory
  3. Walk to nearest NPC shop
  4. Sell all equipment drops (keep ETCs and use items)
  5. Walk to potion shop / General Store
  6. Buy HP and MP potions (restock to full stack)
  7. Use Nearest Town Scroll or walk back to training spot

NPC Interaction in v62:
  - Walk up to NPC and press UP key to talk
  - Dialog opens — click options or press Enter to continue
  - In shops: click item, click Sell/Buy, confirm with Enter
  - Hold Y to auto-confirm "Yes" prompts when selling

Inventory in v62:
  - Open with 'I' key
  - Tabs: Equip, Use, Setup, Etc, Cash
  - Items are in a grid layout
  - Full inventory = can't loot more items
"""

import time
import random
import cv2
import numpy as np


# Inventory window config
INVENTORY_KEY = "i"
INVENTORY_REGION = {
    "x": 480,
    "y": 150,
    "w": 200,
    "h": 350,
}

# Inventory tab positions (relative to game window)
# After opening inventory, these are the tab buttons at the top
INV_TABS = {
    "equip": (530, 178),
    "use": (560, 178),
    "setup": (590, 178),
    "etc": (620, 178),
    "cash": (650, 178),
}

# NPC interaction
NPC_TALK_KEY = "up"  # Press UP arrow near NPC to interact
NPC_CONFIRM_KEY = "enter"

# Town-specific NPC locations
# These are approximate x-positions where NPCs stand in common towns
# The bot will walk left/right to find them
TOWN_NPCS = {
    "henesys": {
        "general_store": {"direction": "right", "walk_time": 3},
        "potion_shop": {"direction": "right", "walk_time": 5},
    },
    "ellinia": {
        "general_store": {"direction": "left", "walk_time": 2},
        "potion_shop": {"direction": "left", "walk_time": 2},
    },
    "perion": {
        "general_store": {"direction": "right", "walk_time": 3},
        "potion_shop": {"direction": "right", "walk_time": 4},
    },
    "kerning": {
        "general_store": {"direction": "left", "walk_time": 3},
        "potion_shop": {"direction": "left", "walk_time": 3},
    },
    "lith_harbor": {
        "general_store": {"direction": "right", "walk_time": 2},
        "potion_shop": {"direction": "right", "walk_time": 4},
    },
}


class TownTripManager:
    """
    Manages full town trips:
    inventory check → town scroll → sell → restock pots → return
    """

    def __init__(self, input_sender, config, capture_fn):
        self.input = input_sender
        self.config = config
        self._capture_fn = capture_fn
        self._loot_count = 0
        self._loot_threshold = config.get("town_trip", {}).get("loot_threshold", 30)
        self._pot_restock_count = config.get("town_trip", {}).get("pot_restock", 100)
        self._trip_count = 0
        self._last_trip_time = 0
        self._min_trip_interval = 300  # Don't trip more than once every 5 min
        
        # Town scroll key (assign nearest town scroll to a key)
        self._town_scroll_key = config.get("keys", {}).get("town_scroll", None)
        
        # Track potions used
        self._pots_used_since_restock = 0

    def increment_loot(self):
        """Called every time the bot loots an item."""
        self._loot_count += 1

    def increment_pot_used(self):
        """Called every time a potion is used."""
        self._pots_used_since_restock += 1

    def needs_town_trip(self):
        """
        Check if we should go to town.
        Triggers:
          1. Looted too many items (inventory getting full)
          2. Used too many potions (need restock)
          3. Minimum interval between trips respected
        """
        now = time.time()
        if now - self._last_trip_time < self._min_trip_interval:
            return False

        # Check loot count
        if self._loot_count >= self._loot_threshold:
            return True

        # Check pot usage (rough estimate of remaining)
        if self._pots_used_since_restock >= self._pot_restock_count * 0.8:
            return True

        return False

    def execute_town_trip(self, hwnd):
        """
        Execute a full town trip cycle.
        
        Steps:
        1. Stop all actions, release keys
        2. Use Nearest Town Scroll
        3. Wait for teleport animation
        4. Sell items at NPC
        5. Buy potions
        6. Use scroll to return (or walk back)
        7. Resume grinding
        """
        self._trip_count += 1
        self._last_trip_time = time.time()

        # Step 1: Stop everything
        self._release_all_keys()
        time.sleep(0.5)

        # Step 2: Use town scroll
        used_scroll = self._use_town_scroll()
        if not used_scroll:
            return False

        # Step 3: Wait for teleport + map load
        time.sleep(random.uniform(3.0, 5.0))

        # Step 4: Sell items
        self._sell_items()

        # Step 5: Buy potions
        self._buy_potions()

        # Step 6: Return to training map
        # Use another nearest town scroll to return (won't work in town)
        # Instead, walk to portal and navigate back
        # For now: we note that the user should use a Return Map scroll
        # or have the bot walk back
        self._prepare_return()

        # Reset counters
        self._loot_count = 0
        self._pots_used_since_restock = 0

        return True

    def _use_town_scroll(self):
        """
        Use Nearest Town Scroll.
        Method 1: If bound to a hotkey, just press it
        Method 2: Open inventory, double-click the scroll
        """
        if self._town_scroll_key:
            self.input.press_key(self._town_scroll_key, hold_time=0.05)
            time.sleep(0.5)
            # Confirm usage dialog
            self.input.press_key("enter", hold_time=0.05)
            time.sleep(1.0)
            return True

        # Method 2: Open inventory and use scroll
        # Open inventory
        self.input.press_key(INVENTORY_KEY, hold_time=0.05)
        time.sleep(0.5)

        # Click the "Use" tab
        self._click(INV_TABS["use"])
        time.sleep(0.3)

        # The Nearest Town Scroll should be in the first slot
        # Double-click it (first item position in Use tab)
        first_slot = (505, 212)
        self._double_click(first_slot)
        time.sleep(0.5)

        # Confirm
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # Close inventory
        self.input.press_key(INVENTORY_KEY, hold_time=0.05)
        time.sleep(0.3)

        return True

    def _sell_items(self):
        """
        Sell equipment drops at NPC.
        
        Flow:
        1. Walk to nearby NPC (General Store)
        2. Talk to NPC (UP key)
        3. Select "Sell" option
        4. Click each equipment item to sell
        5. Confirm sales with Enter/Y
        6. Close dialog
        """
        # Walk toward nearest NPC (walk right for a bit)
        self.input.hold_key("right", random.uniform(2.0, 4.0))
        time.sleep(0.5)

        # Try to talk to NPC
        self.input.press_key(NPC_TALK_KEY, hold_time=0.1)
        time.sleep(1.0)

        # In NPC dialog, look for "Sell" option
        # Usually it's the 2nd option — click it or press Enter
        # In v62, shop dialog has Buy/Sell tabs at the top
        
        # Click potential NPC dialog area
        time.sleep(0.5)
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # Open inventory to sell from equipment tab
        self.input.press_key(INVENTORY_KEY, hold_time=0.05)
        time.sleep(0.5)

        # Click equip tab
        self._click(INV_TABS["equip"])
        time.sleep(0.3)

        # Sell items by clicking them one at a time
        # Equipment grid starts at approximately (505, 212)
        # Each slot is ~36x36 pixels, 4 columns
        grid_start_x = 505
        grid_start_y = 212
        slot_size = 36
        cols = 4
        rows = 6

        sold_count = 0
        for row in range(rows):
            for col in range(cols):
                if sold_count >= 20:  # Don't sell more than 20 items per trip
                    break
                x = grid_start_x + (col * slot_size) + slot_size // 2
                y = grid_start_y + (row * slot_size) + slot_size // 2

                # Click the item
                self._click((x, y))
                time.sleep(0.2)

                # Confirm sell with Enter
                self.input.press_key("enter", hold_time=0.05)
                time.sleep(0.15)

                sold_count += 1

        # Close inventory
        self.input.press_key(INVENTORY_KEY, hold_time=0.05)
        time.sleep(0.3)

        # Close NPC dialog
        self.input.press_key("escape", hold_time=0.05)
        time.sleep(0.5)

    def _buy_potions(self):
        """
        Buy potions from NPC shop.
        
        Flow:
        1. Walk to potion NPC (usually same shop or nearby)
        2. Open shop dialog
        3. Select potion
        4. Set quantity
        5. Buy
        """
        # Walk slightly to find another NPC or use same one
        self.input.hold_key("left", random.uniform(1.0, 2.0))
        time.sleep(0.5)

        # Talk to NPC
        self.input.press_key(NPC_TALK_KEY, hold_time=0.1)
        time.sleep(1.0)

        # Navigate to Buy option
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # In the buy dialog, we need to:
        # 1. Click the potion we want
        # 2. Set quantity (type number)
        # 3. Click Buy/confirm
        
        # Buy HP potions (click first potion in shop list)
        shop_first_item = (450, 250)
        self._click(shop_first_item)
        time.sleep(0.3)

        # Click Buy button or Enter
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # Buy quantity (type the number)
        quantity = str(self._pot_restock_count)
        for char in quantity:
            self.input.press_key(char, hold_time=0.03)
            time.sleep(0.1)
        
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # Buy MP potions (click second item)
        shop_second_item = (450, 285)
        self._click(shop_second_item)
        time.sleep(0.3)
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)
        for char in quantity:
            self.input.press_key(char, hold_time=0.03)
            time.sleep(0.1)
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # Close shop
        self.input.press_key("escape", hold_time=0.05)
        time.sleep(0.5)

    def _prepare_return(self):
        """
        Prepare to return to grinding map.
        Options:
        1. Use another Nearest Town Scroll (won't work in town)
        2. Walk to portal and navigate back
        3. Have a return scroll bound to hotkey
        
        For now, we'll use inventory scroll approach.
        """
        # Open inventory
        self.input.press_key(INVENTORY_KEY, hold_time=0.05)
        time.sleep(0.5)

        # Click Use tab
        self._click(INV_TABS["use"])
        time.sleep(0.3)

        # Use a Town Return Scroll or map-specific scroll
        # These need to be pre-stocked
        first_slot = (505, 212)
        self._double_click(first_slot)
        time.sleep(0.5)
        self.input.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

        # Close inventory
        self.input.press_key(INVENTORY_KEY, hold_time=0.05)
        time.sleep(0.3)

        # Wait for teleport
        time.sleep(random.uniform(3.0, 5.0))

    def _click(self, pos):
        """Click at a position using PostMessage."""
        import win32gui
        import win32con
        import win32api

        x, y = pos
        lparam = win32api.MAKELONG(x, y)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.05)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def _double_click(self, pos):
        """Double-click at a position."""
        import win32gui
        import win32con
        import win32api

        x, y = pos
        lparam = win32api.MAKELONG(x, y)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.03)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONUP, 0, lparam)
        time.sleep(0.08)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lparam)
        time.sleep(0.03)
        win32gui.PostMessage(self.input.hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def _release_all_keys(self):
        """Release all held keys."""
        for key in ["left", "right", "up", "down", "alt", "ctrl", "shift", "z"]:
            try:
                self.input.key_up(key)
            except Exception:
                pass

    @property
    def stats(self):
        return {
            "town_trips": self._trip_count,
            "items_looted_since_sell": self._loot_count,
            "pots_used_since_restock": self._pots_used_since_restock,
        }

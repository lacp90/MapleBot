"""
MapleBot - Background Input Sender
Sends keyboard inputs to the MapleStory window WITHOUT requiring it to be focused.
Uses Win32 PostMessage API so you can work on other things while the bot plays.
"""

import ctypes
import ctypes.wintypes
import time
import random
import win32gui
import win32con
import win32api

# ========================================
# MapleStory Key Code Mapping
# ========================================
# Maps friendly key names to (virtual key code, scan code) pairs
# Scan codes are important — MapleStory reads DirectInput scan codes

VK_MAP = {
    # Movement
    "left": (win32con.VK_LEFT, 0x4B),
    "right": (win32con.VK_RIGHT, 0x4D),
    "up": (win32con.VK_UP, 0x48),
    "down": (win32con.VK_DOWN, 0x50),

    # Actions
    "alt": (win32con.VK_MENU, 0x38),      # Jump
    "ctrl": (win32con.VK_CONTROL, 0x1D),   # Attack
    "shift": (win32con.VK_SHIFT, 0x2A),    # Special
    "space": (win32con.VK_SPACE, 0x39),
    "enter": (win32con.VK_RETURN, 0x1C),

    # Loot / Interact
    "z": (0x5A, 0x2C),
    "x": (0x58, 0x2D),

    # Potions / Items
    "insert": (win32con.VK_INSERT, 0x52),
    "delete": (win32con.VK_DELETE, 0x53),
    "home": (win32con.VK_HOME, 0x47),
    "end": (win32con.VK_END, 0x4F),
    "pageup": (win32con.VK_PRIOR, 0x49),
    "pagedown": (win32con.VK_NEXT, 0x51),

    # Function keys (buffs)
    "f1": (win32con.VK_F1, 0x3B),
    "f2": (win32con.VK_F2, 0x3C),
    "f3": (win32con.VK_F3, 0x3D),
    "f4": (win32con.VK_F4, 0x3E),
    "f5": (win32con.VK_F5, 0x3F),
    "f6": (win32con.VK_F6, 0x40),
    "f7": (win32con.VK_F7, 0x41),
    "f8": (win32con.VK_F8, 0x42),

    # Number keys
    "0": (0x30, 0x0B), "1": (0x31, 0x02), "2": (0x32, 0x03),
    "3": (0x33, 0x04), "4": (0x34, 0x05), "5": (0x35, 0x06),
    "6": (0x36, 0x07), "7": (0x37, 0x08), "8": (0x38, 0x09),
    "9": (0x39, 0x0A),

    # Letter keys
    "a": (0x41, 0x1E), "b": (0x42, 0x30), "c": (0x43, 0x2E),
    "d": (0x44, 0x20), "e": (0x45, 0x12), "f": (0x46, 0x21),
    "g": (0x47, 0x22), "h": (0x48, 0x23), "i": (0x49, 0x17),
    "j": (0x4A, 0x24), "k": (0x4B, 0x25), "l": (0x4C, 0x26),
    "m": (0x4D, 0x32), "n": (0x4E, 0x31), "o": (0x4F, 0x18),
    "p": (0x50, 0x19), "q": (0x51, 0x10), "r": (0x52, 0x13),
    "s": (0x53, 0x1F), "t": (0x54, 0x14), "u": (0x55, 0x16),
    "v": (0x56, 0x2F), "w": (0x57, 0x11), "y": (0x59, 0x15),
}


def _make_lparam(scan_code, key_up=False, extended=False):
    """Build the lParam for WM_KEYDOWN/WM_KEYUP messages."""
    repeat_count = 1
    lparam = repeat_count
    lparam |= (scan_code & 0xFF) << 16
    if extended:
        lparam |= 1 << 24
    if key_up:
        lparam |= 1 << 30  # Previous key state
        lparam |= 1 << 31  # Transition state
    return lparam


# ========================================
# SendInput for movement keys
# ========================================
# PostMessage doesn't work for arrow keys in MapleRoyals.
# SendInput sends real OS-level keyboard events.

_INPUT_KEYBOARD = 1
_KEYEVENTF_SCANCODE = 0x0008
_KEYEVENTF_KEYUP = 0x0002
_KEYEVENTF_EXTENDEDKEY = 0x0001

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]

class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _INPUTUNION)]

def _sendinput_key(scan_code, extended=False, key_up=False):
    """Send a real keyboard event via SendInput."""
    flags = _KEYEVENTF_SCANCODE
    if extended:
        flags |= _KEYEVENTF_EXTENDEDKEY
    if key_up:
        flags |= _KEYEVENTF_KEYUP
    inp = _INPUT()
    inp.type = _INPUT_KEYBOARD
    inp.ii.ki.wScan = scan_code
    inp.ii.ki.dwFlags = flags
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


class InputSender:
    """Sends keyboard inputs to MapleStory window."""

    EXTENDED_KEYS = {"left", "right", "up", "down", "insert", "delete",
                     "home", "end", "pageup", "pagedown"}

    # Keys that need pyautogui (PostMessage doesn't work for arrow keys)
    SENDINPUT_KEYS = {"left", "right", "up", "down"}
    _PYAG_KEYMAP = {"left": "left", "right": "right", "up": "up", "down": "down"}

    def __init__(self, hwnd):
        self.hwnd = hwnd
        # Focus game window ONCE at startup — never again
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            win32gui.SetForegroundWindow(hwnd)
            print("[Input] Game window focused (one-time)")
        except Exception:
            pass

    def key_down(self, key_name):
        """Press a key down (without releasing)."""
        key_name = key_name.lower()
        if key_name not in VK_MAP:
            print(f"[Input] Unknown key: {key_name}")
            return

        vk, scan = VK_MAP[key_name]
        extended = key_name in self.EXTENDED_KEYS

        if key_name in self.SENDINPUT_KEYS:
            import pyautogui
            pyautogui.keyDown(self._PYAG_KEYMAP[key_name])
        else:
            lparam = _make_lparam(scan, key_up=False, extended=extended)
            win32gui.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk, lparam)

    def key_up(self, key_name):
        """Release a key."""
        key_name = key_name.lower()
        if key_name not in VK_MAP:
            return

        vk, scan = VK_MAP[key_name]
        extended = key_name in self.EXTENDED_KEYS

        if key_name in self.SENDINPUT_KEYS:
            import pyautogui
            pyautogui.keyUp(self._PYAG_KEYMAP[key_name])
        else:
            lparam = _make_lparam(scan, key_up=True, extended=extended)
            win32gui.PostMessage(self.hwnd, win32con.WM_KEYUP, vk, lparam)

    def press_key(self, key_name, hold_time=0.05):
        """Press and release a key with a natural hold duration."""
        actual_hold = hold_time + random.uniform(-0.01, 0.02)
        actual_hold = max(0.02, actual_hold)
        self.key_down(key_name)
        time.sleep(actual_hold)
        self.key_up(key_name)

    def press_keys_combo(self, keys, hold_time=0.05):
        """Press multiple keys simultaneously."""
        for key in keys:
            self.key_down(key)
            time.sleep(0.01)
        time.sleep(hold_time)
        for key in reversed(keys):
            self.key_up(key)
            time.sleep(0.01)

    def hold_key(self, key_name, duration):
        """
        Hold a key for a specific duration.
        Movement: pyautogui (only works when game is focused).
        Other keys: PostMessage (works in background).
        """
        key_name = key_name.lower()
        if key_name not in VK_MAP:
            return

        if key_name in self.SENDINPUT_KEYS:
            import pyautogui
            pyautogui.keyDown(self._PYAG_KEYMAP[key_name])
            time.sleep(duration)
            pyautogui.keyUp(self._PYAG_KEYMAP[key_name])
        else:
            vk, scan = VK_MAP[key_name]
            extended = key_name in self.EXTENDED_KEYS
            lparam_down = _make_lparam(scan, key_up=False, extended=extended)
            lparam_up = _make_lparam(scan, key_up=True, extended=extended)
            win32gui.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk, lparam_down)
            time.sleep(duration)
            win32gui.PostMessage(self.hwnd, win32con.WM_KEYUP, vk, lparam_up)

    def walk_right(self, duration=1.0):
        """Walk right for a duration."""
        self.hold_key("right", duration)

    def walk_left(self, duration=1.0):
        """Walk left for a duration."""
        self.hold_key("left", duration)

    def jump(self):
        """Jump in place."""
        self.press_key("alt", hold_time=0.05)

    def jump_right(self):
        """Jump while moving right."""
        self.key_down("right")
        time.sleep(0.05)
        self.press_key("alt", hold_time=0.08)
        time.sleep(0.15)
        self.key_up("right")

    def jump_left(self):
        """Jump while moving left."""
        self.key_down("left")
        time.sleep(0.05)
        self.press_key("alt", hold_time=0.08)
        time.sleep(0.15)
        self.key_up("left")

    def attack(self, key="ctrl"):
        """Basic attack."""
        self.press_key(key, hold_time=0.05)

    def loot(self, key="z"):
        """Pick up items on the ground."""
        self.press_key(key, hold_time=0.04)


# ========================================
# Standalone test
# ========================================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from core.window import WindowManager

    wm = WindowManager()
    hwnd = wm.find_window()

    if not hwnd:
        print("MapleRoyals not found!")
        exit(1)

    wm.position_window()
    inp = InputSender(hwnd)

    print("\n=== Input Sender Test ===")
    print("This will send inputs to MapleRoyals in the BACKGROUND.")
    print("You can keep this terminal focused — the game doesn't need to be in front.")
    print()

    # Give user a moment to see the message
    print("Starting in 3 seconds...")
    time.sleep(3)

    # Test sequence: walk right, jump, attack
    print("[Test] Walking right for 1 second...")
    inp.walk_right(1.0)
    time.sleep(0.3)

    print("[Test] Jumping...")
    inp.jump()
    time.sleep(0.5)

    print("[Test] Attacking (Ctrl)...")
    inp.attack()
    time.sleep(0.3)

    print("[Test] Loot (Z)...")
    inp.loot()
    time.sleep(0.3)

    print("\n[Test] Done! Check MapleRoyals to see if the character responded.")
    print("If nothing happened, the game might need to be in windowed mode")
    print("or the input method may need adjustment (SendMessage vs PostMessage).")


# ===========================================================
# Foreground Mouse Click Support (for UI buttons)
# MapleStory's stat/skill window buttons require REAL mouse
# clicks — PostMessage mouse events are ignored by the UI.
# This uses pyautogui for reliable foreground clicks.
# ===========================================================

def foreground_click(hwnd, client_x, client_y, double=False):
    """
    Perform a REAL mouse click at (client_x, client_y) relative to game window.
    Uses pyautogui for maximum reliability.
    Coordinates are in 1024x768 client space.
    
    IMPORTANT: Do NOT resize the game window — MapleStory v62 stretches
    and breaks if the window dimensions change.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05

        # Set DPI awareness so ClientToScreen returns physical pixel coords
        # Without this, coordinates are wrong at 125%+ DPI scaling
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass  # Already set or not available

        # Get client area screen position (do NOT move/resize window!)
        pt = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))

        screen_x = pt.x + client_x
        screen_y = pt.y + client_y

        # Bring window to foreground
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.1)

        # Click with pyautogui (most reliable)
        if double:
            pyautogui.doubleClick(screen_x, screen_y)
        else:
            pyautogui.click(screen_x, screen_y)

        time.sleep(0.15)
    except Exception as e:
        print(f"[Input] foreground_click failed: {e}")

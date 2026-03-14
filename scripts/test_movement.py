"""
DEEP TEST: Last remaining background movement methods.
Tests SetFocus+SendMessage and thread keyboard state manipulation.
Run with MapleStory open and UNFOCUSED.
"""
import sys, time, ctypes, ctypes.wintypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
sys.path.insert(0, ".")

import win32gui, win32con
from core.window import WindowManager

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

wm = WindowManager()
hwnd = wm.find_window()
if not hwnd:
    print("Game not found!")
    exit(1)

VK_RIGHT = 0x27
VK_LEFT = 0x25
SCAN_RIGHT = 0x4D
SCAN_LEFT = 0x4B

def make_lp(scan, extended=True, repeat=False, up=False):
    lp = 1
    lp |= scan << 16
    if extended: lp |= 1 << 24
    if repeat:   lp |= 1 << 30
    if up:       lp |= (1 << 30) | (1 << 31)
    return lp

game_tid = user32.GetWindowThreadProcessId(hwnd, None)
our_tid = kernel32.GetCurrentThreadId()

print(f"Game HWND: {hwnd}, Game TID: {game_tid}, Our TID: {our_tid}")
print(">>> Click ANOTHER window NOW — 3 seconds <<<")
time.sleep(3)
fg = user32.GetForegroundWindow()
print(f"Foreground: {fg} (game={hwnd}, same={fg==hwnd})")

# ============================================================
# Test A: AttachThreadInput + SetFocus + SendMessage
# SetFocus changes keyboard input target WITHOUT changing foreground
# ============================================================
print("\n=== Test A: AttachThread + SetFocus + SendMessage (right, 2s) ===")
user32.AttachThreadInput(our_tid, game_tid, True)
old_focus = user32.SetFocus(hwnd)
print(f"  SetFocus returned old={old_focus}")

lp_d = make_lp(SCAN_RIGHT)
lp_r = make_lp(SCAN_RIGHT, repeat=True)
lp_u = make_lp(SCAN_RIGHT, up=True)

win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, VK_RIGHT, lp_d)
end = time.time() + 2.0
while time.time() < end:
    time.sleep(0.03)
    win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, VK_RIGHT, lp_r)
win32gui.SendMessage(hwnd, win32con.WM_KEYUP, VK_RIGHT, lp_u)

if old_focus:
    user32.SetFocus(old_focus)
user32.AttachThreadInput(our_tid, game_tid, False)
print("  Done test A")
time.sleep(1)

# ============================================================
# Test B: SetKeyboardState CONTINUOUSLY while PostMessage
# The game's GetKeyState might poll each frame
# ============================================================
print("\n=== Test B: Continuous SetKeyboardState + PostMessage (left, 2s) ===")
user32.AttachThreadInput(our_tid, game_tid, True)

lp_d = make_lp(SCAN_LEFT)
lp_u = make_lp(SCAN_LEFT, up=True)
win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_LEFT, lp_d)

key_state = (ctypes.c_byte * 256)()
end = time.time() + 2.0
while time.time() < end:
    user32.GetKeyboardState(key_state)
    key_state[VK_LEFT] = ctypes.c_byte(-128)  # 0x80 = pressed
    user32.SetKeyboardState(key_state)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_LEFT, make_lp(SCAN_LEFT, repeat=True))
    time.sleep(0.016)  # ~60fps

key_state[VK_LEFT] = ctypes.c_byte(0)
user32.SetKeyboardState(key_state)
win32gui.PostMessage(hwnd, win32con.WM_KEYUP, VK_LEFT, lp_u)
user32.AttachThreadInput(our_tid, game_tid, False)
print("  Done test B")
time.sleep(1)

# ============================================================
# Test C: WM_CHAR messages (some games use character input)
# ============================================================
print("\n=== Test C: WM_CHAR for arrow keys (right, 2s) ===")
end = time.time() + 2.0
while time.time() < end:
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_RIGHT, make_lp(SCAN_RIGHT))
    win32gui.PostMessage(hwnd, 0x0102, VK_RIGHT, make_lp(SCAN_RIGHT))  # WM_CHAR
    time.sleep(0.03)
win32gui.PostMessage(hwnd, win32con.WM_KEYUP, VK_RIGHT, make_lp(SCAN_RIGHT, up=True))
print("  Done test C")
time.sleep(1)

# ============================================================
# Test D: WM_ACTIVATE + WM_SETFOCUS + PostMessage
# Fake the game into thinking it has focus
# ============================================================
print("\n=== Test D: Fake WM_ACTIVATE + WM_SETFOCUS (left, 2s) ===")
# Tell the game it got activated
win32gui.PostMessage(hwnd, win32con.WM_ACTIVATE, 1, 0)  # WA_ACTIVE
win32gui.PostMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
time.sleep(0.1)

lp_d = make_lp(SCAN_LEFT)
lp_u = make_lp(SCAN_LEFT, up=True)
win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_LEFT, lp_d)
end = time.time() + 2.0
while time.time() < end:
    time.sleep(0.03)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_LEFT, make_lp(SCAN_LEFT, repeat=True))
win32gui.PostMessage(hwnd, win32con.WM_KEYUP, VK_LEFT, lp_u)
print("  Done test D")
time.sleep(1)

# ============================================================
# Test E: Child window enumeration - maybe input goes to child
# ============================================================
print("\n=== Test E: Checking for child windows ===")
children = []
def enum_child(child_hwnd, param):
    cls = win32gui.GetClassName(child_hwnd)
    text = win32gui.GetWindowText(child_hwnd)
    rect = win32gui.GetWindowRect(child_hwnd)
    children.append((child_hwnd, cls, text, rect))
    return True
win32gui.EnumChildWindows(hwnd, enum_child, None)
if children:
    for c in children:
        print(f"  Child: {c[0]}, Class: {c[1]}, Text: {c[2]}")
    # Try sending to first child
    child = children[0][0]
    print(f"\n  Sending arrow keys to child window {child}...")
    win32gui.PostMessage(child, win32con.WM_KEYDOWN, VK_RIGHT, make_lp(SCAN_RIGHT))
    end = time.time() + 2.0
    while time.time() < end:
        time.sleep(0.03)
        win32gui.PostMessage(child, win32con.WM_KEYDOWN, VK_RIGHT, make_lp(SCAN_RIGHT, repeat=True))
    win32gui.PostMessage(child, win32con.WM_KEYUP, VK_RIGHT, make_lp(SCAN_RIGHT, up=True))
else:
    print("  No child windows found")

print("\n=== ALL DEEP TESTS DONE ===")
print("Did the character move in ANY test (A/B/C/D/E)?")

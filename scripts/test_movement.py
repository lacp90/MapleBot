"""Test: pyautogui keyboard for movement — the nuclear option."""
import sys, time, ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
sys.path.insert(0, ".")

from core.window import WindowManager
import win32gui
import pyautogui

pyautogui.FAILSAFE = False

wm = WindowManager()
hwnd = wm.find_window()

# Focus game
try:
    win32gui.SetForegroundWindow(hwnd)
except:
    pass
time.sleep(0.5)

print("Test: pyautogui.keyDown('left') for 2s")
pyautogui.keyDown('left')
time.sleep(2.0)
pyautogui.keyUp('left')
print("Done left")

time.sleep(0.5)

print("Test: pyautogui.keyDown('right') for 2s")
pyautogui.keyDown('right')
time.sleep(2.0)
pyautogui.keyUp('right')
print("Done right")

print("\nDid the character move?")

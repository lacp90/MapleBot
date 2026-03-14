"""
Test: Can pyautogui/keybd_event send keys on a separate desktop?
This starts a bot-like process on MapleDesktop that sends keys.
The keys should go to whatever window is focused on MapleDesktop,
NOT to the user's current desktop.
"""
import ctypes
import subprocess
import sys
import time
import os
import tempfile

user32 = ctypes.windll.user32
GENERIC_ALL = 0x10000000
DESKTOP_NAME = "MapleTestDesktop"

# Create a script that sends keys from the hidden desktop
WORKER_SCRIPT = '''
import time
import ctypes

user32 = ctypes.windll.user32

# Wait for the desktop to be set up
time.sleep(2)

# Log what we see
hwnd = user32.GetForegroundWindow()
print(f"[Worker] Foreground on this desktop: {hwnd}")
print("[Worker] Sending right arrow via keybd_event for 3 seconds...")

VK_RIGHT = 0x27
SCAN_RIGHT = 0x4D
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

# Send right arrow using keybd_event
user32.keybd_event(VK_RIGHT, SCAN_RIGHT, KEYEVENTF_EXTENDEDKEY, 0)
time.sleep(3)
user32.keybd_event(VK_RIGHT, SCAN_RIGHT, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

print("[Worker] Done sending keys")
print("[Worker] Did the character move?")
'''

# Save worker script
worker_path = os.path.join(tempfile.gettempdir(), "desktop_key_test.py")
with open(worker_path, "w") as f:
    f.write(WORKER_SCRIPT)

print("=== Desktop Key Isolation Test ===")
print()

# Create desktop
hDesk = user32.CreateDesktopW(DESKTOP_NAME, None, None, 0, GENERIC_ALL, None)
if not hDesk:
    print("Failed to create desktop!")
    sys.exit(1)
print(f"Created desktop '{DESKTOP_NAME}'")

# The KEY INSIGHT: if we start the game process on this desktop,
# it becomes the foreground window there. Then keybd_event from
# a process on the same desktop should send keys TO the game.

# For now, test with just the key-sending worker
# In real use: start MapleStory first, then the bot, both on MapleDesktop

print("Starting key sender on hidden desktop...")
si = subprocess.STARTUPINFO()
si.lpDesktop = DESKTOP_NAME

# Start worker
proc = subprocess.Popen(
    [sys.executable, worker_path],
    startupinfo=si,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

print("Worker started. Waiting for it to finish...")
print("(If MapleStory is on your MAIN desktop, you should NOT see movement)")
print("(The keys go to the hidden desktop, not here)")

stdout, _ = proc.communicate(timeout=15)
print()
print("--- Worker output ---")
print(stdout)
print("--- End worker output ---")

# Cleanup
user32.CloseDesktop(hDesk)
print("Desktop closed. Test complete!")

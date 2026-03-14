"""
Test: Run MapleStory on a SEPARATE Windows Desktop.
Each desktop has its own foreground window — game stays focused
on its desktop while user works on the default desktop.
"""
import ctypes
import ctypes.wintypes
import time
import subprocess

# Win32 Desktop API
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_READOBJECTS = 0x0001
DESKTOP_SWITCHDESKTOP = 0x0100
GENERIC_ALL = 0x10000000

def create_desktop(name):
    """Create a new Windows Desktop."""
    hDesk = user32.CreateDesktopW(
        name,           # Desktop name
        None,           # Reserved
        None,           # Reserved  
        0,              # Flags
        GENERIC_ALL,    # Access
        None            # Security attributes
    )
    if hDesk:
        print(f"[Desktop] Created desktop '{name}' (handle: {hDesk})")
    else:
        print(f"[Desktop] Failed to create desktop: {ctypes.GetLastError()}")
    return hDesk

def run_on_desktop(desktop_name, exe_path):
    """Start a process on a specific named desktop."""
    si = subprocess.STARTUPINFO()
    si.lpDesktop = desktop_name
    
    proc = subprocess.Popen(
        exe_path,
        startupinfo=si,
        cwd=None
    )
    print(f"[Desktop] Started '{exe_path}' on desktop '{desktop_name}' (PID: {proc.pid})")
    return proc

def switch_to_desktop(hDesk):
    """Switch the display to a desktop."""
    result = user32.SwitchDesktop(hDesk)
    if result:
        print("[Desktop] Switched to desktop!")
    else:
        print(f"[Desktop] Switch failed: {ctypes.GetLastError()}")
    return result

# Test: Create a desktop and see if we can run notepad on it
print("=== Windows Desktop Isolation Test ===")
print("Creating a new desktop 'MapleDesktop'...")

hDesk = create_desktop("MapleDesktop")
if not hDesk:
    print("FAILED - can't create desktop. Need admin rights?")
    exit(1)

print("\nStarting notepad on 'MapleDesktop' (you won't see it on your screen)...")
proc = run_on_desktop("MapleDesktop", "notepad.exe")

print("\nWaiting 3 seconds...")
time.sleep(3)

# Check if we can switch to it
print("Switching to MapleDesktop (you'll see notepad)...")
switch_to_desktop(hDesk)
time.sleep(3)

# Switch back to default desktop
print("Switching back to default desktop...")
hDefault = user32.OpenDesktopW("Default", 0, False, GENERIC_ALL)
if hDefault:
    switch_to_desktop(hDefault)
    print("Back to default desktop!")
else:
    # Try winlogon default
    hDefault = user32.OpenDesktopW("Winsta0\\Default", 0, False, GENERIC_ALL)
    switch_to_desktop(hDefault)

# Cleanup
proc.terminate()
user32.CloseDesktop(hDesk)
print("\nTest complete! If you saw notepad appear and disappear, the desktop isolation works.")
print("We can run MapleStory on a separate desktop!")

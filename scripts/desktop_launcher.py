"""
Desktop Manager — Runs MapleStory + Bot on a separate Windows Desktop.
The game stays "focused" on its own desktop while the user works undisturbed.

Usage:
    python desktop_launcher.py          # Start game + bot on hidden desktop
    python desktop_launcher.py --peek   # Briefly switch to game desktop to see it
    python desktop_launcher.py --stop   # Kill everything on the game desktop
"""
import ctypes
import ctypes.wintypes
import subprocess
import sys
import time
import os
import signal

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GENERIC_ALL = 0x10000000
DESKTOP_NAME = "MapleDesktop"

# --- Paths (CHANGE THESE) ---
MAPLE_EXE = r"C:\MapleRoyals2026\MapleRoyals.exe"  # Local MapleStory path
BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_SCRIPT = os.path.join(BOT_DIR, "main.py")
PYTHON_EXE = sys.executable

LOCK_FILE = os.path.join(BOT_DIR, ".desktop_lock")


def create_desktop():
    """Create the MapleDesktop."""
    hDesk = user32.CreateDesktopW(DESKTOP_NAME, None, None, 0, GENERIC_ALL, None)
    if not hDesk:
        print(f"[!] Failed to create desktop: {ctypes.GetLastError()}")
        return None
    print(f"[Desktop] Created '{DESKTOP_NAME}'")
    return hDesk


def open_desktop():
    """Open existing MapleDesktop."""
    return user32.OpenDesktopW(DESKTOP_NAME, 0, False, GENERIC_ALL)


def get_default_desktop():
    """Get handle to the user's normal desktop."""
    return user32.OpenDesktopW("Default", 0, False, GENERIC_ALL)


def switch_desktop(hDesk):
    """Switch the visible desktop."""
    return user32.SwitchDesktop(hDesk)


def start_on_desktop(exe, args=None, cwd=None):
    """Start a process on the MapleDesktop using CreateProcessW directly."""
    
    # STARTUPINFOW structure
    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.wintypes.DWORD),
            ("lpReserved", ctypes.wintypes.LPWSTR),
            ("lpDesktop", ctypes.wintypes.LPWSTR),
            ("lpTitle", ctypes.wintypes.LPWSTR),
            ("dwX", ctypes.wintypes.DWORD),
            ("dwY", ctypes.wintypes.DWORD),
            ("dwXSize", ctypes.wintypes.DWORD),
            ("dwYSize", ctypes.wintypes.DWORD),
            ("dwXCountChars", ctypes.wintypes.DWORD),
            ("dwYCountChars", ctypes.wintypes.DWORD),
            ("dwFillAttribute", ctypes.wintypes.DWORD),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("wShowWindow", ctypes.wintypes.WORD),
            ("cbReserved2", ctypes.wintypes.WORD),
            ("lpReserved2", ctypes.c_void_p),
            ("hStdInput", ctypes.wintypes.HANDLE),
            ("hStdOutput", ctypes.wintypes.HANDLE),
            ("hStdError", ctypes.wintypes.HANDLE),
        ]
    
    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", ctypes.wintypes.HANDLE),
            ("hThread", ctypes.wintypes.HANDLE),
            ("dwProcessId", ctypes.wintypes.DWORD),
            ("dwThreadId", ctypes.wintypes.DWORD),
        ]
    
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    si.lpDesktop = DESKTOP_NAME
    
    pi = PROCESS_INFORMATION()
    
    cmd_line = f'"{exe}"' if not args else f'"{exe}" {args}'
    
    # Set argument types for CreateProcessW
    kernel32.CreateProcessW.argtypes = [
        ctypes.wintypes.LPCWSTR,  # lpApplicationName
        ctypes.wintypes.LPWSTR,   # lpCommandLine
        ctypes.c_void_p,          # lpProcessAttributes
        ctypes.c_void_p,          # lpThreadAttributes
        ctypes.wintypes.BOOL,     # bInheritHandles
        ctypes.wintypes.DWORD,    # dwCreationFlags
        ctypes.c_void_p,          # lpEnvironment
        ctypes.wintypes.LPCWSTR,  # lpCurrentDirectory
        ctypes.POINTER(STARTUPINFOW), # lpStartupInfo
        ctypes.POINTER(PROCESS_INFORMATION) # lpProcessInformation
    ]
    kernel32.CreateProcessW.restype = ctypes.wintypes.BOOL

    result = kernel32.CreateProcessW(
        None,           # lpApplicationName
        cmd_line,       # lpCommandLine
        None,           # lpProcessAttributes
        None,           # lpThreadAttributes
        False,          # bInheritHandles
        0,              # dwCreationFlags
        None,           # lpEnvironment
        cwd,            # lpCurrentDirectory
        ctypes.byref(si),
        ctypes.byref(pi)
    )
    
    if result:
        print(f"[Desktop] Started on '{DESKTOP_NAME}' (PID: {pi.dwProcessId})")
        # Close handles that are not needed to prevent resource leaks
        kernel32.CloseHandle(pi.hProcess)
        kernel32.CloseHandle(pi.hThread)
        return pi.dwProcessId
    else:
        err = ctypes.GetLastError()
        print(f"[Desktop] CreateProcess failed: error {err}")
        return None


def start():
    """Launch game + bot on the hidden desktop."""
    if os.path.exists(LOCK_FILE):
        print("[!] Desktop session already running. Use --stop first.")
        return
    
    print("=" * 50)
    print(" MapleBot Desktop Launcher")
    print("=" * 50)
    
    # 1. Create the desktop
    hDesk = create_desktop()
    if not hDesk:
        return
    
    # 2. Start MapleStory on the hidden desktop
    maple_dir = os.path.dirname(MAPLE_EXE)
    print(f"[Desktop] Starting MapleStory on '{DESKTOP_NAME}'...")
    game_pid = start_on_desktop(MAPLE_EXE, cwd=maple_dir)
    if not game_pid:
        print("[!] Failed to start MapleStory!")
        return
    
    # 3. Wait for game to initialize
    print("[Desktop] Waiting 15 seconds for game to load...")
    time.sleep(15)
    
    # 4. Start the bot on the same desktop
    print(f"[Desktop] Starting bot on '{DESKTOP_NAME}'...")
    bot_pid = start_on_desktop(PYTHON_EXE, f'"{BOT_SCRIPT}"', cwd=BOT_DIR)
    if not bot_pid:
        print("[!] Failed to start bot!")
        return
    
    # 5. Save PIDs to lock file
    with open(LOCK_FILE, "w") as f:
        f.write(f"{game_pid}\n{bot_pid}\n")
    
    print()
    print("=" * 50)
    print(" Game + Bot running on hidden desktop!")
    print(f" Game PID: {game_pid}")
    print(f" Bot PID:  {bot_pid}")
    print()
    print(" Commands:")
    print("   python desktop_launcher.py --peek   (view game)")
    print("   python desktop_launcher.py --stop   (stop everything)")
    print("=" * 50)


def peek():
    """Briefly switch to the game desktop so the user can see it."""
    hDesk = open_desktop()
    if not hDesk:
        print("[!] MapleDesktop not found. Is the game running?")
        return
    
    hDefault = get_default_desktop()
    
    print("[Desktop] Switching to game desktop... (press Ctrl+C to come back)")
    switch_desktop(hDesk)
    
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    
    print("[Desktop] Switching back to your desktop...")
    switch_desktop(hDefault)
    user32.CloseDesktop(hDesk)
    user32.CloseDesktop(hDefault)


def stop():
    """Kill all processes on the game desktop and clean up."""
    if not os.path.exists(LOCK_FILE):
        print("[!] No active desktop session found.")
        return
    
    with open(LOCK_FILE) as f:
        pids = [int(line.strip()) for line in f.readlines() if line.strip()]
    
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"[Desktop] Killed PID {pid}")
        except (ProcessLookupError, OSError):
            print(f"[Desktop] PID {pid} already dead")
    
    os.remove(LOCK_FILE)
    
    # Close the desktop
    hDesk = open_desktop()
    if hDesk:
        user32.CloseDesktop(hDesk)
    
    print("[Desktop] All cleaned up!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--peek":
            peek()
        elif sys.argv[1] == "--stop":
            stop()
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: desktop_launcher.py [--peek|--stop]")
    else:
        start()

"""
MapleBot - Window Manager
Finds the MapleStory window, pins it to a fixed position, 
and provides the HWND for capture and input modules.
"""

import ctypes
import ctypes.wintypes
import time
import yaml
import win32gui
import win32con
import win32api


class WindowManager:
    """Manages the MapleStory game window — find, position, and track."""

    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        self.title_search = cfg["window"]["title"]
        self.target_x = cfg["window"]["x"]
        self.target_y = cfg["window"]["y"]
        self.target_w = cfg["window"]["width"]
        self.target_h = cfg["window"]["height"]
        self.hwnd = None

    def find_window(self):
        """Find the MapleStory window by title (partial match)."""
        result = []

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.title_search.lower() in title.lower():
                    result.append((hwnd, title))

        win32gui.EnumWindows(enum_callback, None)

        if not result:
            print(f"[WindowManager] Window with '{self.title_search}' not found!")
            return None

        self.hwnd = result[0][0]
        title = result[0][1]
        print(f"[WindowManager] Found: '{title}' (HWND: {self.hwnd})")
        return self.hwnd

    def get_window_rect(self):
        """Get current window position and size."""
        if not self.hwnd:
            return None
        rect = win32gui.GetWindowRect(self.hwnd)
        return {
            "x": rect[0],
            "y": rect[1],
            "width": rect[2] - rect[0],
            "height": rect[3] - rect[1],
        }

    def get_client_rect(self):
        """Get the client area (game content) size, excluding title bar and borders."""
        if not self.hwnd:
            return None
        rect = win32gui.GetClientRect(self.hwnd)
        # Convert client coords to screen coords
        point = win32gui.ClientToScreen(self.hwnd, (0, 0))
        return {
            "x": point[0],
            "y": point[1],
            "width": rect[2],
            "height": rect[3],
        }

    def position_window(self):
        """Move the MapleStory window to the fixed target position."""
        if not self.hwnd:
            self.find_window()
        if not self.hwnd:
            return False

        # Get current window rect to preserve the full window size (with borders/titlebar)
        current = self.get_window_rect()
        if not current:
            return False

        # Move window to target position, keep its current full size
        win32gui.SetWindowPos(
            self.hwnd,
            win32con.HWND_NOTOPMOST,
            self.target_x,
            self.target_y,
            current["width"],
            current["height"],
            win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER,
        )

        # Verify
        new_rect = self.get_window_rect()
        client = self.get_client_rect()
        print(f"[WindowManager] Positioned at ({new_rect['x']}, {new_rect['y']})")
        print(f"[WindowManager] Window size: {new_rect['width']}x{new_rect['height']}")
        print(f"[WindowManager] Client area: {client['width']}x{client['height']} at ({client['x']}, {client['y']})")
        return True

    def keep_position(self, check_interval=5.0):
        """Continuously monitor and re-pin the window if it moves."""
        print(f"[WindowManager] Keeping window pinned at ({self.target_x}, {self.target_y})")
        print("[WindowManager] Press Ctrl+C to stop")
        try:
            while True:
                if not win32gui.IsWindow(self.hwnd):
                    print("[WindowManager] Window lost! Searching again...")
                    self.find_window()
                    if self.hwnd:
                        self.position_window()

                current = self.get_window_rect()
                if current and (
                    current["x"] != self.target_x or current["y"] != self.target_y
                ):
                    print(f"[WindowManager] Window moved to ({current['x']}, {current['y']}), repositioning...")
                    self.position_window()

                time.sleep(check_interval)
        except KeyboardInterrupt:
            print("\n[WindowManager] Stopped.")

    def is_valid(self):
        """Check if the stored HWND is still valid."""
        if not self.hwnd:
            return False
        return win32gui.IsWindow(self.hwnd)


# ========================================
# Standalone test
# ========================================
if __name__ == "__main__":
    import sys

    wm = WindowManager()
    hwnd = wm.find_window()

    if not hwnd:
        print("\nMake sure MapleRoyals is running in windowed mode!")
        sys.exit(1)

    print(f"\nCurrent position: {wm.get_window_rect()}")
    print(f"Client area: {wm.get_client_rect()}")

    print(f"\nMoving to fixed position ({wm.target_x}, {wm.target_y})...")
    wm.position_window()

    if "--keep" in sys.argv:
        wm.keep_position()
    else:
        print("\nDone! Run with --keep to continuously re-pin the window.")

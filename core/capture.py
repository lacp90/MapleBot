"""
MapleBot - Background Screen Capture
Captures the MapleStory window content even when behind other windows
using Win32 PrintWindow API.
"""

import ctypes
import ctypes.wintypes
import numpy as np
import win32gui
import win32ui
import win32con
from PIL import Image


def capture_window(hwnd, client_only=True):
    """
    Capture a window's content as a numpy array (BGR format for OpenCV).
    Works even when the window is behind other windows.
    
    Args:
        hwnd: Window handle
        client_only: If True, captures only the client area (game content).
                     If False, captures the full window including title bar.
    
    Returns:
        numpy array in BGR format (OpenCV compatible), or None on failure.
    """
    try:
        if client_only:
            # Get client area dimensions
            client_rect = win32gui.GetClientRect(hwnd)
            width = client_rect[2]
            height = client_rect[3]
        else:
            # Get full window dimensions
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

        if width <= 0 or height <= 0:
            return None

        # Create device contexts
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        # Create bitmap
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)

        # Use PrintWindow to capture (works even when occluded)
        # PW_CLIENTONLY = 1 captures just the client area
        # PW_RENDERFULLCONTENT = 2 for DWM rendering (Windows 8.1+)
        flags = 0
        if client_only:
            flags |= 1  # PW_CLIENTONLY
        flags |= 2  # PW_RENDERFULLCONTENT

        ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), flags)

        # Convert to numpy array
        bmp_info = bitmap.GetInfo()
        bmp_data = bitmap.GetBitmapBits(True)
        img_array = np.frombuffer(bmp_data, dtype=np.uint8)
        img_array = img_array.reshape((bmp_info["bmHeight"], bmp_info["bmWidth"], 4))

        # Convert BGRA to BGR (drop alpha channel)
        img_bgr = img_array[:, :, :3]

        # Cleanup
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)
        win32gui.DeleteObject(bitmap.GetHandle())

        return img_bgr.copy()

    except Exception as e:
        print(f"[Capture] Error: {e}")
        return None


def capture_region(hwnd, x, y, w, h):
    """
    Capture a specific region of the game window.
    Useful for reading specific UI elements (HP bar, minimap, etc.)
    
    Args:
        hwnd: Window handle
        x, y: Top-left corner of the region (relative to client area)
        w, h: Width and height of the region
    
    Returns:
        numpy array in BGR format, or None on failure.
    """
    full_frame = capture_window(hwnd, client_only=True)
    if full_frame is None:
        return None
    
    # Clamp to valid bounds
    max_h, max_w = full_frame.shape[:2]
    x = max(0, min(x, max_w))
    y = max(0, min(y, max_h))
    w = min(w, max_w - x)
    h = min(h, max_h - y)
    
    return full_frame[y : y + h, x : x + w].copy()


def save_screenshot(img_array, path="screenshot.png"):
    """Save a captured frame as PNG."""
    if img_array is None:
        print("[Capture] No image to save!")
        return False
    
    # Convert BGR to RGB for PIL
    img_rgb = img_array[:, :, ::-1]
    img = Image.fromarray(img_rgb)
    img.save(path)
    print(f"[Capture] Screenshot saved: {path}")
    return True


# ========================================
# Standalone test
# ========================================
if __name__ == "__main__":
    import os
    from window import WindowManager

    wm = WindowManager()
    hwnd = wm.find_window()

    if not hwnd:
        print("MapleRoyals not found! Make sure it's running.")
        exit(1)

    # Position the window first
    wm.position_window()

    # Take a full screenshot
    print("\nCapturing game window (background capture)...")
    frame = capture_window(hwnd)

    if frame is not None:
        print(f"Frame shape: {frame.shape} (h, w, channels)")
        os.makedirs("debug_frames", exist_ok=True)
        save_screenshot(frame, "debug_frames/test_capture.png")
        print("\nCheck debug_frames/test_capture.png to verify!")
    else:
        print("Capture failed!")

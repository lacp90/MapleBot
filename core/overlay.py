"""
MapleBot - Transparent Game Overlay
Draws detection results on top of the game window in real-time.
Uses Win32 layered window with GDI+ for transparency.

Features:
- Transparent, click-through, always-on-top
- Color-coded bounding boxes for each object type
- Character position + FPS counter
- 10-15 FPS update rate
"""
import ctypes
import ctypes.wintypes
import time
import threading
import numpy as np
import cv2
import win32gui
import win32con
import win32api
from dataclasses import dataclass
from typing import List, Optional

# Win32 constants
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x8
WS_EX_TOOLWINDOW = 0x80
WS_POPUP = 0x80000000
GWL_EXSTYLE = -20
LWA_COLORKEY = 0x1
LWA_ALPHA = 0x2
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
ULW_ALPHA = 0x02
BI_RGB = 0
DIB_RGB_COLORS = 0

# GDI functions
gdi32 = ctypes.windll.gdi32
user32 = ctypes.windll.user32


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', ctypes.wintypes.DWORD),
        ('biWidth', ctypes.wintypes.LONG),
        ('biHeight', ctypes.wintypes.LONG),
        ('biPlanes', ctypes.wintypes.WORD),
        ('biBitCount', ctypes.wintypes.WORD),
        ('biCompression', ctypes.wintypes.DWORD),
        ('biSizeImage', ctypes.wintypes.DWORD),
        ('biXPelsPerMeter', ctypes.wintypes.LONG),
        ('biYPelsPerMeter', ctypes.wintypes.LONG),
        ('biClrUsed', ctypes.wintypes.DWORD),
        ('biClrImportant', ctypes.wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
    ]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ('BlendOp', ctypes.c_byte),
        ('BlendFlags', ctypes.c_byte),
        ('SourceConstantAlpha', ctypes.c_byte),
        ('AlphaFormat', ctypes.c_byte),
    ]


class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [('cx', ctypes.c_long), ('cy', ctypes.c_long)]


class Overlay:
    """Transparent overlay window that draws detection results."""

    # Colors (BGRA format for the DIB)
    COLORS = {
        "monster":   (0, 0, 255, 200),       # Red
        "item":      (0, 255, 255, 200),      # Yellow
        "rope":      (0, 140, 255, 180),      # Orange
        "portal":    (255, 200, 50, 200),     # Cyan
        "player":    (0, 255, 0, 180),        # Green
        "character": (0, 255, 0, 220),        # Green (brighter)
    }

    def __init__(self, game_hwnd):
        self.game_hwnd = game_hwnd
        self.overlay_hwnd = None
        self.running = False
        self._width = 0
        self._height = 0
        self._screen_x = 0
        self._screen_y = 0
        self._fps = 0
        self._frame_times = []

    def create(self):
        """Create the transparent overlay window."""
        # Get game client area position
        rect = win32gui.GetClientRect(self.game_hwnd)
        self._width = rect[2]
        self._height = rect[3]

        # Get screen position of client area
        pt = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(self.game_hwnd, ctypes.byref(pt))
        self._screen_x = pt.x
        self._screen_y = pt.y

        # Register window class
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = win32gui.DefWindowProc
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "MapleBotOverlay"
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)

        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass  # Already registered

        # Create layered window
        ex_style = (WS_EX_LAYERED | WS_EX_TRANSPARENT |
                    WS_EX_TOPMOST | WS_EX_TOOLWINDOW)

        self.overlay_hwnd = win32gui.CreateWindowEx(
            ex_style,
            "MapleBotOverlay",
            "MapleBot Overlay",
            WS_POPUP,
            self._screen_x, self._screen_y,
            self._width, self._height,
            0, 0, wc.hInstance, None
        )

        # Show the window
        win32gui.ShowWindow(self.overlay_hwnd, win32con.SW_SHOWNOACTIVATE)
        self.running = True
        print(f"[Overlay] Created at ({self._screen_x},{self._screen_y}) {self._width}x{self._height}")

    def update(self, detections, character=None, extra_text=""):
        """Update the overlay with new detection data."""
        if not self.overlay_hwnd or not self.running:
            return

        # Track FPS
        now = time.time()
        self._frame_times.append(now)
        self._frame_times = [t for t in self._frame_times if now - t < 1.0]
        self._fps = len(self._frame_times)

        # Update position (in case game window moved)
        pt = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(self.game_hwnd, ctypes.byref(pt))
        if pt.x != self._screen_x or pt.y != self._screen_y:
            self._screen_x = pt.x
            self._screen_y = pt.y

        # Create BGRA image
        canvas = np.zeros((self._height, self._width, 4), dtype=np.uint8)

        # Draw detections
        for d in detections:
            color = self.COLORS.get(d.type, (255, 255, 255, 180))
            b, g, r, a = color

            # Bounding box (2px border)
            cv2.rectangle(canvas, (d.x, d.y), (d.x + d.w, d.y + d.h),
                          (b, g, r, a), 2)

            # Semi-transparent fill
            roi = canvas[d.y:d.y + d.h, d.x:d.x + d.w]
            if roi.size > 0:
                fill = np.zeros_like(roi)
                fill[:, :] = (b, g, r, 30)  # Very light fill
                canvas[d.y:d.y + d.h, d.x:d.x + d.w] = cv2.add(roi, fill)

            # Label
            label = f"{d.label}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
            # Background for text
            lx, ly = d.x, d.y - 14
            if ly < 0:
                ly = d.y + d.h + 2
            cv2.rectangle(canvas, (lx, ly), (lx + tw + 4, ly + th + 4),
                          (0, 0, 0, 160), -1)
            cv2.putText(canvas, label, (lx + 2, ly + th + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (b, g, r, 255), 1)

        # Draw character
        if character:
            cx, cy = character.center_x, character.center_y
            # Crosshair
            cv2.line(canvas, (cx - 15, cy), (cx + 15, cy), (0, 255, 0, 200), 1)
            cv2.line(canvas, (cx, cy - 15), (cx, cy + 15), (0, 255, 0, 200), 1)
            cv2.circle(canvas, (cx, cy), 8, (0, 255, 0, 200), 1)

        # HUD: FPS + counts
        counts = {}
        for d in detections:
            counts[d.type] = counts.get(d.type, 0) + 1

        hud_lines = [
            f"FPS: {self._fps}",
            f"Mobs: {counts.get('monster', 0)}",
        ]
        if counts.get('item', 0) > 0:
            hud_lines.append(f"Items: {counts['item']}")
        if character:
            hud_lines.append(f"Pos: ({character.center_x},{character.center_y})")
        if extra_text:
            hud_lines.append(extra_text)

        # Draw HUD (bottom right)
        hud_x = self._width - 130
        hud_y = 10
        # Background
        cv2.rectangle(canvas, (hud_x - 5, hud_y - 5),
                      (self._width - 5, hud_y + len(hud_lines) * 18 + 5),
                      (0, 0, 0, 140), -1)
        for i, line in enumerate(hud_lines):
            cv2.putText(canvas, line, (hud_x, hud_y + (i + 1) * 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255, 220), 1)

        # Push canvas to overlay window using UpdateLayeredWindow
        self._draw_to_window(canvas)

    def _draw_to_window(self, bgra_image):
        """Render a BGRA numpy array to the layered window."""
        h, w = bgra_image.shape[:2]

        # Premultiply alpha (required for UpdateLayeredWindow)
        alpha = bgra_image[:, :, 3:4].astype(np.float32) / 255.0
        bgra_image[:, :, :3] = (bgra_image[:, :, :3].astype(np.float32) * alpha).astype(np.uint8)

        # Flip vertically (DIB is bottom-up)
        bgra_image = np.flip(bgra_image, axis=0).copy()

        # Create DIB section
        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = h  # Positive = bottom-up
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(
            hdc_mem, ctypes.byref(bmi), DIB_RGB_COLORS,
            ctypes.byref(bits), None, 0
        )

        if not hbmp:
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)
            return

        old_bmp = gdi32.SelectObject(hdc_mem, hbmp)

        # Copy pixel data
        ctypes.memmove(bits, bgra_image.ctypes.data, bgra_image.nbytes)

        # UpdateLayeredWindow
        pt_src = POINT(0, 0)
        pt_dst = POINT(self._screen_x, self._screen_y)
        sz = SIZE(w, h)
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

        user32.UpdateLayeredWindow(
            self.overlay_hwnd, hdc_screen, ctypes.byref(pt_dst),
            ctypes.byref(sz), hdc_mem, ctypes.byref(pt_src),
            0, ctypes.byref(blend), ULW_ALPHA
        )

        # Cleanup
        gdi32.SelectObject(hdc_mem, old_bmp)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

    def destroy(self):
        """Remove the overlay window."""
        self.running = False
        if self.overlay_hwnd:
            win32gui.DestroyWindow(self.overlay_hwnd)
            self.overlay_hwnd = None
            print("[Overlay] Destroyed.")


# ============================================================
# Main loop — run as standalone overlay
# ============================================================
def run_overlay(target_fps=12):
    """Run the overlay + detector in a loop."""
    import sys
    sys.path.insert(0, ".")
    from core.window import WindowManager
    from core.capture import capture_window
    from core.detector import Detector

    wm = WindowManager()
    hwnd = wm.find_window()
    if not hwnd:
        print("Game not found!")
        return

    det = Detector()
    overlay = Overlay(hwnd)
    overlay.create()

    print("[Overlay] Running! Press Ctrl+C to stop.")
    frame_interval = 1.0 / target_fps

    try:
        while overlay.running:
            t0 = time.time()

            # Capture
            frame = capture_window(hwnd)
            if frame is None:
                time.sleep(0.1)
                continue

            # Detect
            detections = det.detect(frame)
            character = det.find_character(frame)

            # Draw
            overlay.update(detections, character)

            # Also save debug frame periodically
            if det.frame_count % 120 == 1:
                vis = det.draw_detections(frame, detections, character)
                cv2.imwrite("debug_frames/overlay_latest.png", vis)

            # Pump windows messages
            win32gui.PumpWaitingMessages()

            # Frame timing
            elapsed = time.time() - t0
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[Overlay] Stopping...")
    finally:
        overlay.destroy()
        print("[Overlay] Done!")


if __name__ == "__main__":
    run_overlay()

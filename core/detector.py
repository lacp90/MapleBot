"""
MapleBot - Object Detector
Detects monsters, items, ropes, portals, and players in game frames
using color-based detection with OpenCV.
"""
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Detection:
    """A detected game object."""
    type: str          # "monster", "item", "rope", "portal", "player", "npc"
    x: int             # Bounding box top-left X
    y: int             # Bounding box top-left Y
    w: int             # Width
    h: int             # Height
    confidence: float  # 0.0 - 1.0
    label: str = ""    # Display label
    center_x: int = 0
    center_y: int = 0

    def __post_init__(self):
        self.center_x = self.x + self.w // 2
        self.center_y = self.y + self.h // 2


# ============================================================
# Color ranges (HSV) — calibrated for Kerning City Subway
# ============================================================

# Bubblings: bright blue water drops
BUBBLING_LOWER = np.array([90, 60, 120])
BUBBLING_UPPER = np.array([125, 255, 255])
BUBBLING_MIN_AREA = 300    # Minimum blob area in pixels
BUBBLING_MAX_AREA = 5000   # Max blob area (filter out minimap)

# Items / Mesos: yellow-gold glowing objects
ITEM_LOWER = np.array([20, 120, 180])
ITEM_UPPER = np.array([35, 255, 255])
ITEM_MIN_AREA = 40
ITEM_MAX_AREA = 800

# Ropes / Ladders: brown vertical elements
ROPE_LOWER = np.array([8, 40, 50])
ROPE_UPPER = np.array([25, 180, 180])
ROPE_MIN_AREA = 200
ROPE_MIN_ASPECT = 1.2      # Must be taller than wide

# Portals: white-blue glow
PORTAL_LOWER = np.array([90, 30, 200])
PORTAL_UPPER = np.array([130, 120, 255])
PORTAL_MIN_AREA = 300
PORTAL_MIN_ASPECT = 1.5

# Player name tags: white text on dark background
# (detected differently — via text-like horizontal white blobs below sprites)

# ============================================================
# Exclusion zones (UI elements to ignore)
# ============================================================

# Minimap region (top-left corner)
MINIMAP_RECT = (0, 0, 280, 180)

# Bottom UI bar (HP/MP/EXP bars, buttons)
BOTTOM_UI_HEIGHT = 50   # pixels from bottom

# Quest helper (top-right)
QUEST_RECT = (600, 0, 820, 50)


class Detector:
    """Detects game objects in captured frames."""

    def __init__(self):
        self.last_detections = []
        self.frame_count = 0
        self._morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run all detectors on a frame. Returns list of Detection objects."""
        if frame is None:
            return []

        self.frame_count += 1
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        detections = []
        detections.extend(self._detect_monsters(hsv, h, w))
        detections.extend(self._detect_items(hsv, h, w))
        detections.extend(self._detect_ropes(hsv, h, w))
        detections.extend(self._detect_portals(hsv, h, w))

        self.last_detections = detections
        return detections

    def _in_exclusion_zone(self, x, y, w_box, h_box, frame_h, frame_w):
        """Check if a detection is in a UI exclusion zone."""
        cx, cy = x + w_box // 2, y + h_box // 2

        # Minimap
        mx, my, mw, mh = MINIMAP_RECT
        if mx <= cx <= mw and my <= cy <= mh:
            return True

        # Bottom UI
        if cy > frame_h - BOTTOM_UI_HEIGHT:
            return True

        # Quest helper
        qx, qy, qw, qh = QUEST_RECT
        if qx <= cx <= qw and qy <= cy <= qh:
            return True

        return False

    def _detect_blobs(self, hsv, lower, upper, min_area, max_area,
                      frame_h, frame_w, morph=True):
        """Generic color blob detection."""
        mask = cv2.inRange(hsv, lower, upper)
        if morph:
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._morph_kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._morph_kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        results = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            if self._in_exclusion_zone(x, y, w, h, frame_h, frame_w):
                continue
            results.append((x, y, w, h, area))

        return results

    # ----------------------------------------------------------
    # Monster Detection
    # ----------------------------------------------------------
    def _detect_monsters(self, hsv, h, w) -> List[Detection]:
        blobs = self._detect_blobs(hsv, BUBBLING_LOWER, BUBBLING_UPPER,
                                   BUBBLING_MIN_AREA, BUBBLING_MAX_AREA, h, w)
        detections = []
        for x, y, bw, bh, area in blobs:
            conf = min(1.0, area / 1000)  # Larger = more confident
            detections.append(Detection(
                type="monster", x=x, y=y, w=bw, h=bh,
                confidence=conf, label="Bubbling"
            ))
        return detections

    # ----------------------------------------------------------
    # Item Detection
    # ----------------------------------------------------------
    def _detect_items(self, hsv, h, w) -> List[Detection]:
        blobs = self._detect_blobs(hsv, ITEM_LOWER, ITEM_UPPER,
                                   ITEM_MIN_AREA, ITEM_MAX_AREA, h, w)
        detections = []
        for x, y, bw, bh, area in blobs:
            # Items are small and near the bottom of platforms
            label = "Meso" if bw < 15 and bh < 15 else "Item"
            detections.append(Detection(
                type="item", x=x, y=y, w=bw, h=bh,
                confidence=0.6, label=label
            ))
        return detections

    # ----------------------------------------------------------
    # Rope / Ladder Detection
    # ----------------------------------------------------------
    def _detect_ropes(self, hsv, h, w) -> List[Detection]:
        blobs = self._detect_blobs(hsv, ROPE_LOWER, ROPE_UPPER,
                                   ROPE_MIN_AREA, 50000, h, w, morph=False)
        detections = []
        for x, y, bw, bh, area in blobs:
            aspect = bh / max(bw, 1)
            if aspect < ROPE_MIN_ASPECT:
                continue
            label = "Ladder" if bw > 20 else "Rope"
            detections.append(Detection(
                type="rope", x=x, y=y, w=bw, h=bh,
                confidence=min(1.0, aspect / 3), label=label
            ))
        return detections

    # ----------------------------------------------------------
    # Portal Detection
    # ----------------------------------------------------------
    def _detect_portals(self, hsv, h, w) -> List[Detection]:
        blobs = self._detect_blobs(hsv, PORTAL_LOWER, PORTAL_UPPER,
                                   PORTAL_MIN_AREA, 10000, h, w)
        detections = []
        for x, y, bw, bh, area in blobs:
            aspect = bh / max(bw, 1)
            if aspect < PORTAL_MIN_ASPECT:
                continue
            detections.append(Detection(
                type="portal", x=x, y=y, w=bw, h=bh,
                confidence=0.7, label="Portal"
            ))
        return detections

    # ----------------------------------------------------------
    # Character Position
    # ----------------------------------------------------------
    def find_character(self, frame: np.ndarray) -> Optional[Detection]:
        """Find the player character by looking for the name tag.
        MapleStory displays character name in white text below the sprite.
        """
        if frame is None:
            return None
        # The character name 'Thunderius' appears as white text
        # We look for a dense horizontal white region
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]

        # Threshold for white text
        _, white_mask = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)

        # Look for horizontal clusters of white pixels (name tag)
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))
        name_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel_h)

        contours, _ = cv2.findContours(name_mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        best = None
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            # Name tags are typically 40-100px wide, 8-15px tall
            if 30 < cw < 120 and 5 < ch < 20:
                # Must be in the game area (not UI)
                if y > 50 and y < h - 60:
                    # Character sprite is ABOVE the name tag
                    char_x = x + cw // 2
                    char_y = y - 30  # Approximate sprite center
                    if best is None or y > best.y:  # Pick lowest valid one
                        best = Detection(
                            type="character", x=char_x - 20, y=char_y - 30,
                            w=40, h=60, confidence=0.8, label="Thunderius"
                        )

        return best

    # ----------------------------------------------------------
    # Debug Visualization
    # ----------------------------------------------------------
    def draw_detections(self, frame: np.ndarray,
                        detections: List[Detection],
                        char: Optional[Detection] = None) -> np.ndarray:
        """Draw bounding boxes on a frame for debugging."""
        vis = frame.copy()
        colors = {
            "monster": (0, 0, 255),     # Red
            "item": (0, 255, 255),      # Yellow
            "rope": (0, 128, 255),      # Orange
            "portal": (255, 200, 0),    # Cyan-blue
            "player": (0, 255, 0),      # Green
            "character": (0, 255, 0),   # Green
        }

        for d in detections:
            color = colors.get(d.type, (255, 255, 255))
            cv2.rectangle(vis, (d.x, d.y), (d.x + d.w, d.y + d.h), color, 2)
            label = f"{d.label} ({d.confidence:.0%})"
            cv2.putText(vis, label, (d.x, d.y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        if char:
            cv2.rectangle(vis, (char.x, char.y),
                          (char.x + char.w, char.y + char.h), (0, 255, 0), 2)
            cv2.putText(vis, f"YOU ({char.center_x},{char.center_y})",
                        (char.x, char.y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        # Stats
        counts = {}
        for d in detections:
            counts[d.type] = counts.get(d.type, 0) + 1
        stats = " | ".join(f"{k}:{v}" for k, v in counts.items())
        cv2.putText(vis, stats, (5, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return vis


# ============================================================
# Quick test
# ============================================================
if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, ".")
    from core.window import WindowManager
    from core.capture import capture_window

    wm = WindowManager()
    hwnd = wm.find_window()
    if not hwnd:
        print("Game not found!")
        exit(1)

    frame = capture_window(hwnd)
    if frame is None:
        print("Capture failed!")
        exit(1)

    det = Detector()
    detections = det.detect(frame)
    char = det.find_character(frame)

    print(f"\nDetections: {len(detections)}")
    for d in detections:
        print(f"  [{d.type}] {d.label} at ({d.center_x},{d.center_y}) {d.w}x{d.h}")
    if char:
        print(f"  [character] {char.label} at ({char.center_x},{char.center_y})")

    vis = det.draw_detections(frame, detections, char)
    os.makedirs("debug_frames", exist_ok=True)
    cv2.imwrite("debug_frames/detections.png", vis)
    print("\nSaved debug_frames/detections.png")

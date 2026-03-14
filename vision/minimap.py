"""
MapleBot - Minimap Reader
Reads the character's position from the minimap overlay.
The minimap shows:
  - Map layout (dark background with terrain shapes)
  - Character dot (green/white marker)
  - Other player dots (sometimes different colors)
  
Returns the character's relative position within the map as (x%, y%).
This is used for:
  - Knowing where on the map the character is
  - Detecting if stuck (position not changing)
  - Pathing back to grinding spot
"""

import cv2
import numpy as np


# Minimap region in the game window (top-left area)
# The actual map image is inside the minimap panel
MINIMAP_PANEL = {
    "x": 7,       # Left edge of minimap panel
    "y": 55,      # Top of the map image (below title bar)
    "w": 170,     # Width of map area
    "h": 115,     # Height of map area
}

# Character dot color ranges (BGR format)
# The character marker in MapleRoyals minimap is typically:
#   - Green dot (standard): RGB(0, 218, 0) → BGR(0, 218, 0)
#   - Yellow dot (party): RGB(255, 255, 0) → BGR(0, 255, 255)
CHAR_DOT_COLORS = {
    "green": {
        "lower": np.array([0, 180, 0]),     # BGR
        "upper": np.array([80, 255, 80]),
    },
    "yellow": {
        "lower": np.array([0, 200, 200]),   # BGR
        "upper": np.array([50, 255, 255]),
    },
    "white": {
        "lower": np.array([230, 230, 230]),
        "upper": np.array([255, 255, 255]),
    },
}


class MinimapReader:
    """Reads character position from the minimap."""

    def __init__(self):
        self._last_pos = None
        self._position_history = []  # Track recent positions
        self._history_max = 20

    def read_position(self, frame):
        """
        Read the character's position from the minimap.
        
        Args:
            frame: Full game window capture (BGR numpy array)
        
        Returns:
            dict with:
                x: horizontal position (0.0 = left, 1.0 = right)
                y: vertical position (0.0 = top, 1.0 = bottom)
                raw_x, raw_y: pixel position within minimap
                found: bool
        """
        # Extract minimap region
        mm = MINIMAP_PANEL
        minimap = frame[mm["y"]:mm["y"]+mm["h"], mm["x"]:mm["x"]+mm["w"]]

        if minimap.size == 0:
            return {"x": -1, "y": -1, "found": False}

        # Try to find character dot by color
        best_pos = None
        best_area = 0

        for color_name, bounds in CHAR_DOT_COLORS.items():
            mask = cv2.inRange(minimap, bounds["lower"], bounds["upper"])
            
            # Find contours of matching color regions
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                # Character dot is small (2-20 pixels area)
                if 2 <= area <= 50:
                    M = cv2.moments(contour)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        if area > best_area:
                            best_pos = (cx, cy, color_name)
                            best_area = area

        if best_pos is None:
            return {"x": -1, "y": -1, "found": False}

        cx, cy, color = best_pos
        
        # Convert to relative position (0.0 - 1.0)
        rel_x = cx / mm["w"]
        rel_y = cy / mm["h"]

        result = {
            "x": round(rel_x, 3),
            "y": round(rel_y, 3),
            "raw_x": cx,
            "raw_y": cy,
            "color": color,
            "found": True,
        }

        # Update history
        self._last_pos = result
        self._position_history.append((rel_x, rel_y))
        if len(self._position_history) > self._history_max:
            self._position_history.pop(0)

        return result

    def is_stuck(self, threshold=0.01, min_samples=5):
        """
        Check if the character hasn't moved based on position history.
        
        Args:
            threshold: Maximum position change to consider "not moving"
            min_samples: Minimum history samples needed
        
        Returns:
            True if character appears stuck
        """
        if len(self._position_history) < min_samples:
            return False

        recent = self._position_history[-min_samples:]
        xs = [p[0] for p in recent]
        ys = [p[1] for p in recent]

        x_range = max(xs) - min(xs)
        y_range = max(ys) - min(ys)

        return x_range < threshold and y_range < threshold

    def get_map_side(self):
        """
        Get which side of the map the character is on.
        Returns: 'left', 'center', or 'right'
        """
        if self._last_pos is None or not self._last_pos.get("found"):
            return "unknown"
        x = self._last_pos["x"]
        if x < 0.35:
            return "left"
        elif x > 0.65:
            return "right"
        return "center"

    def calibrate(self, frame):
        """Save debug images for minimap calibration."""
        mm = MINIMAP_PANEL
        minimap = frame[mm["y"]:mm["y"]+mm["h"], mm["x"]:mm["x"]+mm["w"]]
        
        cv2.imwrite("debug_frames/minimap_region.png", minimap)
        
        # Draw detected dots
        annotated = minimap.copy()
        for color_name, bounds in CHAR_DOT_COLORS.items():
            mask = cv2.inRange(minimap, bounds["lower"], bounds["upper"])
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                area = cv2.contourArea(c)
                if 2 <= area <= 50:
                    M = cv2.moments(c)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), 2)
                        cv2.putText(annotated, color_name, (cx+8, cy), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
        
        cv2.imwrite("debug_frames/minimap_annotated.png", annotated)
        print("[Minimap] Calibration images saved to debug_frames/")
        
        pos = self.read_position(frame)
        if pos["found"]:
            print(f"[Minimap] Character at ({pos['x']:.2f}, {pos['y']:.2f}) — {pos['color']} dot")
        else:
            print("[Minimap] Character dot NOT found — may need color calibration")
        
        return pos


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from core.window import WindowManager
    from core.capture import capture_window

    wm = WindowManager()
    hwnd = wm.find_window()
    if not hwnd:
        print("Game not found!")
        exit(1)
    
    wm.position_window()
    frame = capture_window(hwnd)
    
    reader = MinimapReader()
    pos = reader.calibrate(frame)
    
    if pos["found"]:
        print(f"\nCharacter position: x={pos['x']:.1%} y={pos['y']:.1%}")
        print(f"Map side: {reader.get_map_side()}")
    else:
        print("\nCould not find character dot. Check debug_frames/minimap_annotated.png")

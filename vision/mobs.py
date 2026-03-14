"""
MapleBot - Mob Detector
Detects monsters on screen using color-based analysis and movement detection.
Rather than template matching (which needs pre-captured sprites for every mob),
this uses a combination of:
  1. Motion detection — mobs move, background doesn't
  2. HP bar detection — mobs have small red/yellow HP bars above them
  3. Color anomaly detection — mobs have distinct colors vs background

This approach works on ANY map and ANY mob without needing templates.
"""

import cv2
import numpy as np
import time


# Game area (excluding UI elements)
GAME_AREA = {
    "x": 0,
    "y": 0,
    "w": 1024,
    "h": 650,  # Everything above the status bar
}

# Mob HP bar characteristics
# Mobs in MapleStory have small colored bars above them
MOB_HP_BAR = {
    # Red/orange HP bar colors (BGR)
    "lower": np.array([0, 0, 150]),
    "upper": np.array([80, 80, 255]),
    "min_width": 15,
    "max_width": 80,
    "min_height": 2,
    "max_height": 6,
}

# Name tag colors (mob names appear as yellow/white text)
MOB_NAME = {
    "lower_yellow": np.array([0, 180, 180]),  # BGR
    "upper_yellow": np.array([80, 255, 255]),
}


class MobDetector:
    """
    Detects mobs on screen using motion and HP bar detection.
    No template matching needed — works on any map.
    """

    def __init__(self):
        self._last_frame = None
        self._mob_positions = []  # (x, y, w, h) list
        self._detection_count = 0

    def detect_mobs(self, frame):
        """
        Detect mobs in the current game frame.
        
        Args:
            frame: Full game window capture
        
        Returns:
            list of dicts with: x, y, w, h, confidence, direction
        """
        ga = GAME_AREA
        game_area = frame[ga["y"]:ga["y"]+ga["h"], ga["x"]:ga["x"]+ga["w"]]
        
        mobs = []

        # Method 1: Detect mob HP bars (most reliable)
        hp_mobs = self._detect_hp_bars(game_area)
        mobs.extend(hp_mobs)

        # Method 2: Motion detection (supplement)
        if self._last_frame is not None:
            motion_mobs = self._detect_motion(game_area)
            # Only add motion detections that don't overlap with HP bar detections
            for m in motion_mobs:
                if not self._overlaps(m, mobs):
                    mobs.append(m)

        self._last_frame = game_area.copy()
        self._mob_positions = mobs
        self._detection_count += 1

        return mobs

    def _detect_hp_bars(self, game_area):
        """Detect mobs by their HP bars (red bars above mob heads)."""
        mobs = []
        
        # Look for red HP bar-shaped regions
        hp = MOB_HP_BAR
        mask = cv2.inRange(game_area, hp["lower"], hp["upper"])
        
        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # HP bars are wide and thin
            if (hp["min_width"] <= w <= hp["max_width"] and 
                hp["min_height"] <= h <= hp["max_height"] and
                w / max(h, 1) > 3):  # Width/height ratio > 3
                
                mobs.append({
                    "x": x,
                    "y": y + 20,  # Mob body is below the HP bar
                    "w": w,
                    "h": 40,  # Approximate mob height
                    "confidence": 0.8,
                    "method": "hp_bar",
                })

        return mobs

    def _detect_motion(self, game_area):
        """Detect moving objects (mobs) by frame differencing."""
        mobs = []
        
        if self._last_frame is None:
            return mobs

        # Resize for performance
        small_curr = cv2.resize(game_area, (256, 163))
        small_prev = cv2.resize(self._last_frame, (256, 163))

        # Frame difference
        diff = cv2.absdiff(
            cv2.cvtColor(small_curr, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(small_prev, cv2.COLOR_BGR2GRAY),
        )
        
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Find motion regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        scale_x = GAME_AREA["w"] / 256
        scale_y = GAME_AREA["h"] / 163

        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 5000:  # Filter too small/large
                x, y, w, h = cv2.boundingRect(contour)
                mobs.append({
                    "x": int(x * scale_x),
                    "y": int(y * scale_y),
                    "w": int(w * scale_x),
                    "h": int(h * scale_y),
                    "confidence": 0.4,
                    "method": "motion",
                })

        return mobs

    def _overlaps(self, mob, mob_list, threshold=50):
        """Check if a mob overlaps with any mob in the list."""
        for m in mob_list:
            dx = abs(mob["x"] - m["x"])
            dy = abs(mob["y"] - m["y"])
            if dx < threshold and dy < threshold:
                return True
        return False

    def get_nearest_mob(self, char_x=512):
        """
        Get the nearest mob to the character's position.
        
        Args:
            char_x: Character's x position (default: center of 1024px screen)
        
        Returns:
            dict with mob info, or None
        """
        if not self._mob_positions:
            return None

        nearest = min(self._mob_positions, 
                      key=lambda m: abs(m["x"] + m["w"]/2 - char_x))
        
        # Also determine direction
        mob_center = nearest["x"] + nearest["w"] / 2
        nearest["direction"] = "right" if mob_center > char_x else "left"
        
        return nearest

    def get_mob_count(self):
        """Number of mobs currently detected."""
        return len(self._mob_positions)

    def get_mob_density_side(self, char_x=512):
        """
        Count mobs on each side of the character.
        Returns: (left_count, right_count)
        """
        left = sum(1 for m in self._mob_positions if m["x"] + m["w"]/2 < char_x)
        right = len(self._mob_positions) - left
        return left, right

    def calibrate(self, frame):
        """Save debug images showing detected mobs."""
        mobs = self.detect_mobs(frame)
        
        ga = GAME_AREA
        annotated = frame[ga["y"]:ga["y"]+ga["h"], ga["x"]:ga["x"]+ga["w"]].copy()
        
        for mob in mobs:
            color = (0, 255, 0) if mob["method"] == "hp_bar" else (0, 255, 255)
            cv2.rectangle(annotated, 
                         (mob["x"], mob["y"]), 
                         (mob["x"] + mob["w"], mob["y"] + mob["h"]),
                         color, 2)
            label = f"{mob['method']} ({mob['confidence']:.1f})"
            cv2.putText(annotated, label, (mob["x"], mob["y"] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        cv2.imwrite("debug_frames/mob_detection.png", annotated)
        print(f"[Mobs] Detected {len(mobs)} mobs — saved to debug_frames/mob_detection.png")
        
        for i, m in enumerate(mobs):
            print(f"  Mob {i+1}: ({m['x']},{m['y']}) {m['w']}x{m['h']} "
                  f"[{m['method']}] conf={m['confidence']:.1f}")
        
        return mobs


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
    
    # Take two frames for motion detection
    frame1 = capture_window(hwnd)
    import time
    time.sleep(0.5)
    frame2 = capture_window(hwnd)

    detector = MobDetector()
    detector.detect_mobs(frame1)  # Set baseline
    detector.calibrate(frame2)    # Detect with motion

    nearest = detector.get_nearest_mob()
    if nearest:
        print(f"\nNearest mob: ({nearest['x']},{nearest['y']}) — {nearest['direction']}")
    
    left, right = detector.get_mob_density_side()
    print(f"Mob density: {left} left, {right} right")

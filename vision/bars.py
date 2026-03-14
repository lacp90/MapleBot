"""
MapleBot - HP/MP/EXP Bar Reader
Reads the status bars from the MapleStory UI using pixel color detection.
Works by scanning the bar areas and calculating fill percentage based on colored pixels.

MapleRoyals v62 UI Layout (1024x768 client area):
- HP bar: Red bar at the bottom status panel
- MP bar: Blue/cyan bar next to HP
- EXP bar: Yellow bar next to MP
- Level/Class text: Bottom-left corner

Pixel coordinates verified against live game capture on 2025-03-14.
"""

import numpy as np
import cv2


# ========================================
# Bar Regions (pixel coordinates in client area)
# Calibrated for MapleRoyals 1024x768 resolution
# Format: (x_start, y_start, x_end, y_end)
#
# Verified via debug_frames/bar_measurements.txt:
#   HP bar: red fill at y=752-759, x starts ~245
#   MP bar: blue fill at y=752-758, x starts ~370
#   EXP bar: yellow fill at y=752-758, x starts ~503
#   Gray (empty) portion has R≈47 G≈54 B≈60
# ========================================

BAR_REGIONS = {
    # (x_start, y_start, x_end, y_end) — colored fill area only
    "hp":  (245, 752, 365, 759),   # Red bar — 120px wide
    "mp":  (370, 752, 498, 759),   # Blue/cyan bar — 128px wide
    "exp": (503, 752, 634, 759),   # Yellow bar — 131px wide
}

# Color ranges in BGR format for OpenCV
# These thresholds were measured from actual game pixels:
#   HP red:  R=238-255, G=0-72, B=0-72 (BGR: B=0-72, G=0-72, R=238-255)
#   MP blue: B=222-255, G=85-194, R=0-72 (it's actually cyan-ish)
#   EXP yellow: R=140-212, G=150-228, B=0 (BGR: B=0, G=150-228, R=140-212)
#   Empty/gray: R≈47, G≈54, B≈60
BAR_COLORS = {
    "hp": {
        # Red bar in BGR: low B, low G, high R
        "lower": np.array([0, 0, 160]),
        "upper": np.array([100, 100, 255]),
    },
    "mp": {
        # Blue/Cyan bar in BGR: high B, moderate G, low R
        "lower": np.array([170, 50, 0]),
        "upper": np.array([255, 255, 100]),
    },
    "exp": {
        # Yellow bar in BGR: low B, high G, high R
        "lower": np.array([0, 100, 100]),
        "upper": np.array([50, 255, 255]),
    },
}


def read_bar_percentage(frame, bar_name):
    """
    Read a bar's fill percentage from a game screenshot.
    
    Args:
        frame: Full game screenshot as numpy array (BGR)
        bar_name: "hp", "mp", or "exp"
    
    Returns:
        Float 0-100 representing fill percentage, or -1 if detection failed.
    """
    if bar_name not in BAR_REGIONS:
        return -1

    x1, y1, x2, y2 = BAR_REGIONS[bar_name]
    
    # Safety check
    h, w = frame.shape[:2]
    if x2 > w or y2 > h:
        return -1

    # Extract the bar region
    bar_region = frame[y1:y2, x1:x2]

    if bar_region.size == 0:
        return -1

    # Create mask for the bar's color
    color_range = BAR_COLORS[bar_name]
    mask = cv2.inRange(bar_region, color_range["lower"], color_range["upper"])

    # Count colored pixels per column to find where the fill ends
    bar_width = x2 - x1
    col_counts = np.sum(mask > 0, axis=0)  # Count colored pixels per column
    bar_height = y2 - y1

    # A column is "filled" if at least 30% of its height has the bar color
    threshold = bar_height * 0.3
    filled_columns = np.sum(col_counts >= threshold)

    percentage = (filled_columns / bar_width) * 100
    return round(percentage, 1)


def read_all_bars(frame):
    """
    Read HP, MP, and EXP percentages from a game screenshot.
    
    Args:
        frame: Full game screenshot (BGR numpy array)
    
    Returns:
        Dict with hp, mp, exp percentages
    """
    return {
        "hp": read_bar_percentage(frame, "hp"),
        "mp": read_bar_percentage(frame, "mp"),
        "exp": read_bar_percentage(frame, "exp"),
    }


def read_bar_values_ocr(frame):
    """
    Read the numeric HP/MP values from the UI text.
    e.g., "HP [65/65]" -> (65, 65)
    
    Uses simple template matching or color-based text detection.
    This is a backup method — percentage-based reading is faster.
    
    For now, returns None (will implement with OCR or template matching later).
    """
    # TODO: Implement OCR-based reading for exact values
    return None


def calibrate_bars(frame, output_dir="debug_frames"):
    """
    Debug helper: saves bar regions as separate images for calibration.
    Run this to verify that the bar coordinates are correct.
    
    Args:
        frame: Full game screenshot
        output_dir: Where to save debug images
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    h, w = frame.shape[:2]
    print(f"[Bars] Frame size: {w}x{h}")

    for name, (x1, y1, x2, y2) in BAR_REGIONS.items():
        if x2 > w or y2 > h:
            print(f"[Bars] {name}: Region out of bounds! ({x1},{y1})-({x2},{y2}) vs frame {w}x{h}")
            continue

        region = frame[y1:y2, x1:x2]
        path = os.path.join(output_dir, f"bar_{name}.png")
        cv2.imwrite(path, region)
        
        # Also create a color mask visualization
        color_range = BAR_COLORS[name]
        mask = cv2.inRange(region, color_range["lower"], color_range["upper"])
        mask_path = os.path.join(output_dir, f"bar_{name}_mask.png")
        cv2.imwrite(mask_path, mask)
        
        pct = read_bar_percentage(frame, name)
        print(f"[Bars] {name}: {pct}% — saved to {path} and {mask_path}")

    # Save the full bottom bar area for reference
    bottom = frame[728:, :]
    cv2.imwrite(os.path.join(output_dir, "bottom_bar_full.png"), bottom)
    print(f"[Bars] Full bottom bar saved to {output_dir}/bottom_bar_full.png")

    # Draw rectangles on a copy showing where we're reading
    annotated = frame.copy()
    colors = {"hp": (0, 0, 255), "mp": (255, 0, 0), "exp": (0, 255, 255)}
    for name, (x1, y1, x2, y2) in BAR_REGIONS.items():
        cv2.rectangle(annotated, (x1, y1), (x2, y2), colors[name], 2)
        cv2.putText(annotated, name.upper(), (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[name], 1)
    cv2.imwrite(os.path.join(output_dir, "bar_regions_annotated.png"), annotated)
    print(f"[Bars] Annotated screenshot saved to {output_dir}/bar_regions_annotated.png")


# ========================================
# Standalone test / calibration
# ========================================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from core.window import WindowManager
    from core.capture import capture_window

    wm = WindowManager()
    hwnd = wm.find_window()

    if not hwnd:
        print("MapleRoyals not found!")
        exit(1)

    wm.position_window()

    print("\n=== Bar Reader Calibration ===")
    print("Capturing game window...")
    frame = capture_window(hwnd)

    if frame is None:
        print("Capture failed!")
        exit(1)

    print(f"Frame shape: {frame.shape}")

    # Run calibration (saves debug images)
    calibrate_bars(frame)

    # Read all bars
    print("\n--- Bar Readings ---")
    bars = read_all_bars(frame)
    for name, value in bars.items():
        print(f"  {name.upper()}: {value}%")

    print("\nCheck debug_frames/ folder for calibration images!")
    print("If bars show wrong values, adjust BAR_REGIONS coordinates in vision/bars.py")

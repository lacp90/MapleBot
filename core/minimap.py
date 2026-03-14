"""
MapleBot — Minimap OCR + Map Detection
Reads the map name from the minimap UI element to auto-detect current location.

Uses a two-stage approach:
  1. Perceptual hash matching against known map text signatures (fast, pixel-perfect)
  2. OCR fallback for unknown maps (pytesseract)

The minimap text area is at:
  - Line 1 (region): y=36-52, x=55-225 (e.g. "Kerning City Subway")
  - Line 2 (sub):    y=52-68, x=55-225 (e.g. "Line 1 <Area 1>")
"""
import cv2
import numpy as np
import os
import hashlib
import json
from typing import Optional, Tuple

# Configure Tesseract path (optional, for unknown maps)
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    os.environ["PATH"] += os.pathsep + r"C:\Program Files\Tesseract-OCR"
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    except ImportError:
        pass

# Minimap text coordinates (calibrated from live game capture)
MM_TEXT_Y1 = 36      # Top of first text line
MM_TEXT_Y2 = 68      # Bottom of second text line
MM_TEXT_X1 = 55      # Left (after icon)
MM_TEXT_X2 = 225     # Right

# Path to the hash database
HASH_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "knowledge", "map_hashes.json")


def _extract_text_region(frame):
    """Extract the minimap text region and create a binary signature."""
    if frame is None or frame.shape[0] < MM_TEXT_Y2 or frame.shape[1] < MM_TEXT_X2:
        return None
    roi = frame[MM_TEXT_Y1:MM_TEXT_Y2, MM_TEXT_X1:MM_TEXT_X2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # Threshold to get white text
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    return binary


def _phash(binary_img, size=16):
    """Compute a perceptual hash from a binary image."""
    resized = cv2.resize(binary_img, (size, size), interpolation=cv2.INTER_AREA)
    avg = resized.mean()
    bits = (resized > avg).flatten()
    # Pack into hex string
    h = 0
    for b in bits:
        h = (h << 1) | int(b)
    return format(h, f'0{size*size//4}x')


def _pixel_hash(binary_img):
    """Compute a stable hash from the binary pixel data."""
    # Resize to standard small size for comparison
    small = cv2.resize(binary_img, (64, 16), interpolation=cv2.INTER_AREA)
    _, small_bin = cv2.threshold(small, 128, 255, cv2.THRESH_BINARY)
    return hashlib.md5(small_bin.tobytes()).hexdigest()


def _hamming_distance(h1, h2):
    """Compute hamming distance between two hex hash strings."""
    if len(h1) != len(h2):
        return 999
    i1, i2 = int(h1, 16), int(h2, 16)
    return bin(i1 ^ i2).count('1')


# ============================================================
# Hash Database
# ============================================================

def _load_hash_db():
    """Load the map hash database."""
    if os.path.exists(HASH_DB_PATH):
        with open(HASH_DB_PATH, 'r') as f:
            return json.load(f)
    return {}


def _save_hash_db(db):
    """Save the map hash database."""
    os.makedirs(os.path.dirname(HASH_DB_PATH), exist_ok=True)
    with open(HASH_DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)


def learn_map(frame, map_key, map_name=""):
    """Learn a new map by saving its minimap text hash.
    Call this when you know which map you're on.
    """
    binary = _extract_text_region(frame)
    if binary is None:
        return False

    ph = _phash(binary)
    px = _pixel_hash(binary)

    db = _load_hash_db()
    db[map_key] = {
        "name": map_name or map_key,
        "phash": ph,
        "pixel_hash": px,
    }
    _save_hash_db(db)
    print(f"[Minimap] Learned map: {map_key} ({map_name})")
    return True


def detect_map(frame) -> Tuple[Optional[str], Optional[str], float]:
    """Detect the current map from its minimap text.
    
    Returns: (map_key, map_name, confidence)
    """
    binary = _extract_text_region(frame)
    if binary is None:
        return None, None, 0.0

    current_ph = _phash(binary)
    current_px = _pixel_hash(binary)

    db = _load_hash_db()

    # Try exact pixel hash match first
    for key, data in db.items():
        if data.get("pixel_hash") == current_px:
            return key, data.get("name", key), 1.0

    # Try perceptual hash match (tolerant of small changes)
    best_key = None
    best_name = None
    best_dist = 999

    for key, data in db.items():
        stored_ph = data.get("phash", "")
        dist = _hamming_distance(current_ph, stored_ph)
        if dist < best_dist:
            best_dist = dist
            best_key = key
            best_name = data.get("name", key)

    # Accept if close enough (within 25% of hash bits)
    hash_bits = 16 * 16  # 256 bits in our phash
    if best_dist < hash_bits * 0.25:  # Within 25% different
        conf = max(0.3, 1.0 - (best_dist / hash_bits))
        return best_key, best_name, conf

    return None, None, 0.0


def auto_learn_current_map(frame, map_key, map_name=""):
    """Convenience: detect or learn.
    If map is unknown, learn it. If known, return the match.
    """
    key, name, conf = detect_map(frame)
    if conf >= 0.7:
        return key, name, conf

    # Unknown map — learn it
    learn_map(frame, map_key, map_name)
    return map_key, map_name, 1.0


# ============================================================
# Quick test
# ============================================================
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

    frame = capture_window(hwnd)
    if frame is None:
        print("Capture failed!")
        exit(1)

    # Try detection
    key, name, conf = detect_map(frame)
    print(f"Detected: key={key}, name={name}, confidence={conf:.0%}")

    if conf < 0.5:
        # Learn it as current map
        print("\nMap unknown! Learning as 'kerning_city' (Victoria Road)...")
        learn_map(frame, "kerning_city", "Victoria Road, Kerning City")
        
        # Verify
        key, name, conf = detect_map(frame)
        print(f"After learning: key={key}, name={name}, confidence={conf:.0%}")

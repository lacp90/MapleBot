"""Debug v3: try many OCR strategies to find what works."""
import sys, os, cv2, numpy as np
sys.path.insert(0, ".")
os.environ["PATH"] += os.pathsep + r"C:\Program Files\Tesseract-OCR"
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from core.capture import capture_window
from core.window import WindowManager

wm = WindowManager()
hwnd = wm.find_window()
frame = capture_window(hwnd)
os.makedirs("debug_frames", exist_ok=True)

# Both text lines
roi = frame[36:70, 55:225]

# Strategy 1: High scale + white text extraction
gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

# The text is bright white (~240+) on dark blue (~60)
# Extract just the bright pixels
_, white_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
scaled = cv2.resize(white_mask, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
# Add padding (Tesseract needs whitespace around text)
padded = cv2.copyMakeBorder(scaled, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
# Invert: Tesseract prefers black text on white
inverted = cv2.bitwise_not(padded)
cv2.imwrite("debug_frames/mm_strat1.png", inverted)
text1 = pytesseract.image_to_string(inverted, config="--psm 6").strip()
print("Strategy 1 (white extract 6x invert): " + repr(text1))

# Strategy 2: Same but NEAREST interpolation + morphology
_, white2 = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)
scaled2 = cv2.resize(white2, None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST)
kernel = np.ones((2,2), np.uint8)
dilated = cv2.dilate(scaled2, kernel, iterations=1)
padded2 = cv2.copyMakeBorder(dilated, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
inv2 = cv2.bitwise_not(padded2)
cv2.imwrite("debug_frames/mm_strat2.png", inv2)
text2 = pytesseract.image_to_string(inv2, config="--psm 6").strip()
print("Strategy 2 (dilate + 5x): " + repr(text2))

# Strategy 3: Color-based extraction (white pixels only)
hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
# White text: low saturation, high value
white_low = np.array([0, 0, 200])
white_high = np.array([180, 60, 255])
white3 = cv2.inRange(hsv, white_low, white_high)
scaled3 = cv2.resize(white3, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
padded3 = cv2.copyMakeBorder(scaled3, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=0)
cv2.imwrite("debug_frames/mm_strat3.png", padded3)
text3 = pytesseract.image_to_string(padded3, config="--psm 6").strip()
print("Strategy 3 (HSV white 6x): " + repr(text3))

# Strategy 4: Line by line
for i, (y1, y2) in enumerate([(36, 52), (52, 68)]):
    line = frame[y1:y2, 55:225]
    g = cv2.cvtColor(line, cv2.COLOR_BGR2GRAY)
    _, t = cv2.threshold(g, 200, 255, cv2.THRESH_BINARY)
    s = cv2.resize(t, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
    p = cv2.copyMakeBorder(s, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
    inv = cv2.bitwise_not(p)
    cv2.imwrite("debug_frames/mm_line" + str(i+1) + "_v3.png", inv)
    tx = pytesseract.image_to_string(inv, config="--psm 7").strip()
    print("Line " + str(i+1) + " (psm7): " + repr(tx))

print("\nDone!")

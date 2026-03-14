"""Quick verification: bars + DPI awareness."""
import sys, ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
sys.path.insert(0, ".")

from core.window import WindowManager
from core.capture import capture_window
from vision.bars import read_all_bars

wm = WindowManager()
hwnd = wm.find_window()
wm.position_window()
frame = capture_window(hwnd)
print(f"Frame: {frame.shape}")
bars = read_all_bars(frame)
hp = bars["hp"]
mp = bars["mp"]
exp = bars["exp"]
print(f"HP={hp}%  MP={mp}%  EXP={exp}%")

if hp > 0 and mp > 0:
    print("Bars reading OK - bot is ready!")
else:
    print("WARNING: bars not reading correctly")

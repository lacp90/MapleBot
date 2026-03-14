"""
LIVE TEST: Overlay + Background Movement together.
Runs the overlay detector AND moves the character in background simultaneously.

Usage: C:\Python312-32\python.exe scripts\live_test.py
Then click your IDE — character should walk while overlay shows detections!
"""
import sys, time, threading
sys.path.insert(0, ".")

from core.window import WindowManager
from core.capture import capture_window
from core.detector import Detector
from core.overlay import Overlay
from core.memory_input import MemoryHook

def movement_thread(hook):
    """Walk left/right in a loop using background memory hooks."""
    print("[Movement] Starting in 5 seconds — CLICK YOUR IDE NOW!")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    print("[Movement] Walking! Game should be UNFOCUSED.")
    cycles = 0
    while hook.hooked:
        cycles += 1
        print(f"[Movement] Cycle {cycles}: Walking RIGHT...")
        hook.hold_key("right", 2.5)
        time.sleep(0.3)
        print(f"[Movement] Cycle {cycles}: Walking LEFT...")
        hook.hold_key("left", 2.5)
        time.sleep(0.3)
        if cycles >= 3:
            break
    print("[Movement] Done!")


def main():
    # 1. Find game
    wm = WindowManager()
    hwnd = wm.find_window()
    if not hwnd:
        print("Game not found!")
        return

    # 2. Set up memory hook for background movement
    print("\n=== Setting up background movement ===")
    hook = MemoryHook()
    if not hook.attach():
        print("Failed to attach!")
        return
    if not hook.install():
        print("Failed to install hooks!")
        return

    # 3. Set up overlay
    print("\n=== Setting up overlay ===")
    det = Detector()
    overlay = Overlay(hwnd)
    overlay.create()

    # 4. Start movement in background thread
    move_thread = threading.Thread(target=movement_thread, args=(hook,), daemon=True)
    move_thread.start()

    # 5. Run overlay loop
    print("[Overlay] Running! Press Ctrl+C to stop.\n")
    frame_interval = 1.0 / 12  # 12 FPS

    try:
        while overlay.running:
            t0 = time.time()

            frame = capture_window(hwnd)
            if frame is None:
                time.sleep(0.1)
                continue

            detections = det.detect(frame)
            character = det.find_character(frame)

            # Show status
            status = "Moving" if hook.hooked else "Idle"
            overlay.update(detections, character, extra_text=f"Mode: {status}")

            import win32gui
            win32gui.PumpWaitingMessages()

            elapsed = time.time() - t0
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[Main] Stopping...")
    finally:
        # Clean up
        hook.release_all()
        hook.uninstall()
        overlay.destroy()
        print("[Main] All cleaned up!")


if __name__ == "__main__":
    main()

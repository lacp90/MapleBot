"""
MapleBot - Chat Monitor
Monitors the in-game chat area for incoming messages.
Uses pixel-level change detection to know when new chat appears,
then uses the knowledge base for keyword-based responses.

The chat monitor does NOT use OCR (too slow and unreliable for pixel fonts).
Instead, it takes a template-matching approach:
  1. Detects when new text appears in the chat area
  2. Captures the chat region
  3. Sends to LLM for reading (when available)
  4. Falls back to simple keyword detection

For keyword detection without OCR, we monitor for specific visual patterns
like the ">" symbol that appears in direct messages.
"""

import time
import cv2
import numpy as np


# Chat area coordinates in the game window
# In MapleRoyals, the chat box is at the bottom, above the status bar
CHAT_REGION = {
    "x": 0,
    "y": 670,
    "w": 500,
    "h": 55,
}

# The "All Chat" area where public messages appear
CHAT_TEXT_REGION = {
    "x": 5,
    "y": 672,
    "w": 490,
    "h": 18,  # Single line height
}


class ChatMonitor:
    """
    Monitors the in-game chat for incoming messages.
    Uses frame differencing to detect new messages,
    then optionally uses LLM to read them.
    """

    def __init__(self, ollama_client=None):
        self.llm = ollama_client
        self._last_chat_frame = None
        self._last_change_time = 0
        self._cooldown = 5.0  # Don't respond more often than every 5s
        self._change_threshold = 0.05  # 5% pixel change = new message
        self._response_count = 0

    def check_for_new_message(self, frame):
        """
        Check if new chat messages have appeared.
        
        Args:
            frame: Full game window capture
        
        Returns:
            dict with:
                new_message: bool
                should_respond: bool
                chat_image: numpy array of chat region (for LLM reading)
        """
        cr = CHAT_REGION
        chat_area = frame[cr["y"]:cr["y"]+cr["h"], cr["x"]:cr["x"]+cr["w"]]

        result = {
            "new_message": False,
            "should_respond": False,
            "chat_image": chat_area,
        }

        if self._last_chat_frame is None:
            self._last_chat_frame = chat_area.copy()
            return result

        # Compare with last chat frame
        diff = cv2.absdiff(
            cv2.cvtColor(chat_area, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(self._last_chat_frame, cv2.COLOR_BGR2GRAY),
        )
        change_pct = np.mean(diff > 20) # % of pixels that changed significantly

        if change_pct > self._change_threshold:
            result["new_message"] = True

            # Check cooldown
            now = time.time()
            if now - self._last_change_time >= self._cooldown:
                result["should_respond"] = True
                self._last_change_time = now

        self._last_chat_frame = chat_area.copy()
        return result

    def read_chat_with_llm(self, chat_image):
        """
        Use LLM vision to read chat text from the screenshot.
        
        Args:
            chat_image: Cropped chat area image
        
        Returns:
            str with the chat text, or None
        """
        if not self.llm or not self.llm.is_available():
            return None

        _, png_data = cv2.imencode(".png", chat_image)
        if png_data is None:
            return None

        response = self.llm.analyze_screenshot(
            png_data.tobytes(),
            "This is a chat area from MapleStory game. Read the text exactly as shown. "
            "Only output the chat text, nothing else. If there are multiple lines, "
            "show the most recent one."
        )
        return response

    def get_response(self, message_text):
        """
        Determine the appropriate response to a chat message.
        First tries knowledge base keyword matching, then falls back to LLM.
        
        Args:
            message_text: The chat message to respond to
        
        Returns:
            str response or None (None = don't respond)
        """
        from knowledge.game_data import get_chat_response

        # Try keyword-based response first (fast, reliable)
        category, response = get_chat_response(message_text)
        if response:
            self._response_count += 1
            return response

        # Fall back to LLM for complex messages
        if self.llm and self.llm.is_available():
            llm_response = self.llm.chat_response(message_text)
            if llm_response:
                self._response_count += 1
                return llm_response

        # Default: don't respond (most human thing to do)
        return None

    def type_response(self, input_sender, message):
        """
        Type a response in the chat box.
        Opens chat with Enter, types the message, sends with Enter.
        
        Args:
            input_sender: InputSender instance
            message: Text to type
        """
        import random
        
        # Open chat
        input_sender.press_key("enter", hold_time=0.05)
        time.sleep(0.3)

        # Type each character with human-like delays
        for char in message:
            char_lower = char.lower()
            if char_lower in "abcdefghijklmnopqrstuvwxyz0123456789":
                input_sender.press_key(char_lower, hold_time=0.03)
                time.sleep(random.uniform(0.04, 0.12))
            elif char == " ":
                input_sender.press_key("space", hold_time=0.03)
                time.sleep(random.uniform(0.03, 0.08))
            # Skip special characters we can't easily type

        time.sleep(random.uniform(0.1, 0.3))

        # Send message
        input_sender.press_key("enter", hold_time=0.05)
        time.sleep(0.5)

    @property
    def stats(self):
        return {"responses_sent": self._response_count}


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

    monitor = ChatMonitor()
    result = monitor.check_for_new_message(frame)
    print(f"New message: {result['new_message']}")

    # Save chat area
    cr = CHAT_REGION
    chat = frame[cr["y"]:cr["y"]+cr["h"], cr["x"]:cr["x"]+cr["w"]]
    cv2.imwrite("debug_frames/chat_monitor_test.png", chat)
    print("Chat area saved to debug_frames/chat_monitor_test.png")

    # Test response logic
    test_msgs = ["cc pls", "hey are u a bot?", "hi", "nice weather today"]
    for msg in test_msgs:
        resp = monitor.get_response(msg)
        print(f"  '{msg}' → '{resp}'")

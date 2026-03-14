"""
MapleBot - LLM Sanity Checker
Periodically screenshots the game and asks the LLM:
  - Is the character alive?
  - Is there a dialog/popup blocking gameplay?
  - Is the character stuck or not moving?
  - Is this a death screen?
  - Anything unusual?

Falls back to simple heuristics when LLM is unavailable.
"""

import time
import cv2
import numpy as np


class SanityChecker:
    """Periodic game state sanity check using vision + LLM."""

    def __init__(self, ollama_client=None, check_interval=30):
        self.llm = ollama_client
        self.check_interval = check_interval
        self._last_check = 0
        self._last_frame = None
        self._stuck_count = 0
        self._max_stuck = 10  # Consider stuck after 10 identical frames (~5 min)

    def should_check(self):
        """Is it time for a sanity check?"""
        return time.time() - self._last_check >= self.check_interval

    def check(self, frame):
        """
        Run a sanity check on the current game frame.
        
        Returns dict with:
            healthy: bool — is everything normal?
            issues: list of str — detected problems
            action: str — recommended action (continue/stop/recover)
        """
        self._last_check = time.time()
        result = {
            "healthy": True,
            "issues": [],
            "action": "continue",
        }

        # === Heuristic checks (fast, no LLM needed) ===

        # 1. Check if screen is mostly black (disconnect/crash)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        if mean_brightness < 15:
            result["healthy"] = False
            result["issues"].append("Screen is black — possible disconnect or crash")
            result["action"] = "recover"
            return result

        # 2. Check if screen is mostly white (error dialog)
        if mean_brightness > 240:
            result["healthy"] = False
            result["issues"].append("Screen is very bright — possible error popup")
            result["action"] = "recover"
            return result

        # 3. Check for stuck detection (frame similarity)
        if self._last_frame is not None:
            # Compare current frame to last frame
            diff = cv2.absdiff(
                cv2.resize(gray, (128, 96)),
                cv2.resize(
                    cv2.cvtColor(self._last_frame, cv2.COLOR_BGR2GRAY),
                    (128, 96),
                ),
            )
            similarity = 1.0 - (np.mean(diff) / 255.0)
            if similarity > 0.995:  # 99.5% similar = truly identical (even small mob movement changes this)
                self._stuck_count += 1
                if self._stuck_count >= self._max_stuck:
                    result["healthy"] = False
                    result["issues"].append(
                        f"Screen hasn't changed in {self._stuck_count} checks — character may be stuck"
                    )
                    result["action"] = "unstick"
            else:
                self._stuck_count = 0

        self._last_frame = frame.copy()

        # 4. Check for common popup colors (white dialog boxes in center)
        center_region = frame[200:400, 300:700]
        if center_region.size > 0:
            center_gray = cv2.cvtColor(center_region, cv2.COLOR_BGR2GRAY)
            white_pixels = np.sum(center_gray > 230)
            total_pixels = center_gray.size
            if white_pixels / total_pixels > 0.6:
                result["healthy"] = False
                result["issues"].append("Large white area in center — possible dialog/popup")
                result["action"] = "dismiss_popup"

        # === LLM Vision check (slow but thorough) ===
        if self.llm and self.llm.is_available() and not result["issues"]:
            try:
                # Encode frame as PNG
                _, png_data = cv2.imencode(".png", frame)
                if png_data is not None:
                    analysis = self.llm.analyze_screenshot(
                        png_data.tobytes(),
                        "This is a MapleStory game screenshot. Briefly answer: "
                        "1) Is the character visible and alive? "
                        "2) Is there any dialog box or popup blocking gameplay? "
                        "3) Is anything unusual happening? "
                        "Answer very briefly with YES/NO for each."
                    )
                    if analysis:
                        analysis_lower = analysis.lower()
                        if "dead" in analysis_lower or "died" in analysis_lower:
                            result["healthy"] = False
                            result["issues"].append(f"LLM detected death: {analysis}")
                            result["action"] = "recover"
                        if "dialog" in analysis_lower or "popup" in analysis_lower:
                            if "yes" in analysis_lower:
                                result["healthy"] = False
                                result["issues"].append(f"LLM detected popup: {analysis}")
                                result["action"] = "dismiss_popup"
            except Exception as e:
                pass  # LLM failure is not critical

        return result

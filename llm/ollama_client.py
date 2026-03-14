"""
MapleBot - Ollama LLM Client
Wraps the Ollama local API for text generation and vision analysis.
Used for sanity checks, chat responses, and situation awareness.
"""

import json
import base64
import time
import requests


OLLAMA_BASE = "http://localhost:11434"


class OllamaClient:
    """Local LLM client via Ollama API."""

    def __init__(self, model="phi3:mini", vision_model="llava:7b", timeout=30):
        self.model = model
        self.vision_model = vision_model
        self.timeout = timeout
        self._available = None

    def is_available(self):
        """Check if Ollama server is running."""
        if self._available is not None:
            return self._available
        try:
            r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
            self._available = r.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False

    def get_models(self):
        """List available models."""
        try:
            r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def generate(self, prompt, system=None, temperature=0.7, max_tokens=150):
        """
        Generate text response from LLM.
        
        Args:
            prompt: The user prompt
            system: Optional system prompt for context
            temperature: Creativity (0=focused, 1=creative)
            max_tokens: Max response length
        
        Returns:
            str response or None on failure
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

        try:
            r = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("response", "").strip()
        except Exception as e:
            print(f"[LLM] Error: {e}")
        return None

    def analyze_screenshot(self, image_bytes, prompt):
        """
        Send a screenshot to a vision model for analysis.
        
        Args:
            image_bytes: PNG image as bytes
            prompt: What to analyze about the image
        
        Returns:
            str analysis or None
        """
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.vision_model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 200,
            },
        }

        try:
            r = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json=payload,
                timeout=60,  # Vision takes longer
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("response", "").strip()
        except Exception as e:
            print(f"[LLM Vision] Error: {e}")
        return None

    def chat_response(self, incoming_message, context=""):
        """
        Generate a natural, human-like chat response.
        
        Args:
            incoming_message: What someone said to us
            context: Additional context (map, level, etc.)
        
        Returns:
            str response or None
        """
        system = (
            "You are a MapleStory player. You are a casual gamer who plays I/L mage. "
            "You are grinding and somewhat distracted (watching YouTube or something). "
            "Reply in very short, casual gamer language. Use lowercase, abbreviations, "
            "and occasional typos. Keep responses under 10 words. Never mention being a bot. "
            "If someone asks if you're a bot, deny it casually. "
            "Common responses: 'lol', 'haha', 'sry', 'mb', 'thx', 'gl', 'gg'. "
            f"Context: {context}" if context else ""
        )

        prompt = f"Someone in MapleStory just said to you: \"{incoming_message}\"\nReply briefly:"

        return self.generate(prompt, system=system, temperature=0.8, max_tokens=30)


# Quick test
if __name__ == "__main__":
    client = OllamaClient()
    print(f"Ollama available: {client.is_available()}")
    print(f"Models: {client.get_models()}")

    if client.is_available():
        print("\nTesting chat response...")
        resp = client.chat_response("hey are u a bot?")
        print(f"Response: {resp}")

        resp2 = client.chat_response("cc pls")
        print(f"Response: {resp2}")

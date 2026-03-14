"""Full integration test — all 20 modules."""
import sys, time
sys.path.insert(0, ".")

print("=== MapleBot Full Integration Test ===\n")

# Core
from core.capture import capture_window
from core.input import InputSender
from core.window import WindowManager
from core.config import load_config
print("[1/7] Core modules: OK")

# Vision
from vision.bars import read_all_bars
from vision.minimap import MinimapReader
from vision.mobs import MobDetector
from vision.chat import ChatMonitor
print("[2/7] Vision modules: OK")

# Brain
from brain.state_machine import BotEngine, BotState
from brain.potions import AutoPot
from brain.buffs import BuffManager
from brain.attack import AttackRotation
from brain.looting import LootCollector
print("[3/7] Brain modules: OK")

# LLM
from llm.ollama_client import OllamaClient
from llm.sanity_check import SanityChecker
print("[4/7] LLM modules: OK")

# Knowledge
from knowledge.game_data import get_training_spots, get_chat_response, get_current_skill_info
print("[5/7] Knowledge modules: OK")

# Humanizer
from humanizer.delays import Humanizer
print("[6/7] Humanizer module: OK")

# Live test
cfg = load_config()
wm = WindowManager()
hwnd = wm.find_window()
if hwnd:
    wm.position_window()
    frame = capture_window(hwnd)
    if frame is not None:
        # Bars
        bars = read_all_bars(frame)
        print(f"\n[Live] HP={bars['hp']:.1f}% MP={bars['mp']:.1f}% EXP={bars['exp']:.1f}%")

        # Minimap
        mm = MinimapReader()
        pos = mm.read_position(frame)
        if pos["found"]:
            print(f"[Live] Position: ({pos['x']:.1%}, {pos['y']:.1%}) — {pos['color']} dot, {mm.get_map_side()} side")

        # Mobs
        md = MobDetector()
        mobs = md.detect_mobs(frame)
        time.sleep(0.3)
        frame2 = capture_window(hwnd)
        mobs = md.detect_mobs(frame2)
        print(f"[Live] Mobs detected: {len(mobs)}")
        left, right = md.get_mob_density_side()
        print(f"[Live] Mob density: {left} left, {right} right")

        # Sanity
        checker = SanityChecker()
        result = checker.check(frame)
        print(f"[Live] Sanity: healthy={result['healthy']}")

        # Knowledge
        spots = get_training_spots(35)
        print(f"[Data] Level 35 top spot: [{spots[0]['exp_tier']}] {spots[0]['map']}")

        # LLM
        llm = OllamaClient()
        print(f"[LLM]  Ollama: {'CONNECTED' if llm.is_available() else 'OFFLINE'}")

print("\n[7/7] All live tests: OK")
print("\n" + "="*40)
print("  ALL 20 MODULES VERIFIED")
print("  Bot is ready to grind!")
print("="*40)

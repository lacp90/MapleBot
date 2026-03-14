"""
MapleBot - State Machine
The brain of the bot. Manages all states and transitions:
  IDLE → BUFFING → GRINDING → POTTING → LOOTING → GRINDING → ...

Each tick:
  1. Capture screen
  2. Read game state (HP/MP/EXP)
  3. Run sanity checks (stuck, dead, popup)
  4. Decide what to do based on priority
  5. Execute action with humanized timing
  6. Log everything
"""

import os
import time
import random
import datetime
from enum import Enum, auto


class BotState(Enum):
    """All possible bot states."""
    IDLE = auto()       # Not started or waiting
    BUFFING = auto()    # Applying buffs
    GRINDING = auto()   # Walking + attacking
    POTTING = auto()    # Using potions
    LOOTING = auto()    # Picking up items
    PAUSED = auto()     # User paused
    BREAK = auto()      # Humanizer break
    DEAD = auto()       # Character died
    RECOVERING = auto() # Handling recovery (unstick, dismiss popup)
    TOWN_TRIP = auto()  # Going to town to sell/buy
    QUESTING = auto()   # Handling quest dialog
    ERROR = auto()      # Something went wrong


class BotEngine:
    """
    Main bot engine — the state machine that drives everything.
    
    Usage:
        engine = BotEngine(hwnd, config)
        engine.start()  # Begins the main loop
    """

    def __init__(self, hwnd, config, verbose=True):
        from core.input import InputSender
        from core.capture import capture_window
        from vision.bars import read_all_bars
        from brain.potions import AutoPot
        from brain.buffs import BuffManager
        from brain.attack import AttackRotation
        from brain.looting import LootCollector
        from humanizer.delays import Humanizer
        from llm.sanity_check import SanityChecker

        # Try to initialize LLM (optional)
        try:
            from llm.ollama_client import OllamaClient
            self.llm = OllamaClient()
            if not self.llm.is_available():
                print("[Engine] Ollama not running — LLM features disabled")
                self.llm = None
        except Exception:
            self.llm = None

        self.hwnd = hwnd
        self.config = config
        self.verbose = verbose
        self._capture_fn = capture_window
        self._read_bars_fn = read_all_bars

        # Initialize all subsystems
        self.input = InputSender(hwnd)
        self.humanizer = Humanizer(config)
        self.potions = AutoPot(self.input, config)
        self.buffs = BuffManager(self.input, config)
        self.attack = AttackRotation(self.input, config, self.humanizer)
        self.loot = LootCollector(self.input, config, self.humanizer)

        # Sanity checker
        check_interval = config.get("timers", {}).get("llm_check_interval", 30)
        self.sanity = SanityChecker(self.llm, check_interval=check_interval)

        # Vision modules
        from vision.minimap import MinimapReader
        from vision.mobs import MobDetector
        from vision.chat import ChatMonitor
        self.minimap = MinimapReader()
        self.mob_detector = MobDetector()
        self.chat_monitor = ChatMonitor(self.llm)

        # Level-up handler (auto AP/SP allocation)
        from brain.level_up import LevelUpHandler
        self.level_up = LevelUpHandler(self.input, config)

        # Town trip manager (sell items, buy pots)
        from brain.town_trip import TownTripManager
        self.town = TownTripManager(self.input, config, capture_window)
        self._town_enabled = config.get("town_trip", {}).get("enabled", True)

        # Quest handler (lightbulb detection, NPC dialogs)
        from brain.quests import QuestHandler
        start_level = config.get("character", {}).get("start_level", 7)
        self.quests = QuestHandler(self.input, config, level=start_level)

        # State
        self.state = BotState.IDLE
        self._running = False
        self._paused = False
        self._direction = config.get("grinding", {}).get("start_direction", "right")
        self._tick_count = 0
        self._start_time = None
        self._last_bars = {"hp": -1, "mp": -1, "exp": -1}
        self._last_exp = -1
        self._exp_gained = 0

        # Grinding config
        grinding = config.get("grinding", {})
        self._walk_min = grinding.get("walk_duration_min", 1.5)
        self._walk_max = grinding.get("walk_duration_max", 3.5)

        # Capture rate
        self._capture_interval = config.get("timers", {}).get("capture_interval", 0.15)

        # File logging
        log_cfg = config.get("logging", {})
        self._log_file = None
        if log_cfg.get("enabled", True):
            log_dir = log_cfg.get("log_dir", "logs")
            os.makedirs(log_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_file = open(os.path.join(log_dir, f"session_{ts}.log"), "w")

    def start(self):
        """Start the bot main loop."""
        self._running = True
        self._start_time = time.time()
        self.state = BotState.IDLE
        self._log("="*50)
        self._log("  MapleBot Engine Started")
        self._log(f"  Humanizer: {'ON' if self.humanizer.enabled else 'OFF'}")
        self._log(f"  LLM: {'CONNECTED' if self.llm else 'OFFLINE'}")
        self._log(f"  HP pot threshold: {self.potions.hp_threshold}%")
        self._log(f"  MP pot threshold: {self.potions.mp_threshold}%")
        self._log(f"  Buff interval: {self.buffs.buff_interval}s")
        self._log(f"  Sanity check every: {self.sanity.check_interval}s")
        self._log("="*50)

        try:
            self._main_loop()
        except KeyboardInterrupt:
            self._log("\nBot stopped by user (Ctrl+C)")
        finally:
            self._running = False
            self._release_all_keys()
            self._print_session_stats()
            if self._log_file:
                self._log_file.close()

    def stop(self):
        """Stop the bot gracefully."""
        self._running = False

    def pause(self):
        """Toggle pause state."""
        self._paused = not self._paused
        if self._paused:
            self._release_all_keys()
            self.state = BotState.PAUSED
            self._log("[Engine] PAUSED")
        else:
            self.state = BotState.GRINDING
            self._log("[Engine] RESUMED")

    def _main_loop(self):
        """The core bot loop."""
        while self._running:
            if self._paused:
                time.sleep(0.5)
                continue

            self._tick_count += 1

            # Step 1: Capture screen
            frame = self._capture_fn(self.hwnd)
            if frame is None:
                self._log("[Engine] Capture failed! Window may be minimized.")
                self.state = BotState.ERROR
                time.sleep(2)
                continue

            # Step 2: Read game state
            bars = self._read_bars_fn(frame)
            self._last_bars = bars
            hp = bars.get("hp", -1)
            mp = bars.get("mp", -1)
            exp = bars.get("exp", -1)

            # Track EXP gains
            if self._last_exp >= 0 and exp >= 0 and exp != self._last_exp:
                if exp > self._last_exp:
                    self._exp_gained += (exp - self._last_exp)
            self._last_exp = exp

            # Level-up detection & auto AP/SP allocation
            if exp >= 0:
                leveled = self.level_up.handle_level_up(exp)
                if leveled:
                    self._log(f"[LEVEL UP!] Now level {self.level_up.level}!")
                    self._log(f"[LEVEL UP] AP allocated to INT, SP to {self.level_up.stats['sp_distribution']}")
                    continue

            # Step 3: Death detection
            if 0 <= hp < 1:
                self.state = BotState.DEAD
                self._log(f"[Engine] Character may be DEAD! HP={hp}%")
                time.sleep(3)
                continue

            # Step 4: Priority-based state transitions
            #  Priority 1: Emergency pot
            #  Priority 2: Potions
            #  Priority 3: Buffs
            #  Priority 4: Humanizer break
            #  Priority 5: Loot
            #  Priority 6: Grind

            # Emergency pot check
            if 0 < hp < self.potions.safe_hp:
                self.state = BotState.POTTING
                self._log(f"[Engine] EMERGENCY POT — HP={hp:.0f}%")
                self.potions.check_and_pot(hp, mp)
                continue

            # Normal pot check
            pot_action = None
            if (0 < hp < self.potions.hp_threshold) or (0 < mp < self.potions.mp_threshold):
                self.state = BotState.POTTING
                pot_action = self.potions.check_and_pot(hp, mp)
                if pot_action:
                    self._log(f"[Engine] {pot_action} — HP={hp:.0f}% MP={mp:.0f}%")

            # Buff check
            if self.buffs.needs_rebuff():
                self.state = BotState.BUFFING
                self._log("[Engine] Rebuffing...")
                self.buffs.apply_buffs(self.humanizer)
                self.humanizer.action_delay()
                continue

            # Humanizer break check
            if self.humanizer.should_take_break():
                self.state = BotState.BREAK
                self._release_all_keys()
                self.humanizer.take_break()
                self.state = BotState.GRINDING
                continue

            # Sanity check (periodic)
            if self.sanity.should_check():
                check = self.sanity.check(frame)
                if not check["healthy"]:
                    self._log(f"[Sanity] Issues: {check['issues']}")
                    self._log(f"[Sanity] Recommended: {check['action']}")
                    self._handle_recovery(check["action"])
                    continue

            # Town trip check (sell items, buy pots)
            if self._town_enabled and self.town.needs_town_trip():
                self.state = BotState.TOWN_TRIP
                self._log("[Engine] TOWN TRIP — selling items and restocking potions...")
                self._log(f"[Engine] Loots since sell: {self.town.stats['items_looted_since_sell']}")
                success = self.town.execute_town_trip(self.hwnd)
                if success:
                    self._log("[Engine] Town trip complete — resuming grinding")
                else:
                    self._log("[Engine] Town trip failed — resuming anyway")
                self.state = BotState.GRINDING
                continue

            # Quest lightbulb check (every 20 ticks) — detection only, no auto-click
            # Enable auto-click later by setting quests.auto_handle = True
            if self._tick_count % 20 == 0:
                self.quests.update_level(self.level_up.level)
                if self.quests.check_for_lightbulb(frame):
                    self._log("[Quest] Lightbulb detected — ignoring (auto-click disabled)")

            # Chat monitor (check every 10 ticks to save CPU)
            if self._tick_count % 10 == 0:
                chat_result = self.chat_monitor.check_for_new_message(frame)
                if chat_result["new_message"] and chat_result["should_respond"]:
                    # Try to read chat and respond
                    msg_text = None
                    if self.llm:
                        msg_text = self.chat_monitor.read_chat_with_llm(chat_result["chat_image"])
                    if msg_text:
                        response = self.chat_monitor.get_response(msg_text)
                        if response:
                            self._log(f"[Chat] Responding to '{msg_text}' with '{response}'")
                            self.chat_monitor.type_response(self.input, response)

            # Loot check
            if self.attack.should_loot():
                self.state = BotState.LOOTING
                self.loot.sweep_loot()
                self.humanizer.action_delay()

            # Read minimap position
            pos = self.minimap.read_position(frame)

            # Detect mobs
            mobs = self.mob_detector.detect_mobs(frame)

            # GRINDING — the main loop
            self.state = BotState.GRINDING
            self._grind_tick(pos, mobs)

            # Status update every 50 ticks
            if self._tick_count % 50 == 0:
                elapsed = (time.time() - self._start_time) / 60
                mob_count = self.mob_detector.get_mob_count()
                pos_str = f"pos=({pos['x']:.0%},{pos['y']:.0%})" if pos.get("found") else "pos=?"
                self._log(
                    f"[Tick {self._tick_count}] "
                    f"HP={hp:.0f}% MP={mp:.0f}% EXP={exp:.0f}% | "
                    f"{pos_str} mobs={mob_count} | "
                    f"Time={elapsed:.1f}m | "
                    f"Atk={self.attack.stats['total_actions']} "
                    f"Pot={self.potions.stats['hp_pots_used']}hp/{self.potions.stats['mp_pots_used']}mp"
                )

    def _grind_tick(self, pos=None, mobs=None):
        """
        Natural patrol pattern:
          Walk 2-4s → Stop → Attack 2x → Loot → Flip direction
          Every 6 ticks: change platform (jump/drop)
        """
        if not hasattr(self, "_patrol_tick"):
            self._patrol_tick = 0
        self._patrol_tick += 1

        # === WALK to next spot ===
        walk_time = random.uniform(2.0, 4.0)
        self.input.hold_key(self._direction, walk_time)

        # === STOP and ATTACK 2 times ===
        for _ in range(2):
            self.input.press_key("x", hold_time=random.uniform(0.08, 0.12))
            time.sleep(random.uniform(0.5, 0.7))

        # === LOOT ===
        self.loot.quick_loot()

        # === ALWAYS flip direction (guarantees full patrol) ===
        self._direction = "left" if self._direction == "right" else "right"

        # === Every 6 ticks, change platform ===
        if self._patrol_tick % 6 == 0:
            if random.random() < 0.6:
                self._jump_up()
            else:
                self._drop_down()

    def _drop_down(self):
        """Drop through a platform by pressing DOWN + JUMP."""
        self.input.key_down("down")
        time.sleep(0.05)
        self.input.press_key("alt", hold_time=0.06)
        time.sleep(0.1)
        self.input.key_up("down")
        time.sleep(0.3)

    def _jump_up(self):
        """Jump up to a higher platform or climb a rope/ladder."""
        # First try jumping while moving (reach higher platform)
        self.input.key_down(self._direction)
        time.sleep(0.03)
        self.input.press_key("alt", hold_time=0.08)
        time.sleep(0.3)
        self.input.key_up(self._direction)
        time.sleep(0.2)

        # Also try climbing (UP key for ropes/ladders)
        if random.random() < 0.4:
            self.input.hold_key("up", random.uniform(0.8, 1.5))
            time.sleep(0.2)

    def _release_all_keys(self):
        """Safety: release all keys to prevent stuck keys."""
        for key in ["left", "right", "up", "down", "alt", "ctrl", "shift", "z"]:
            try:
                self.input.key_up(key)
            except Exception:
                pass

    def _print_session_stats(self):
        """Print end-of-session statistics."""
        if self._start_time is None:
            return
        elapsed = (time.time() - self._start_time) / 60
        self._log("\n" + "="*50)
        self._log("  Session Summary")
        self._log("="*50)
        self._log(f"  Duration:     {elapsed:.1f} minutes")
        self._log(f"  Total ticks:  {self._tick_count}")
        self._log(f"  Attacks:      {self.attack.stats['total_actions']}")
        self._log(f"  Skills used:  {self.attack.stats['skills']}")
        self._log(f"  HP pots:      {self.potions.stats['hp_pots_used']}")
        self._log(f"  MP pots:      {self.potions.stats['mp_pots_used']}")
        self._log(f"  Buff cycles:  {self.buffs.stats['buff_cycles']}")
        self._log(f"  Loot attempts:{self.loot.stats['loot_attempts']}")
        self._log(f"  EXP gained:   ~{self._exp_gained:.1f}%")
        self._log(f"  Session time: {self.humanizer.session_minutes:.1f} min")
        self._log("="*50)

    def _handle_recovery(self, action):
        """Handle recovery based on sanity check recommendation."""
        self.state = BotState.RECOVERING
        self._release_all_keys()

        if action == "unstick":
            self._log("[Recovery] Attempting to unstick — jumping and moving...")
            # Try to unstick by jumping and walking
            self.input.press_key("alt", hold_time=0.06)  # Jump
            time.sleep(0.3)
            direction = random.choice(["left", "right"])
            self.input.hold_key(direction, random.uniform(1.0, 2.5))
            time.sleep(0.5)
            self.input.press_key("alt", hold_time=0.06)  # Jump again
            time.sleep(0.5)

        elif action == "dismiss_popup":
            self._log("[Recovery] Attempting to dismiss popup...")
            # Try common dismiss keys
            self.input.press_key("enter", hold_time=0.05)
            time.sleep(0.5)
            self.input.press_key("space", hold_time=0.05)
            time.sleep(0.5)
            self.input.press_key("enter", hold_time=0.05)
            time.sleep(0.5)

        elif action == "recover":
            self._log("[Recovery] Major issue detected — waiting 10s before retry...")
            time.sleep(10)

        else:
            self._log(f"[Recovery] Unknown action: {action} — waiting...")
            time.sleep(5)

        self.state = BotState.GRINDING

    def _log(self, msg):
        """Print a log message and write to log file."""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        if self.verbose:
            print(line)
        if self._log_file:
            try:
                self._log_file.write(line + "\n")
                self._log_file.flush()
            except Exception:
                pass

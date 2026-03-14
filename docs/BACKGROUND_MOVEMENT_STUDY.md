# MapleBot Background Movement — Research Study

## Problem
MapleStory v62 (MapleRoyals) ignores `PostMessage`/`SendMessage` for movement keys (arrows).
The game reads keyboard state from hardware APIs, which only work when the game has focus.

## Goal
Enable true background movement — character walks left/right while user works in other apps.

---

## Methods Tested (Chronological)

### ❌ Phase 1: Win32 Message-Based
| # | Method | Result |
|---|--------|--------|
| 1 | `PostMessage WM_KEYDOWN` with various flags | No movement |
| 2 | `SendMessage WM_KEYDOWN` (synchronous) | No movement |
| 3 | `AttachThreadInput` + `SetKeyboardState` + `PostMessage` | No movement |
| 4 | `WM_CHAR` messages for arrow keys | No movement |
| 5 | Fake `WM_ACTIVATE` + `WM_SETFOCUS` + `PostMessage` | No movement |
| 6 | `SetFocus` (changes input target without foreground) + `SendMessage` | No movement |
| 7 | Continuous `SetKeyboardState` every 16ms + `PostMessage` | No movement |
| 8 | Numpad arrow keys / extended key flags | No movement |
| 9 | Child window targeting | No child windows exist |

**Conclusion:** The game does NOT process WM_KEYDOWN for arrows. It reads keyboard state directly.

### ❌ Phase 2: Desktop Isolation
| # | Method | Result |
|---|--------|--------|
| 10 | `CreateDesktopW` — separate Windows desktop | Game appeared on main desktop, no isolation |

### ❌ Phase 3: DirectInput Hooking
| # | Method | Result |
|---|--------|--------|
| 11 | Hook `GetDeviceState` (vtable index 9) in dinput8.dll | 0 calls — game doesn't use DirectInput for keyboard |
| 12 | Hook ALL functions in dinput8.dll with counters | 0 calls on any function |

**Key Finding:** `dinput8.dll` is loaded but NOT used for keyboard (probably mouse/joystick only).

### ❌ Phase 4: GetAsyncKeyState Hooking
| # | Method | Result |
|---|--------|--------|
| 13 | 64-bit Python → Hook `GetAsyncKeyState` | Process hung (arch mismatch) |
| 14 | 32-bit Python → Hook `GetAsyncKeyState` | Hook installed, 0 calls |
| 15 | Hook ALL keyboard functions (6 total) | 0 calls on all |

**Key Finding:** Game stops polling keyboard entirely when unfocused. It checks focus FIRST.

### ❌ Phase 5: Single Focus Hook
| # | Method | Result |
|---|--------|--------|
| 16 | Hook `GetForegroundWindow` only → return game HWND | Still 0 calls to `GetAsyncKeyState` |

**Key Finding:** Game checks MULTIPLE focus functions, not just one.

### ✅ Phase 6: Multi-Function Focus Hook (THE SOLUTION)
| # | Method | Result |
|---|--------|--------|
| 17 | Hook `GetForegroundWindow` + `GetFocus` + `GetActiveWindow` + `GetCapture` + `GetAsyncKeyState` | **CHARACTER MOVED!** 🎉 |

---

## The Solution: Multi-Function Focus Trick

### Architecture
```
┌─────────────────────────────────────────┐
│           MapleStory Process            │
│                                         │
│  Game Loop:                             │
│  ┌──────────────────────────────┐       │
│  │ 1. Check focus:              │       │
│  │    GetForegroundWindow() ──┐ │       │
│  │    GetFocus()  ────────────┤ │       │
│  │    GetActiveWindow() ──────┤ │       │
│  │    GetCapture() ───────────┤ │       │
│  │                 ALL return │ │       │
│  │                 game HWND ◄┘ │       │
│  │                              │       │
│  │ 2. "I have focus! Read keys" │       │
│  │    GetAsyncKeyState(VK_LEFT) │       │
│  │    GetAsyncKeyState(VK_RIGHT)│       │
│  │    → Returns 0x8001 if our   │       │
│  │      key table says pressed  │       │
│  │                              │       │
│  │ 3. Move character!           │       │
│  └──────────────────────────────┘       │
│                                         │
│  Our hooks in allocated memory:         │
│  ┌────────────┐ ┌──────────────────┐    │
│  │ Key Table  │ │ Shellcode Hooks  │    │
│  │ [256 bytes]│ │ (focus + keystate)│   │
│  └────────────┘ └──────────────────┘    │
└─────────────────────────────────────────┘
         ▲ WriteProcessMemory
         │
┌────────┴────────────────────────────────┐
│          Python Bot (32-bit)            │
│  pm.write_bytes(key_table + 0x27, 0x01) │  ← "walk right"
│  time.sleep(2.0)                        │
│  pm.write_bytes(key_table + 0x27, 0x00) │  ← "stop"
└─────────────────────────────────────────┘
```

### Stealth Properties
- **No DLL file** on disk (pure shellcode injection)
- **No module list entries** (not visible to `EnumProcessModules`)
- **Cleanly removable** (original bytes restored on exit)
- **Minimal footprint** (~100 bytes of shellcode + 256-byte key table)

### Technical Details
- **Architecture requirement:** Must use 32-bit Python to match 32-bit game
- **32-bit Python location:** `C:\Python312-32\python.exe`
- **Hooks placed at:** USER32.dll exports (GetForegroundWindow, GetFocus, etc.)
- **Shellcode type:** x86 inline hooks with JMP+trampoline pattern

### Key Files
- `core/memory_input.py` — `MemoryHook` class (hook installation/management)
- `core/input.py` — `InputSender` class (integrated with MemoryHook)
- `scripts/double_hook.py` — Standalone test/prototype

---

## Other Keys (Non-Movement)
PostMessage works perfectly for these keys in the background:
- **Attack:** Ctrl, X
- **Jump:** Alt  
- **Loot:** Z
- **Buffs:** F1-F8
- **Skills:** Number keys, letter keys
- **Items:** Insert, Delete, Home, End, PgUp, PgDn

Only **arrow keys** (movement) needed the memory hook approach.

## Potential Future Explorations
- Speed hack (modify movement speed pointer — server has tolerance)
- Vac hack (modify mob positions — client-side, use carefully)
- No-delay attack (remove animation timer — moderate risk)
- *Avoid:* Godmode, one-hit kill, full map attack (server-validated = instant ban)

"""
MapleBot - Memory-Based Background Input (Movement)
====================================================
Hooks Win32 API functions inside the MapleStory process to enable
true background movement without requiring window focus.

How it works:
  1. Hooks GetForegroundWindow, GetFocus, GetActiveWindow, GetCapture
     → All return the game's HWND, tricking the game into thinking it's focused
  2. Hooks GetAsyncKeyState
     → Returns 0x8001 ("pressed") for arrow keys we control
  3. Bot writes to a shared key table in game memory to control movement

Requirements:
  - Must run from 32-bit Python (C:\\Python312-32\\python.exe)
  - Game must be running (attached via pymem)
  
Stealth:
  - No DLL file on disk
  - No module list entries
  - Pure shellcode in allocated memory
  - Cleanly removable (original bytes restored on exit)
"""
import ctypes
import ctypes.wintypes
import struct
import time
import pymem
import pymem.process

PAGE_EXECUTE_READWRITE = 0x40

# Virtual key codes for arrow keys
VK_LEFT  = 0x25
VK_UP    = 0x26
VK_RIGHT = 0x27
VK_DOWN  = 0x28

CONTROLLED_VK = {VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN}

# Map friendly names to VK codes
VK_NAME_MAP = {
    "left": VK_LEFT, "right": VK_RIGHT,
    "up": VK_UP, "down": VK_DOWN,
}


class MemoryHook:
    """
    Multi-function hook that tricks MapleStory into accepting
    background keyboard input for movement.
    """

    def __init__(self, process_name="MapleRoyals.exe"):
        self.pm = None
        self.process_name = process_name
        self.game_hwnd = 0
        self.alloc_base = 0       # Base of our allocated memory
        self.key_table = 0        # 256-byte key state table
        self.hooked = False
        self._originals = {}      # addr -> original_bytes for unhooking

    # ----------------------------------------------------------
    # Attach / Detach
    # ----------------------------------------------------------
    def attach(self):
        """Attach to the MapleStory process."""
        for name in [self.process_name, "MapleRoyals.exe", "MapleStory.exe"]:
            try:
                self.pm = pymem.Pymem(name)
                self.process_name = name
                print(f"[MemHook] Attached to {name} (PID: {self.pm.process_id})")
                return True
            except pymem.exception.ProcessNotFound:
                continue
        print("[MemHook] MapleStory process not found!")
        return False

    def _find_game_hwnd(self):
        """Find the MapleStory window handle."""
        import win32gui
        results = []
        def cb(hwnd, _):
            if 'MapleRoyals' in win32gui.GetWindowText(hwnd):
                results.append(hwnd)
        win32gui.EnumWindows(cb, None)
        if results:
            self.game_hwnd = results[0]
            print(f"[MemHook] Game HWND: 0x{self.game_hwnd:08X}")
            return True
        print("[MemHook] Game window not found!")
        return False

    def _find_export(self, dll_name, func_name):
        """Find a function address in the game's loaded DLL."""
        for mod in pymem.process.enum_process_module(self.pm.process_handle):
            if mod.name and dll_name.lower() in mod.name.lower():
                base = mod.lpBaseOfDll
                try:
                    e_lfanew = self.pm.read_int(base + 0x3C)
                    opt = base + e_lfanew + 24
                    exp_rva = self.pm.read_int(opt + 96)
                    if exp_rva == 0:
                        continue
                    exp = base + exp_rva
                    nn = self.pm.read_int(exp + 24)
                    nr = self.pm.read_int(exp + 32)
                    fr = self.pm.read_int(exp + 28)
                    orn = self.pm.read_int(exp + 36)
                    for i in range(nn):
                        n_rva = self.pm.read_int(base + nr + i * 4)
                        nb = self.pm.read_bytes(base + n_rva, len(func_name) + 1)
                        ns = nb.split(b'\x00')[0].decode('ascii', 'ignore')
                        if ns == func_name:
                            o = self.pm.read_short(base + orn + i * 2)
                            f = self.pm.read_int(base + fr + o * 4)
                            return base + f
                except Exception:
                    pass
        return None

    # ----------------------------------------------------------
    # Hook Installation
    # ----------------------------------------------------------
    def install(self):
        """Install all hooks for background movement."""
        if not self.pm:
            raise RuntimeError("Not attached to process")
        if not self._find_game_hwnd():
            return False

        # Allocate memory in game process
        # Layout: [0..255] key table | [256..511] counters | [512+] hook code
        self.alloc_base = self.pm.allocate(8192)
        self.key_table = self.alloc_base
        counters = self.alloc_base + 256
        hook_base = self.alloc_base + 512

        # Zero everything
        self.pm.write_bytes(self.alloc_base, b'\x00' * 4096, 4096)

        # Make executable
        old_prot = ctypes.wintypes.DWORD()
        ctypes.windll.kernel32.VirtualProtectEx(
            self.pm.process_handle, self.alloc_base, 8192,
            PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))

        # --- Hook focus functions to return game HWND ---
        focus_funcs = [
            ("USER32.dll", "GetForegroundWindow"),
            ("USER32.dll", "GetFocus"),
            ("USER32.dll", "GetActiveWindow"),
            ("USER32.dll", "GetCapture"),
        ]

        hook_idx = 0
        for dll, func in focus_funcs:
            addr = self._find_export(dll, func)
            if not addr:
                continue
            orig = self.pm.read_bytes(addr, 16)
            hook_addr = hook_base + hook_idx * 64

            # Shellcode: return game_hwnd
            sc = bytearray()
            sc += b'\xB8' + struct.pack('<I', self.game_hwnd)  # mov eax, hwnd
            sc += b'\xC3'                                       # ret
            self.pm.write_bytes(hook_addr, bytes(sc), len(sc))

            # Patch function entry
            self._patch_function(addr, hook_addr, orig[:5])
            self._originals[addr] = orig[:5]
            hook_idx += 1

        # --- Hook GetAsyncKeyState ---
        gaks_addr = self._find_export("USER32.dll", "GetAsyncKeyState")
        if gaks_addr:
            gaks_orig = self.pm.read_bytes(gaks_addr, 16)
            hook_addr = hook_base + hook_idx * 64

            sc = self._build_gaks_hook(gaks_addr, gaks_orig[:5], hook_addr)
            self.pm.write_bytes(hook_addr, bytes(sc), len(sc))
            self._patch_function(gaks_addr, hook_addr, gaks_orig[:5])
            self._originals[gaks_addr] = gaks_orig[:5]
            hook_idx += 1

        self.hooked = True
        print(f"[MemHook] ✅ {hook_idx} hooks installed — background movement enabled!")
        return True

    def _build_gaks_hook(self, orig_addr, orig_bytes, hook_addr):
        """Build GetAsyncKeyState hook shellcode."""
        sc = bytearray()

        # mov eax, [esp+4]  — get vKey argument
        sc += b'\x8B\x44\x24\x04'

        # Check if in arrow key range (0x25-0x28)
        sc += b'\x83\xF8\x25'      # cmp eax, 0x25
        jb_pos = len(sc) + 1
        sc += b'\x72\x00'           # jb .call_original

        sc += b'\x83\xF8\x28'      # cmp eax, 0x28
        ja_pos = len(sc) + 1
        sc += b'\x77\x00'           # ja .call_original

        # Check our key table
        sc += b'\x0F\xB6\x80'      # movzx eax, byte [eax + key_table]
        sc += struct.pack('<I', self.key_table)

        sc += b'\x85\xC0'           # test eax, eax
        jz_pos = len(sc) + 1
        sc += b'\x74\x00'           # jz .call_original

        # Return 0x8001 (key pressed)
        sc += b'\xB8\x01\x80\x00\x00'  # mov eax, 0x8001
        sc += b'\xC2\x04\x00'           # ret 4 (stdcall)

        # .call_original:
        call_orig_offset = len(sc)
        sc[jb_pos] = call_orig_offset - (jb_pos + 1)
        sc[ja_pos] = call_orig_offset - (ja_pos + 1)
        sc[jz_pos] = call_orig_offset - (jz_pos + 1)

        # Execute original prologue + jump back
        sc += bytes(orig_bytes)
        jmp_back = (orig_addr + 5) - (hook_addr + len(sc) + 5)
        sc += b'\xE9' + struct.pack('<i', jmp_back)

        return sc

    def _patch_function(self, func_addr, hook_addr, orig_bytes):
        """Patch function entry with JMP to our hook."""
        old_prot = ctypes.wintypes.DWORD()
        ctypes.windll.kernel32.VirtualProtectEx(
            self.pm.process_handle, func_addr, 16,
            PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        jmp_rel = hook_addr - (func_addr + 5)
        self.pm.write_bytes(func_addr, b'\xE9' + struct.pack('<i', jmp_rel), 5)

    # ----------------------------------------------------------
    # Key Control API
    # ----------------------------------------------------------
    def press_key(self, key):
        """Press an arrow key (background, no focus needed)."""
        if not self.hooked:
            return
        vk = VK_NAME_MAP.get(key, key) if isinstance(key, str) else key
        self.pm.write_bytes(self.key_table + vk, b'\x01', 1)

    def release_key(self, key):
        """Release an arrow key."""
        if not self.hooked:
            return
        vk = VK_NAME_MAP.get(key, key) if isinstance(key, str) else key
        self.pm.write_bytes(self.key_table + vk, b'\x00', 1)

    def hold_key(self, key, duration):
        """Hold a key for a duration (fully background)."""
        self.press_key(key)
        time.sleep(duration)
        self.release_key(key)

    def release_all(self):
        """Release all controlled keys."""
        for vk in CONTROLLED_VK:
            self.release_key(vk)

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------
    def uninstall(self):
        """Remove all hooks and restore original bytes."""
        if not self.hooked:
            return
        self.release_all()

        for addr, orig in self._originals.items():
            try:
                old_prot = ctypes.wintypes.DWORD()
                ctypes.windll.kernel32.VirtualProtectEx(
                    self.pm.process_handle, addr, 16,
                    PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
                self.pm.write_bytes(addr, orig, len(orig))
            except Exception:
                pass

        if self.alloc_base:
            ctypes.windll.kernel32.VirtualFreeEx(
                self.pm.process_handle, self.alloc_base, 0, 0x8000)

        self.hooked = False
        self._originals.clear()
        print("[MemHook] All hooks removed, original functions restored.")

    def __del__(self):
        try:
            self.uninstall()
        except Exception:
            pass


# ==============================================================
# Quick standalone test
# ==============================================================
if __name__ == "__main__":
    print("=== Memory Hook Test ===")
    print("Make sure MapleStory is running and you're logged in!")
    print()

    hook = MemoryHook()
    if not hook.attach():
        exit(1)
    if not hook.install():
        exit(1)

    print("\n>>> CLICK YOUR IDE NOW — 5 seconds <<<")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    print("Walking RIGHT for 3 seconds...")
    hook.hold_key("right", 3.0)
    time.sleep(0.5)
    print("Walking LEFT for 3 seconds...")
    hook.hold_key("left", 3.0)

    print("\nDone! Removing hooks...")
    hook.uninstall()
    print("=== TEST COMPLETE === Did the character move? ===")

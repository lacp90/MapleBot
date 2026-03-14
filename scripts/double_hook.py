"""
Hook ALL focus-related functions to find which one the game uses.
Also hook GetAsyncKeyState and count calls.
"""
import pymem, pymem.process, ctypes, ctypes.wintypes, struct, time, win32gui

PAGE_EXECUTE_READWRITE = 0x40

pm = pymem.Pymem('MapleRoyals.exe')
print(f"Game PID: {pm.process_id}")

# Find game HWND
results = []
def find_maple(hwnd, _):
    if 'MapleRoyals' in win32gui.GetWindowText(hwnd):
        results.append(hwnd)
win32gui.EnumWindows(find_maple, None)
game_hwnd = results[0] if results else 0
print(f"Game HWND: 0x{game_hwnd:08X}")

def find_func(dll, name):
    for mod in pymem.process.enum_process_module(pm.process_handle):
        if mod.name and dll.lower() in mod.name.lower():
            base = mod.lpBaseOfDll
            try:
                e_lfanew = pm.read_int(base + 0x3C)
                opt = base + e_lfanew + 24
                exp_rva = pm.read_int(opt + 96)
                if exp_rva == 0: continue
                exp = base + exp_rva
                nn = pm.read_int(exp + 24)
                nr = pm.read_int(exp + 32)
                fr = pm.read_int(exp + 28)
                orn = pm.read_int(exp + 36)
                for i in range(nn):
                    n_rva = pm.read_int(base + nr + i*4)
                    nb = pm.read_bytes(base + n_rva, len(name)+1)
                    ns = nb.split(b'\x00')[0].decode('ascii','ignore')
                    if ns == name:
                        o = pm.read_short(base + orn + i*2)
                        f = pm.read_int(base + fr + o*4)
                        return base + f
            except: pass
    return None

# ALL focus-related functions
focus_funcs = [
    ("USER32.dll", "GetForegroundWindow"),
    ("USER32.dll", "GetFocus"),
    ("USER32.dll", "GetActiveWindow"),
    ("USER32.dll", "GetCapture"),
    ("USER32.dll", "GetAsyncKeyState"),
    ("win32u.dll", "NtUserGetForegroundWindow"),
    ("win32u.dll", "NtUserGetAsyncKeyState"),
]

# Allocate memory
alloc = pm.allocate(8192)
key_table = alloc           # 256 bytes
counters = alloc + 256      # 64 bytes (16 * 4)
hook_base = alloc + 512     # hook code

pm.write_bytes(alloc, b'\x00' * 4096, 4096)

old_prot = ctypes.wintypes.DWORD()
ctypes.windll.kernel32.VirtualProtectEx(
    pm.process_handle, alloc, 8192,
    PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))

originals = {}
hook_idx = 0

for dll, func in focus_funcs:
    addr = find_func(dll, func)
    if not addr:
        print(f"  {dll}:{func} - NOT FOUND")
        continue
    
    orig = pm.read_bytes(addr, 16)
    print(f"  {dll}:{func} @ 0x{addr:08X}")
    
    counter_addr = counters + hook_idx * 4
    hook_addr = hook_base + hook_idx * 64  # 64 bytes per hook
    
    if func in ("GetForegroundWindow", "NtUserGetForegroundWindow",
                "GetFocus", "GetActiveWindow", "GetCapture"):
        # Return game_hwnd AND increment counter
        sc = bytearray()
        sc += b'\xFF\x05' + struct.pack('<I', counter_addr)
        sc += b'\xB8' + struct.pack('<I', game_hwnd)
        sc += b'\xC3'  # ret
    elif func == "GetAsyncKeyState":
        # Check key table, return 0x8001 if set, else call original
        sc = bytearray()
        sc += b'\xFF\x05' + struct.pack('<I', counter_addr)
        sc += b'\x8B\x44\x24\x04'  # mov eax, [esp+4]
        sc += b'\x83\xF8\x25'      # cmp eax, 0x25
        jb_pos = len(sc) + 1
        sc += b'\x72\x00'
        sc += b'\x83\xF8\x28'      # cmp eax, 0x28
        ja_pos = len(sc) + 1
        sc += b'\x77\x00'
        sc += b'\x0F\xB6\x80'      # movzx eax, byte [eax + key_table]
        sc += struct.pack('<I', key_table)
        sc += b'\x85\xC0'           # test eax, eax
        jz_pos = len(sc) + 1
        sc += b'\x74\x00'
        sc += b'\xB8\x01\x80\x00\x00'  # mov eax, 0x8001
        sc += b'\xC2\x04\x00'           # ret 4
        # call_original:
        call_orig = len(sc)
        sc[jb_pos] = call_orig - (jb_pos + 1)
        sc[ja_pos] = call_orig - (ja_pos + 1)
        sc[jz_pos] = call_orig - (jz_pos + 1)
        sc += bytes(orig[:5])
        jmp = (addr + 5) - (hook_addr + len(sc) + 5)
        sc += b'\xE9' + struct.pack('<i', jmp)
    else:
        # NtUserGetAsyncKeyState - just count + trampoline
        sc = bytearray()
        sc += b'\xFF\x05' + struct.pack('<I', counter_addr)
        sc += bytes(orig[:5])
        jmp = (addr + 5) - (hook_addr + len(sc) + 5)
        sc += b'\xE9' + struct.pack('<i', jmp)
    
    pm.write_bytes(hook_addr, bytes(sc), len(sc))
    
    # Patch
    ctypes.windll.kernel32.VirtualProtectEx(
        pm.process_handle, addr, 16,
        PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    jmp_rel = hook_addr - (addr + 5)
    pm.write_bytes(addr, b'\xE9' + struct.pack('<i', jmp_rel), 5)
    
    originals[addr] = (orig[:5], dll, func, counter_addr)
    hook_idx += 1

print(f"\nHooked {hook_idx} functions!")
print(">>> CLICK YOUR IDE - 5 seconds <<<")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

print("\nResults (unfocused):")
gaks_called = False
for addr, (orig, dll, func, cnt) in originals.items():
    c = pm.read_int(cnt)
    mark = "✅" if c > 0 else "❌"
    print(f"  {mark} {dll}:{func} = {c} calls")
    if func == "GetAsyncKeyState" and c > 0:
        gaks_called = True

if gaks_called:
    print("\n🎉 GetAsyncKeyState IS called! Testing movement...")
    pm.write_bytes(key_table + 0x27, b'\x01', 1)  # RIGHT
    time.sleep(3)
    pm.write_bytes(key_table + 0x27, b'\x00', 1)
    time.sleep(0.5)
    pm.write_bytes(key_table + 0x25, b'\x01', 1)  # LEFT
    time.sleep(3)
    pm.write_bytes(key_table + 0x25, b'\x00', 1)
    print("Did the character move?!")

# Unhook all
for addr, (orig, dll, func, cnt) in originals.items():
    pm.write_bytes(addr, orig, 5)

pm.close_process()
print("\nAll hooks removed. Done!")

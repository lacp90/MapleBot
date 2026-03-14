"""
FINAL diagnostic: Hook NtUserGetAsyncKeyState at the syscall level,
verify the hook IS installed by reading back patched bytes,
then test with game FOCUSED vs UNFOCUSED.
"""
import pymem, pymem.process, ctypes, ctypes.wintypes, struct, time

PAGE_EXECUTE_READWRITE = 0x40

pm = pymem.Pymem('MapleRoyals.exe')
print(f"Game PID: {pm.process_id}")

def find_func(dll, name):
    for mod in pymem.process.enum_process_module(pm.process_handle):
        if mod.name and dll.lower() in mod.name.lower():
            base = mod.lpBaseOfDll
            e_lfanew = pm.read_int(base + 0x3C)
            opt_hdr = base + e_lfanew + 24
            exp_rva = pm.read_int(opt_hdr + 96)
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
    return None

# Find GetAsyncKeyState
gaks = find_func("USER32.dll", "GetAsyncKeyState")
print(f"GetAsyncKeyState @ 0x{gaks:08X}")
orig_gaks = pm.read_bytes(gaks, 16)
print(f"  Before hook: {' '.join(f'{b:02X}' for b in orig_gaks[:8])}")

# Allocate
alloc = pm.allocate(512)
counter = alloc
hook_code = alloc + 8

pm.write_int(counter, 0)

# Make executable
old_prot = ctypes.wintypes.DWORD()
ctypes.windll.kernel32.VirtualProtectEx(
    pm.process_handle, hook_code, 256,
    PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))

# Build hook
sc = bytearray()
sc += b'\xFF\x05' + struct.pack('<I', counter)  # inc [counter]
sc += bytes(orig_gaks[:5])  # original 5 bytes
jmp_back = (gaks + 5) - (hook_code + len(sc) + 5)
sc += b'\xE9' + struct.pack('<i', jmp_back)

pm.write_bytes(hook_code, bytes(sc), len(sc))

# Patch GetAsyncKeyState
ctypes.windll.kernel32.VirtualProtectEx(
    pm.process_handle, gaks, 16,
    PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))

jmp_rel = hook_code - (gaks + 5)
patch = b'\xE9' + struct.pack('<i', jmp_rel)
pm.write_bytes(gaks, patch, 5)

# VERIFY the patch was applied
patched = pm.read_bytes(gaks, 8)
print(f"  After hook:  {' '.join(f'{b:02X}' for b in patched[:8])}")
print(f"  Patch applied: {patched[0] == 0xE9}")

# Read hook code back
hc = pm.read_bytes(hook_code, 16)
print(f"  Hook code:   {' '.join(f'{b:02X}' for b in hc[:16])}")

print("\n=== Phase 1: Game should be FOCUSED ===")
print(">>> CLICK THE GAME WINDOW NOW <<<")
print(">>> Press arrow keys! <<<")
print("Counting for 5 seconds...")
pm.write_int(counter, 0)
time.sleep(5)
c = pm.read_int(counter)
print(f"Calls when FOCUSED: {c}")

print("\n=== Phase 2: Game should be UNFOCUSED ===") 
print(">>> CLICK YOUR IDE NOW <<<")
print("Waiting 3 seconds...")
time.sleep(3)
pm.write_int(counter, 0)
print("Counting for 5 seconds...")
time.sleep(5)
c2 = pm.read_int(counter)
print(f"Calls when UNFOCUSED: {c2}")

# Unhook
pm.write_bytes(gaks, orig_gaks[:5], 5)
verify = pm.read_bytes(gaks, 8)
print(f"\n  Restored: {' '.join(f'{b:02X}' for b in verify[:8])}")

pm.close_process()
print("Done!")

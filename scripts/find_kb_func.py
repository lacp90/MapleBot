"""
Find exactly WHICH keyboard function the game uses.
Check GetAsyncKeyState, GetKeyState, GetKeyboardState in user32.dll,
and their forwarded destinations in win32u.dll / ntdll.dll.
"""
import pymem, pymem.process, ctypes, ctypes.wintypes, struct, time

PAGE_EXECUTE_READWRITE = 0x40

pm = pymem.Pymem('MapleRoyals.exe')
print(f"Game PID: {pm.process_id}")

def find_export(dll_name, func_name):
    """Find a function in the game's DLL."""
    for mod in pymem.process.enum_process_module(pm.process_handle):
        if mod.name and dll_name.lower() in mod.name.lower():
            base = mod.lpBaseOfDll
            try:
                e_lfanew = pm.read_int(base + 0x3C)
                opt_hdr = base + e_lfanew + 24
                export_rva = pm.read_int(opt_hdr + 96)
                if export_rva == 0: continue
                export_dir = base + export_rva
                num_names = pm.read_int(export_dir + 24)
                names_rva = pm.read_int(export_dir + 32)
                funcs_rva = pm.read_int(export_dir + 28)
                ords_rva = pm.read_int(export_dir + 36)
                for i in range(num_names):
                    name_rva = pm.read_int(base + names_rva + i * 4)
                    nb = pm.read_bytes(base + name_rva, len(func_name)+1)
                    ns = nb.split(b'\x00')[0].decode('ascii','ignore')
                    if ns == func_name:
                        ordinal = pm.read_short(base + ords_rva + i * 2)
                        func_rva = pm.read_int(base + funcs_rva + ordinal * 4)
                        return base + func_rva
            except: pass
    return None

# Test EACH keyboard function
targets = [
    ("USER32.dll", "GetAsyncKeyState"),
    ("USER32.dll", "GetKeyState"),
    ("USER32.dll", "GetKeyboardState"),
    ("win32u.dll", "NtUserGetAsyncKeyState"),
    ("win32u.dll", "NtUserGetKeyState"),
    ("win32u.dll", "NtUserGetKeyboardState"),
]

# Allocate counter space
alloc = pm.allocate(256)
pm.write_bytes(alloc, b'\x00' * 256, 256)

# Hook code space
hook_base = pm.allocate(4096)
old_protect = ctypes.wintypes.DWORD()
ctypes.windll.kernel32.VirtualProtectEx(
    pm.process_handle, hook_base, 4096,
    PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)
)

originals = {}
hook_idx = 0

for dll, func in targets:
    addr = find_export(dll, func)
    if not addr:
        print(f"  {dll}:{func} — NOT FOUND")
        continue
    
    # Read original bytes
    orig = pm.read_bytes(addr, 16)
    first_hex = ' '.join(f'{b:02X}' for b in orig[:8])
    print(f"  {dll}:{func} @ 0x{addr:08X} — {first_hex}")
    
    # Check if function is just a JMP (forwarded)
    if orig[0] == 0xE9:
        rel = struct.unpack('<i', orig[1:5])[0]
        target = addr + 5 + rel
        print(f"    -> Forwarded to 0x{target:08X}")
    elif orig[0] == 0xFF and orig[1] == 0x25:
        # jmp [addr] — indirect
        ind_addr = struct.unpack('<I', orig[2:6])[0]
        print(f"    -> Indirect JMP via [0x{ind_addr:08X}]")
    
    # Hook it with counter
    counter = alloc + hook_idx * 4
    hook_addr = hook_base + hook_idx * 32
    
    sc = bytearray()
    sc += b'\xFF\x05' + struct.pack('<I', counter)  # inc [counter]
    sc += bytes(orig[:5])  # original bytes
    jmp_back = (addr + 5) - (hook_addr + len(sc) + 5)
    sc += b'\xE9' + struct.pack('<i', jmp_back)
    
    pm.write_bytes(hook_addr, bytes(sc), len(sc))
    
    ctypes.windll.kernel32.VirtualProtectEx(
        pm.process_handle, addr, 16,
        PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)
    )
    jmp_rel = hook_addr - (addr + 5)
    pm.write_bytes(addr, b'\xE9' + struct.pack('<i', jmp_rel), 5)
    
    originals[addr] = (orig[:5], dll, func, counter)
    hook_idx += 1

print(f"\nHooked {hook_idx} functions. Counting for 3 seconds...")
time.sleep(3)

print("\nResults:")
found_any = False
for addr, (orig, dll, func, counter) in originals.items():
    count = pm.read_int(counter)
    if count > 0:
        print(f"  ✅ {dll}:{func} — {count} calls ({count/3:.0f}/sec)")
        found_any = True
    else:
        print(f"  ❌ {dll}:{func} — 0 calls")

if not found_any:
    print("\n!!! None of these functions are being called!")
    print("The game uses something ELSE for keyboard input.")

# Unhook
for addr, (orig, dll, func, counter) in originals.items():
    pm.write_bytes(addr, orig, 5)

pm.close_process()
print("\nDone!")

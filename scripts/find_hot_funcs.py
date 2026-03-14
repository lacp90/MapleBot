"""
Scan game memory for ALL GetDeviceState-like functions in dinput8.dll,
hook each one with a diagnostic counter, and see which one gets called.
"""
import pymem, pymem.process, ctypes, ctypes.wintypes, struct, time

PAGE_EXECUTE_READWRITE = 0x40

pm = pymem.Pymem('MapleRoyals.exe')
print(f"Game PID: {pm.process_id}")

# Find dinput8.dll
dinput8_base = None
dinput8_size = 0
for mod in pymem.process.enum_process_module(pm.process_handle):
    if mod.name and 'dinput8' in mod.name.lower():
        dinput8_base = mod.lpBaseOfDll
        dinput8_size = mod.SizeOfImage
        break

print(f"dinput8.dll: 0x{dinput8_base:08X} - 0x{dinput8_base + dinput8_size:08X}")

# Read the .text section of dinput8.dll and find all function prologues
# that match 8B FF 55 8B EC (mov edi,edi; push ebp; mov ebp,esp)
e_lfanew = pm.read_int(dinput8_base + 0x3C)
pe_base = dinput8_base + e_lfanew
num_sections = pm.read_short(pe_base + 6)
opt_hdr_size = pm.read_short(pe_base + 20)
section_start = pe_base + 24 + opt_hdr_size

text_start = 0
text_size = 0
for i in range(num_sections):
    sec_addr = section_start + i * 40
    sec_name = pm.read_bytes(sec_addr, 8).split(b'\x00')[0].decode('ascii', errors='ignore')
    sec_rva = pm.read_int(sec_addr + 12)
    sec_vsize = pm.read_int(sec_addr + 8)
    sec_chars = pm.read_int(sec_addr + 36)
    if sec_chars & 0x20000000:  # Execute
        text_start = dinput8_base + sec_rva
        text_size = sec_vsize
        print(f"Code section: {sec_name} @ 0x{text_start:08X}, {text_size} bytes")
        break

# Read entire code section
code = pm.read_bytes(text_start, text_size)

# Find all function prologues with 8B FF 55 8B EC
prologue = b'\x8B\xFF\x55\x8B\xEC'
functions = []
pos = 0
while pos < len(code) - 5:
    idx = code.find(prologue, pos)
    if idx == -1:
        break
    func_addr = text_start + idx
    functions.append(func_addr)
    pos = idx + 1

print(f"Found {len(functions)} functions with standard prologue in dinput8.dll")

# Allocate memory for counters (one DWORD per function)
alloc = pm.allocate(4096)
print(f"Counter array @ 0x{alloc:08X}")

# Zero counters
pm.write_bytes(alloc, b'\x00' * (len(functions) * 4), len(functions) * 4)

# Allocate code region for all hooks
hook_code_base = pm.allocate(len(functions) * 32 + 256)
old_protect = ctypes.wintypes.DWORD()
ctypes.windll.kernel32.VirtualProtectEx(
    pm.process_handle, hook_code_base, len(functions) * 32 + 256,
    PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)
)

# For each function, install a hook that increments its counter
originals = {}
for i, func_addr in enumerate(functions):
    counter_addr = alloc + i * 4
    hook_addr = hook_code_base + i * 32
    
    # Read original bytes
    orig = pm.read_bytes(func_addr, 8)
    originals[func_addr] = orig[:5]
    
    # Build mini hook: inc [counter]; original 5 bytes; jmp back
    sc = bytearray()
    sc += b'\xFF\x05' + struct.pack('<I', counter_addr)  # inc [counter]
    sc += orig[:5]  # original prologue
    jmp_back = (func_addr + 5) - (hook_addr + len(sc) + 5)
    sc += b'\xE9' + struct.pack('<i', jmp_back)  # jmp original+5
    
    pm.write_bytes(hook_addr, bytes(sc), len(sc))
    
    # Patch original function
    ctypes.windll.kernel32.VirtualProtectEx(
        pm.process_handle, func_addr, 8,
        PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)
    )
    jmp_to = hook_addr - (func_addr + 5)
    pm.write_bytes(func_addr, b'\xE9' + struct.pack('<i', jmp_to), 5)

print(f"Hooked {len(functions)} functions. Counting for 3 seconds...")
time.sleep(3)

# Read counters
print("\nResults:")
hot_functions = []
for i, func_addr in enumerate(functions):
    counter_addr = alloc + i * 4
    count = pm.read_int(counter_addr)
    if count > 0:
        hot_functions.append((func_addr, count))
        print(f"  0x{func_addr:08X}: {count} calls ({count/3:.0f}/sec)")

if not hot_functions:
    print("  NO functions called! DirectInput might not be used for keyboard.")

# Unhook all
for func_addr, orig in originals.items():
    try:
        pm.write_bytes(func_addr, orig, 5)
    except:
        pass

# Free memory
ctypes.windll.kernel32.VirtualFreeEx(pm.process_handle, alloc, 0, 0x8000)
ctypes.windll.kernel32.VirtualFreeEx(pm.process_handle, hook_code_base, 0, 0x8000)

pm.close_process()
print("\nAll hooks removed. Done!")

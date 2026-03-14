"""
Find the game's ACTUAL DirectInput keyboard device by scanning memory.
Hook its vtable entry for GetDeviceState (index 9).
"""
import pymem, pymem.process, ctypes, ctypes.wintypes, struct, time

PAGE_EXECUTE_READWRITE = 0x40

pm = pymem.Pymem('MapleRoyals.exe')
print(f"Game PID: {pm.process_id}")

# Strategy: Instead of hooking the function code, 
# we hook the VTABLE of the game's actual keyboard device.
# 
# The game calls: pKeyboardDevice->lpVtbl->GetDeviceState(pDevice, 256, buffer)
# If we replace the vtable[9] pointer with our function, we intercept the call.
#
# But first we need to FIND the game's keyboard device object.
#
# Alternative approach: Hook the DirectInput8Create function itself,
# or find ALL GetDeviceState implementations in dinput8.dll and hook them all.

# Let's find ALL functions in dinput8.dll that could be GetDeviceState
dinput8_base = None
dinput8_size = 0
for mod in pymem.process.enum_process_module(pm.process_handle):
    if mod.name and 'dinput8' in mod.name.lower():
        dinput8_base = mod.lpBaseOfDll
        dinput8_size = mod.SizeOfImage
        break

print(f"dinput8.dll: 0x{dinput8_base:08X}, size: {dinput8_size}")

# Read the entire dinput8.dll code section to find all function prologues
# that match the GetDeviceState pattern
e_lfanew = pm.read_int(dinput8_base + 0x3C)
pe_base = dinput8_base + e_lfanew

# Read section headers
num_sections = pm.read_short(pe_base + 6)
opt_hdr_size = pm.read_short(pe_base + 20)
section_start = pe_base + 24 + opt_hdr_size

print(f"\nSearching dinput8.dll sections for vtable patterns...")

# Read all vtable-like addresses from the .rdata section
for i in range(num_sections):
    sec_addr = section_start + i * 40
    sec_name = pm.read_bytes(sec_addr, 8).split(b'\x00')[0].decode('ascii', errors='ignore')
    sec_vsize = pm.read_int(sec_addr + 8)
    sec_rva = pm.read_int(sec_addr + 12)
    sec_raw_size = pm.read_int(sec_addr + 16)
    sec_raw_ptr = pm.read_int(sec_addr + 20)
    sec_chars = pm.read_int(sec_addr + 36)
    
    is_code = sec_chars & 0x20000000  # IMAGE_SCN_MEM_EXECUTE
    is_data = sec_chars & 0x40000000  # IMAGE_SCN_MEM_READ
    
    print(f"  {sec_name}: RVA=0x{sec_rva:08X} Size=0x{sec_vsize:08X} {'CODE' if is_code else 'DATA'}")

# Alternative: scan the game memory for pointers into dinput8.dll
# that look like vtable entries
print(f"\nLooking for DirectInput vtable entries in game's MapleRoyals.exe data...")

# Read MapleRoyals.exe base
maple_base = 0x00400000  # Standard load address
maple_size = 0

for mod in pymem.process.enum_process_module(pm.process_handle):
    if mod.name and 'MapleRoyals' in mod.name:
        maple_base = mod.lpBaseOfDll
        maple_size = mod.SizeOfImage
        break

print(f"MapleRoyals.exe: 0x{maple_base:08X}, size: 0x{maple_size:08X}")

# Scan .data and .rdata sections of MapleRoyals.exe for pointers into dinput8.dll
# These could be vtable entries or stored function pointers
e_lfanew2 = pm.read_int(maple_base + 0x3C)
pe_base2 = maple_base + e_lfanew2
num_sections2 = pm.read_short(pe_base2 + 6)
opt_hdr_size2 = pm.read_short(pe_base2 + 20)
section_start2 = pe_base2 + 24 + opt_hdr_size2

dinput_ptrs = []

for i in range(num_sections2):
    sec_addr = section_start2 + i * 40
    sec_name = pm.read_bytes(sec_addr, 8).split(b'\x00')[0].decode('ascii', errors='ignore')
    sec_vsize = pm.read_int(sec_addr + 8)
    sec_rva = pm.read_int(sec_addr + 12)
    sec_chars = pm.read_int(sec_addr + 36)
    
    is_writable = sec_chars & 0x80000000  # IMAGE_SCN_MEM_WRITE (data section)
    
    if not is_writable:
        continue
    
    print(f"\n  Scanning {sec_name} (0x{sec_rva:08X}, {sec_vsize} bytes)...")
    
    # Read in chunks
    sec_start = maple_base + sec_rva
    chunk_size = min(sec_vsize, 0x100000)  # Max 1MB chunks
    
    try:
        data = pm.read_bytes(sec_start, chunk_size)
    except Exception as e:
        print(f"    Error reading: {e}")
        continue
    
    # Scan for 4-byte values that point into dinput8.dll
    dinput_end = dinput8_base + dinput8_size
    for offset in range(0, len(data) - 4, 4):
        val = struct.unpack_from('<I', data, offset)[0]
        if dinput8_base <= val < dinput_end:
            addr = sec_start + offset
            dinput_ptrs.append((addr, val))

print(f"\nFound {len(dinput_ptrs)} pointers to dinput8.dll in game data:")
for addr, val in dinput_ptrs[:20]:
    print(f"  [0x{addr:08X}] -> 0x{val:08X}")

# Also scan the heap (allocated memory) for vtable pointers
# The device object is most likely on the heap
print(f"\nScanning heap for DirectInput device objects...")
# Use VirtualQueryEx to find committed memory regions
MEMORY_BASIC_INFORMATION = ctypes.c_byte * 28  # 32-bit
class MBI(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', ctypes.wintypes.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', ctypes.wintypes.DWORD),
        ('Protect', ctypes.wintypes.DWORD),
        ('Type', ctypes.wintypes.DWORD),
    ]

MEM_COMMIT = 0x1000
PAGE_READWRITE_VAL = 0x04
heap_ptrs = []
addr = 0
count = 0

while addr < 0x7FFF0000 and count < 1000:
    mbi = MBI()
    ret = ctypes.windll.kernel32.VirtualQueryEx(
        pm.process_handle, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)
    )
    if ret == 0:
        break
    
    if mbi.State == MEM_COMMIT and mbi.Protect in (0x04, 0x02, 0x40):
        size = min(mbi.RegionSize, 0x100000)
        if size > 0 and size < 0x1000000:
            try:
                data = pm.read_bytes(mbi.BaseAddress, size)
                dinput_end = dinput8_base + dinput8_size
                for offset in range(0, len(data) - 40, 4):
                    val = struct.unpack_from('<I', data, offset)[0]
                    if dinput8_base <= val < dinput_end:
                        # This could be a vtable pointer!
                        # Check if it looks like a vtable (multiple consecutive dinput pointers)
                        consecutive = 0
                        for j in range(1, 10):
                            next_val = struct.unpack_from('<I', data, offset + j*4)[0]
                            if dinput8_base <= next_val < dinput_end:
                                consecutive += 1
                        if consecutive >= 3:
                            ptr_addr = mbi.BaseAddress + offset
                            heap_ptrs.append((ptr_addr, val, consecutive))
            except Exception:
                pass
    
    addr = mbi.BaseAddress + mbi.RegionSize
    count += 1

print(f"Found {len(heap_ptrs)} vtable-like structures pointing to dinput8.dll:")
for addr, val, consec in sorted(heap_ptrs, key=lambda x: -x[2])[:10]:
    print(f"  [0x{addr:08X}] -> 0x{val:08X} ({consec+1} consecutive dinput ptrs)")
    # Print the vtable entries
    for k in range(min(consec+1, 12)):
        entry = pm.read_int(addr + k*4)
        label = ""
        if k == 9:
            label = " <-- GetDeviceState (index 9)"
        elif k == 10:
            label = " <-- GetDeviceData (index 10)"
        print(f"    [{k}] 0x{entry:08X}{label}")

pm.close_process()
print("\nDone!")

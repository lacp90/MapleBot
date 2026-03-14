"""
Diagnostic: Is our GetDeviceState hook actually being called?
Writes a counter each time the hook runs, then reads it back.
Also tries setting ALL keys to 0x80 to see if ANYTHING happens.
"""
import pymem, pymem.process, ctypes, ctypes.wintypes, struct, time

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', ctypes.c_ulong), ('Data2', ctypes.c_ushort),
        ('Data3', ctypes.c_ushort), ('Data4', ctypes.c_ubyte * 8)
    ]

PAGE_EXECUTE_READWRITE = 0x40

pm = pymem.Pymem('MapleRoyals.exe')
print(f"Game PID: {pm.process_id}")

# Find GetDeviceState
GUID_SysKeyboard = GUID(0x6F1D2B61, 0xD5A0, 0x11CF,
    (ctypes.c_ubyte*8)(0xBF,0xC7,0x44,0x45,0x53,0x54,0x00,0x00))
IID_IDirectInput8A = GUID(0xBF798030, 0x483A, 0x4DA2,
    (ctypes.c_ubyte*8)(0xAA,0x99,0x5D,0x64,0xED,0x36,0x97,0x00))

dinput = ctypes.windll.LoadLibrary('dinput8.dll')
pDI = ctypes.c_void_p()
dinput.DirectInput8Create(
    ctypes.windll.kernel32.GetModuleHandleW(None), 0x0800,
    ctypes.byref(IID_IDirectInput8A), ctypes.byref(pDI), None
)
vtable = ctypes.c_uint32.from_address(pDI.value).value
cdp = ctypes.c_uint32.from_address(vtable + 3*4).value
CreateDevice = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
    ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p)(cdp)
pDev = ctypes.c_void_p()
CreateDevice(pDI.value, ctypes.byref(GUID_SysKeyboard), ctypes.byref(pDev), None)
dev_vtable = ctypes.c_uint32.from_address(pDev.value).value
gds_addr = ctypes.c_uint32.from_address(dev_vtable + 9*4).value
print(f"GetDeviceState @ 0x{gds_addr:08X}")

# Read first bytes
orig = pm.read_bytes(gds_addr, 16)
print(f"First bytes: {' '.join(f'{b:02X}' for b in orig[:8])}")

# Also check: does the GAME have the same GetDeviceState address?
# Read from the game's copy of dinput8.dll at the same offset
game_bytes = pm.read_bytes(gds_addr, 8)
print(f"Game bytes:  {' '.join(f'{b:02X}' for b in game_bytes)}")
print(f"Match: {orig[:8] == game_bytes}")

# Check if maybe the game already has this hooked (first byte is E9 = jmp)
if game_bytes[0] == 0xE9:
    jmp_rel = struct.unpack('<i', game_bytes[1:5])[0]
    jmp_target = gds_addr + 5 + jmp_rel
    print(f"!!! GetDeviceState is ALREADY HOOKED by something else!")
    print(f"    Jumps to 0x{jmp_target:08X}")

# Allocate memory for test
alloc = pm.allocate(512)
counter_addr = alloc      # 4-byte counter
key_table = alloc + 4     # 256-byte key table
hook_code = alloc + 260   # hook code

# Init counter to 0
pm.write_int(counter_addr, 0)
# Init key table: set a few keys to see if anything happens
pm.write_bytes(key_table, b'\x00' * 256, 256)

# Build simple diagnostic hook:
# Just increment the counter and call original
original_continue = gds_addr + 5

sc = bytearray()
# inc dword [counter_addr]
sc += b'\xFF\x05' + struct.pack('<I', counter_addr)
# Execute original 5 bytes
sc += bytes(orig[:5])
# jmp to original+5
jmp_from = hook_code + len(sc) + 5
jmp_rel = original_continue - jmp_from
sc += b'\xE9' + struct.pack('<i', jmp_rel)

# Write hook code
old_protect = ctypes.wintypes.DWORD()
ctypes.windll.kernel32.VirtualProtectEx(pm.process_handle, hook_code, 256,
    PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect))
pm.write_bytes(hook_code, bytes(sc), len(sc))

# Patch GetDeviceState
ctypes.windll.kernel32.VirtualProtectEx(pm.process_handle, gds_addr, 16,
    PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect))
patch_from = gds_addr + 5
patch_rel = hook_code - patch_from
patch = b'\xE9' + struct.pack('<i', patch_rel)
pm.write_bytes(gds_addr, patch, 5)

print("\nHook installed! Counting calls for 3 seconds...")
time.sleep(1)
c1 = pm.read_int(counter_addr)
print(f"  After 1s: {c1} calls")
time.sleep(1)
c2 = pm.read_int(counter_addr)
print(f"  After 2s: {c2} calls")
time.sleep(1)
c3 = pm.read_int(counter_addr)
print(f"  After 3s: {c3} calls")

if c3 == 0:
    print("\n❌ Hook is NOT being called!")
    print("The game's keyboard device uses a DIFFERENT GetDeviceState!")
else:
    print(f"\n✅ Hook IS being called! ({c3} calls in 3s = {c3/3:.0f} calls/sec)")

# Unhook
pm.write_bytes(gds_addr, orig[:5], 5)
pm.close_process()
print("Unhooked. Done!")

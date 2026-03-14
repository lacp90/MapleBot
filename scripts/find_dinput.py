"""Find DirectInput GetDeviceState address for hooking."""
import pymem, pymem.process, ctypes, struct

pm = pymem.Pymem('MapleRoyals.exe')
print(f"Game PID: {pm.process_id}")

# Load dinput8.dll in our own 32-bit process
dinput = ctypes.windll.LoadLibrary('dinput8.dll')

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', ctypes.c_ulong),
        ('Data2', ctypes.c_ushort),
        ('Data3', ctypes.c_ushort),
        ('Data4', ctypes.c_ubyte * 8)
    ]

GUID_SysKeyboard = GUID(0x6F1D2B61, 0xD5A0, 0x11CF,
    (ctypes.c_ubyte * 8)(0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00))

IID_IDirectInput8A = GUID(0xBF798030, 0x483A, 0x4DA2,
    (ctypes.c_ubyte * 8)(0xAA, 0x99, 0x5D, 0x64, 0xED, 0x36, 0x97, 0x00))

# Create DirectInput8 object
pDI = ctypes.c_void_p()
hr = dinput.DirectInput8Create(
    ctypes.windll.kernel32.GetModuleHandleW(None),
    0x0800,  # DIRECTINPUT_VERSION
    ctypes.byref(IID_IDirectInput8A),
    ctypes.byref(pDI),
    None
)
print(f"DirectInput8Create: hr=0x{hr & 0xFFFFFFFF:08X}, pDI={pDI.value}")

if hr != 0 or not pDI.value:
    print("Failed to create DirectInput!")
    pm.close_process()
    exit(1)

# Read vtable pointer
vtable = ctypes.c_uint32.from_address(pDI.value).value
print(f"IDirectInput8 vtable @ 0x{vtable:08X}")

# CreateDevice is vtable[3]
create_device_ptr = ctypes.c_uint32.from_address(vtable + 3*4).value

# Call CreateDevice using function pointer
CreateDeviceFunc = ctypes.WINFUNCTYPE(
    ctypes.c_long,       # return HRESULT
    ctypes.c_void_p,     # this
    ctypes.POINTER(GUID),  # rguid
    ctypes.POINTER(ctypes.c_void_p),  # lplpDirectInputDevice
    ctypes.c_void_p      # pUnkOuter
)
CreateDevice = CreateDeviceFunc(create_device_ptr)

pDevice = ctypes.c_void_p()
hr2 = CreateDevice(pDI.value, ctypes.byref(GUID_SysKeyboard), ctypes.byref(pDevice), None)
print(f"CreateDevice: hr=0x{hr2 & 0xFFFFFFFF:08X}, pDevice={pDevice.value}")

if hr2 != 0 or not pDevice.value:
    print("Failed to create keyboard device!")
    pm.close_process()
    exit(1)

# Read device vtable
dev_vtable = ctypes.c_uint32.from_address(pDevice.value).value
print(f"IDirectInputDevice8 vtable @ 0x{dev_vtable:08X}")

# GetDeviceState is index 9
gds_addr = ctypes.c_uint32.from_address(dev_vtable + 9*4).value
print(f"GetDeviceState @ 0x{gds_addr:08X}")

# Read first bytes
first = (ctypes.c_ubyte * 16)()
ctypes.memmove(first, gds_addr, 16)
hex_str = ' '.join(f'{b:02X}' for b in first)
print(f"First 16 bytes: {hex_str}")

# The KEY insight: since both our process and the game load dinput8.dll
# at the same base (0x68340000), the GetDeviceState function address
# is the SAME in both processes. We can hook it in the game!
print()
print(f"=== HOOK TARGET: GetDeviceState @ 0x{gds_addr:08X} ===")
print("This address is valid in the game process too (same DLL base)")

# Clean up
ReleaseFunc = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
Release = ReleaseFunc(ctypes.c_uint32.from_address(dev_vtable + 2*4).value)
Release(pDevice.value)
Release2 = ReleaseFunc(ctypes.c_uint32.from_address(vtable + 2*4).value)
Release2(pDI.value)

pm.close_process()
print("Done!")

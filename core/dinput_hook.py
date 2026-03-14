"""
DirectInput8 GetDeviceState hook for background keyboard control.
Hooks the game's DirectInput keyboard device to inject fake key presses.

How GetDeviceState works:
  HRESULT GetDeviceState(DWORD cbData, LPVOID lpvData)
  - cbData = 256 (size of keyboard state buffer)
  - lpvData = pointer to 256-byte buffer
  - Each byte: 0x80 = pressed, 0x00 = not pressed
  - Index = DirectInput key code (DIK_LEFT = 0xCB, DIK_RIGHT = 0xCD, etc.)

Our hook:
  1. Call original GetDeviceState (fills the buffer with real key states)
  2. Check our control table for keys we want to inject
  3. OR our fake key states into the buffer
  4. Return
"""
import ctypes
import ctypes.wintypes
import struct
import time
import pymem
import pymem.process

# DirectInput key codes (DIK_ constants)
DIK_LEFT   = 0xCB
DIK_RIGHT  = 0xCD
DIK_UP     = 0xC8
DIK_DOWN   = 0xD0
DIK_LALT   = 0x38  # Left Alt (jump in MapleStory)

CONTROLLED_KEYS = {DIK_LEFT, DIK_RIGHT, DIK_UP, DIK_DOWN, DIK_LALT}

PAGE_EXECUTE_READWRITE = 0x40


class DirectInputHook:
    """
    Hooks IDirectInputDevice8::GetDeviceState to inject fake key presses.
    Works completely in background — no focus needed.
    """
    
    def __init__(self, process_name="MapleRoyals.exe"):
        self.pm = None
        self.process_name = process_name
        self.key_table_addr = 0     # Our key state table in game memory
        self.hook_addr = 0          # Our hook code in game memory
        self.gds_addr = 0           # Original GetDeviceState address
        self.original_bytes = b""   # Saved bytes for unhooking
        self.hooked = False
    
    def attach(self):
        """Attach to the game process."""
        try:
            self.pm = pymem.Pymem(self.process_name)
            print(f"[DInput] Attached to {self.process_name} (PID: {self.pm.process_id})")
            return True
        except pymem.exception.ProcessNotFound:
            for name in ["MapleRoyals.exe", "MapleStory.exe"]:
                try:
                    self.pm = pymem.Pymem(name)
                    self.process_name = name
                    print(f"[DInput] Attached to {name} (PID: {self.pm.process_id})")
                    return True
                except pymem.exception.ProcessNotFound:
                    continue
            print("[DInput] Could not find MapleStory process!")
            return False
    
    def _find_getdevicestate(self):
        """Find GetDeviceState address by creating a temp DirectInput device."""
        
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
        
        dinput = ctypes.windll.LoadLibrary('dinput8.dll')
        
        pDI = ctypes.c_void_p()
        hr = dinput.DirectInput8Create(
            ctypes.windll.kernel32.GetModuleHandleW(None),
            0x0800,
            ctypes.byref(IID_IDirectInput8A),
            ctypes.byref(pDI),
            None
        )
        
        if hr != 0 or not pDI.value:
            print(f"[DInput] DirectInput8Create failed: 0x{hr & 0xFFFFFFFF:08X}")
            return None
        
        vtable = ctypes.c_uint32.from_address(pDI.value).value
        create_device_ptr = ctypes.c_uint32.from_address(vtable + 3*4).value
        
        CreateDeviceFunc = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p,
            ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p
        )
        CreateDevice = CreateDeviceFunc(create_device_ptr)
        
        pDevice = ctypes.c_void_p()
        hr2 = CreateDevice(pDI.value, ctypes.byref(GUID_SysKeyboard), ctypes.byref(pDevice), None)
        
        if hr2 != 0 or not pDevice.value:
            print(f"[DInput] CreateDevice failed: 0x{hr2 & 0xFFFFFFFF:08X}")
            return None
        
        dev_vtable = ctypes.c_uint32.from_address(pDevice.value).value
        gds_addr = ctypes.c_uint32.from_address(dev_vtable + 9*4).value
        
        # Clean up our temp objects
        ReleaseFunc = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        Release1 = ReleaseFunc(ctypes.c_uint32.from_address(dev_vtable + 2*4).value)
        Release1(pDevice.value)
        Release2 = ReleaseFunc(ctypes.c_uint32.from_address(vtable + 2*4).value)
        Release2(pDI.value)
        
        return gds_addr
    
    def install_hook(self):
        """Install the GetDeviceState hook."""
        if not self.pm:
            raise RuntimeError("Not attached")
        
        # 1. Find GetDeviceState
        self.gds_addr = self._find_getdevicestate()
        if not self.gds_addr:
            print("[DInput] Failed to find GetDeviceState!")
            return False
        print(f"[DInput] GetDeviceState @ 0x{self.gds_addr:08X}")
        
        # Read first bytes
        self.original_bytes = self.pm.read_bytes(self.gds_addr, 16)
        first_hex = ' '.join(f'{b:02X}' for b in self.original_bytes[:8])
        print(f"[DInput] Original bytes: {first_hex}")
        
        # 2. Allocate memory: 256 bytes key table + 512 bytes code
        alloc_size = 1024
        self.key_table_addr = self.pm.allocate(alloc_size)
        self.hook_addr = self.key_table_addr + 256
        print(f"[DInput] Key table @ 0x{self.key_table_addr:08X}")
        print(f"[DInput] Hook code @ 0x{self.hook_addr:08X}")
        
        # Init key table to zeros
        self.pm.write_bytes(self.key_table_addr, b'\x00' * 256, 256)
        
        # 3. Build hook shellcode
        # GetDeviceState(this, cbData, lpvData) — __stdcall, 3 args (12 bytes)
        # Actually it's COM __stdcall: this + 2 params = 3 * 4 = 12 bytes on stack
        #
        # Our hook:
        #   push ebp
        #   mov ebp, esp
        #   ; Save registers
        #   pushad
        #   
        #   ; Call original GetDeviceState
        #   push [ebp+16]    ; lpvData
        #   push [ebp+12]    ; cbData
        #   push [ebp+8]     ; this
        #   ; Execute original prologue bytes + jump to rest
        #   <original 5 bytes>
        #   call original+5
        #   
        #   ; After original returns, modify the buffer
        #   ; lpvData = [ebp+16]
        #   mov edi, [ebp+16]
        #   ; OR our key states into the buffer
        #   ; For each controlled key, check our table
        
        # Actually, simpler approach: hook by modifying the RETURN of GetDeviceState
        # After GetDeviceState fills the buffer, we modify specific bytes
        #
        # SIMPLEST APPROACH: Instead of complex code hooking, let's use a POLLING approach
        # We DON'T hook GetDeviceState at all.
        # Instead, we continuously write our desired key states into the DirectInput
        # buffer AFTER the game reads it. But we don't know where the buffer is...
        #
        # OK let's do the hook properly.
        # GetDeviceState prologue is typically: mov edi,edi / push ebp / mov ebp,esp
        
        original_continue = self.gds_addr + 5
        
        shellcode = bytearray()
        
        # Our hooked GetDeviceState:
        # 1. Execute original prologue (5 bytes)
        # 2. JMP to original+5 (continue original function)
        # ... but we need to modify the RESULT after it returns
        
        # Better approach: WRAPPER function
        # push ebp
        # mov ebp, esp
        # 
        # ; Call original GetDeviceState by executing its prologue then jumping
        # ; We need to CALL the original, not JMP, so we get control back
        #
        # push [ebp+16]     ; lpvData
        # push [ebp+12]     ; cbData  
        # push [ebp+8]      ; this
        # call trampoline   ; calls original GetDeviceState
        # ; eax = HRESULT
        # 
        # ; If failed, just return
        # test eax, eax
        # jnz .return
        #
        # ; Modify the buffer: OR our key states in
        # mov edi, [ebp+16]  ; lpvData pointer
        # mov esi, key_table_addr
        # ; For DIK_LEFT (0xCB): if key_table[0xCB] != 0, set buffer[0xCB] = 0x80
        # (repeat for each key)
        #
        # .return:
        # pop ebp
        # ret 12  ; stdcall, clean 3 args (this + cbData + lpvData)
        #
        # trampoline:
        #   <original 5 bytes>
        #   jmp original+5

        # --- Build the trampoline first (at the end of our code region) ---
        trampoline_offset = 200  # relative to hook_addr
        trampoline_addr = self.hook_addr + trampoline_offset
        
        tramp = bytearray()
        tramp += bytes(self.original_bytes[:5])  # Original prologue
        # JMP to original+5
        jmp_from = trampoline_addr + len(tramp) + 5
        jmp_rel = original_continue - jmp_from
        tramp += b'\xE9' + struct.pack('<i', jmp_rel)
        
        # --- Build main hook ---
        sc = bytearray()
        
        # push ebp; mov ebp, esp
        sc += b'\x55'          # push ebp
        sc += b'\x89\xE5'      # mov ebp, esp
        
        # push [ebp+16] (lpvData)
        sc += b'\xFF\x75\x10'
        # push [ebp+12] (cbData)  
        sc += b'\xFF\x75\x0C'
        # push [ebp+8] (this)
        sc += b'\xFF\x75\x08'
        
        # call trampoline (which calls original GetDeviceState)
        call_from = self.hook_addr + len(sc) + 5
        call_rel = trampoline_addr - call_from
        sc += b'\xE8' + struct.pack('<i', call_rel)
        
        # eax = HRESULT. If not 0 (failed), skip modification
        sc += b'\x85\xC0'      # test eax, eax
        sc += b'\x75'          # jnz .return
        jnz_pos = len(sc)
        sc += b'\x00'          # placeholder
        
        # Save eax (HRESULT = 0 = success)
        sc += b'\x50'          # push eax
        
        # edi = lpvData (the keyboard state buffer)
        sc += b'\x8B\x7D\x10'  # mov edi, [ebp+16]
        
        # For each controlled key, check our table and OR 0x80 into buffer
        for dik in [DIK_LEFT, DIK_RIGHT, DIK_UP, DIK_DOWN, DIK_LALT]:
            # movzx eax, byte [key_table + dik]
            sc += b'\x0F\xB6\x05'  # movzx eax, byte [imm32]
            sc += struct.pack('<I', self.key_table_addr + dik)
            # test al, al
            sc += b'\x84\xC0'
            # jz skip
            sc += b'\x74\x03'  # jz +3
            # or byte [edi + dik], 0x80
            sc += b'\x80\x4F' + bytes([dik])  # or byte [edi+dik], ... wait this is wrong
            # Actually: or byte [edi+dik], 0x80
            # Encoding: 80 0C 3F offset 80  -- no
            # Let's use: mov byte [edi+dik], 0x80
            
        # The above encoding is wrong. Let me redo it properly.
        sc = bytearray()
        
        # push ebp; mov ebp, esp; push esi; push edi; push ebx
        sc += b'\x55'          # push ebp
        sc += b'\x89\xE5'      # mov ebp, esp
        sc += b'\x56'          # push esi
        sc += b'\x57'          # push edi
        sc += b'\x53'          # push ebx
        
        # Call original GetDeviceState via trampoline
        # push [ebp+16] (lpvData)
        sc += b'\xFF\x75\x10'
        # push [ebp+12] (cbData)
        sc += b'\xFF\x75\x0C'
        # push [ebp+8] (this)
        sc += b'\xFF\x75\x08'
        # call trampoline
        call_from = self.hook_addr + len(sc) + 5
        call_rel = trampoline_addr - call_from
        sc += b'\xE8' + struct.pack('<i', call_rel)
        
        # Save result
        sc += b'\x89\xC3'      # mov ebx, eax (save HRESULT)
        
        # Check if succeeded
        sc += b'\x85\xC0'      # test eax, eax
        sc += b'\x75'          # jnz .return
        jnz_pos = len(sc)
        sc += b'\x00'          # placeholder
        
        # edi = lpvData
        sc += b'\x8B\x7D\x10'  # mov edi, [ebp+16]
        
        # For each key: check table, set buffer byte
        for dik in sorted(CONTROLLED_KEYS):
            # cmp byte [key_table + dik], 0
            sc += b'\x80\x3D'      # cmp byte [imm32], imm8
            sc += struct.pack('<I', self.key_table_addr + dik)
            sc += b'\x00'          # compare with 0
            # je skip (skip 3 bytes: the mov instruction)
            sc += b'\x74\x03'      # je +3
            # mov byte [edi + dik], 0x80
            sc += b'\xC6\x47'      # mov byte [edi+imm8], imm8
            sc += bytes([dik])     # offset
            # Wait, C6 47 xx yy = mov byte [edi+xx], yy — that's 4 bytes, not 3
            # Fix: je +4 instead of +3
        
        # Redo the key injection loop with correct sizes
        sc_keys_start = len(sc) - len(CONTROLLED_KEYS) * 12  # approximate, redo from scratch
        
        # Actually let me just rebuild from the key table check cleanly
        sc = bytearray()
        
        # Prologue
        sc += b'\x55'           # push ebp
        sc += b'\x89\xE5'       # mov ebp, esp
        sc += b'\x57'           # push edi
        
        # Call original: push args, call trampoline
        sc += b'\xFF\x75\x10'   # push [ebp+16]  lpvData
        sc += b'\xFF\x75\x0C'   # push [ebp+12]  cbData
        sc += b'\xFF\x75\x08'   # push [ebp+8]   this
        call_from = self.hook_addr + len(sc) + 5
        call_rel = trampoline_addr - call_from
        sc += b'\xE8' + struct.pack('<i', call_rel)  # call trampoline
        
        # Check result
        sc += b'\x85\xC0'       # test eax, eax
        jnz_pos = len(sc) + 1   # position of the offset byte
        sc += b'\x75\x00'       # jnz .return (placeholder)
        
        # edi = lpvData buffer
        sc += b'\x8B\x7D\x10'   # mov edi, [ebp+16]
        
        # Inject each key
        for dik in sorted(CONTROLLED_KEYS):
            # cmp byte [key_table + dik], 0
            sc += b'\x80\x3D'
            sc += struct.pack('<I', self.key_table_addr + dik)
            sc += b'\x00'
            # je skip (skip the mov which is 4 bytes: C6 87 dword 80)
            sc += b'\x74\x07'    # je +7
            # mov byte [edi + dik], 0x80
            sc += b'\xC6\x87'    # mov byte [edi + imm32], imm8
            sc += struct.pack('<I', dik)
            sc += b'\x80'        # value = 0x80 (key pressed)
        
        # .return:
        return_offset = len(sc)
        # Fix jnz offset
        sc[jnz_pos] = return_offset - (jnz_pos + 1)
        
        # Epilogue
        sc += b'\x5F'           # pop edi
        sc += b'\x5D'           # pop ebp
        sc += b'\xC2\x0C\x00'   # ret 12 (stdcall, 3 args * 4)
        
        # 4. Write shellcode and trampoline to game memory
        old_protect = ctypes.wintypes.DWORD()
        ctypes.windll.kernel32.VirtualProtectEx(
            self.pm.process_handle,
            self.hook_addr,
            512,
            PAGE_EXECUTE_READWRITE,
            ctypes.byref(old_protect)
        )
        
        # Write main hook
        self.pm.write_bytes(self.hook_addr, bytes(sc), len(sc))
        # Write trampoline
        self.pm.write_bytes(trampoline_addr, bytes(tramp), len(tramp))
        
        print(f"[DInput] Hook code: {len(sc)} bytes, trampoline: {len(tramp)} bytes")
        
        # 5. Patch GetDeviceState to jump to our hook
        jmp_to = self.hook_addr
        jmp_from_gds = self.gds_addr + 5
        jmp_rel = jmp_to - jmp_from_gds
        patch = b'\xE9' + struct.pack('<i', jmp_rel)
        
        ctypes.windll.kernel32.VirtualProtectEx(
            self.pm.process_handle,
            self.gds_addr,
            16,
            PAGE_EXECUTE_READWRITE,
            ctypes.byref(old_protect)
        )
        self.pm.write_bytes(self.gds_addr, patch, 5)
        
        self.hooked = True
        print("[DInput] ✅ GetDeviceState hooked! Background movement enabled.")
        return True
    
    def press_key(self, dik_code):
        """Press a DirectInput key."""
        if self.hooked:
            self.pm.write_bytes(self.key_table_addr + dik_code, b'\x01', 1)
    
    def release_key(self, dik_code):
        """Release a DirectInput key."""
        if self.hooked:
            self.pm.write_bytes(self.key_table_addr + dik_code, b'\x00', 1)
    
    def hold_key(self, dik_code, duration):
        """Hold a key for a duration."""
        self.press_key(dik_code)
        time.sleep(duration)
        self.release_key(dik_code)
    
    def walk_right(self, duration=1.0):
        self.hold_key(DIK_RIGHT, duration)
    
    def walk_left(self, duration=1.0):
        self.hold_key(DIK_LEFT, duration)
    
    def jump(self):
        self.hold_key(DIK_UP, 0.05)
    
    def release_all(self):
        for dik in CONTROLLED_KEYS:
            self.release_key(dik)
    
    def unhook(self):
        """Remove hook and restore original bytes."""
        if not self.hooked:
            return
        self.release_all()
        old_protect = ctypes.wintypes.DWORD()
        ctypes.windll.kernel32.VirtualProtectEx(
            self.pm.process_handle, self.gds_addr, 16,
            PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)
        )
        self.pm.write_bytes(self.gds_addr, self.original_bytes[:5], 5)
        ctypes.windll.kernel32.VirtualFreeEx(
            self.pm.process_handle, self.key_table_addr, 0, 0x8000
        )
        self.hooked = False
        print("[DInput] Hook removed, original GetDeviceState restored.")


if __name__ == "__main__":
    print("=== DirectInput Hook Test ===")
    
    di = DirectInputHook()
    if not di.attach():
        exit(1)
    
    print("\nInstalling hook...")
    if not di.install_hook():
        exit(1)
    
    print("\n>>> CLICK YOUR IDE NOW — 5 seconds <<<")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    print("Walking RIGHT for 3 seconds...")
    di.walk_right(3.0)
    time.sleep(0.5)
    print("Walking LEFT for 3 seconds...")
    di.walk_left(3.0)
    
    print("\nRemoving hook...")
    di.unhook()
    print("=== DONE ===")
    print("Did the character move?")

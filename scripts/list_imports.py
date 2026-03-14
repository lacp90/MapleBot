"""List ALL user32.dll imports from MapleRoyals.exe and check for GetProcAddress."""
import pymem, pymem.process, struct

pm = pymem.Pymem('MapleRoyals.exe')
maple_base = 0x00400000
for mod in pymem.process.enum_process_module(pm.process_handle):
    if mod.name and 'MapleRoyals' in mod.name:
        maple_base = mod.lpBaseOfDll
        break

print(f"MapleRoyals.exe @ 0x{maple_base:08X}")

e_lfanew = pm.read_int(maple_base + 0x3C)
pe_base = maple_base + e_lfanew
opt_hdr = pe_base + 24
import_rva = pm.read_int(opt_hdr + 104)
import_dir = maple_base + import_rva

i = 0
while True:
    desc = import_dir + i * 20
    name_rva = pm.read_int(desc + 12)
    if name_rva == 0:
        break
    dll = pm.read_bytes(maple_base + name_rva, 30).split(b'\x00')[0].decode('ascii', 'ignore')
    
    ilt_rva = pm.read_int(desc + 0)
    iat_rva = pm.read_int(desc + 16)
    
    funcs = []
    j = 0
    while True:
        ilt_entry = pm.read_int(maple_base + ilt_rva + j*4)
        if ilt_entry == 0:
            break
        if not (ilt_entry & 0x80000000):
            name = pm.read_bytes(maple_base + ilt_entry + 2, 50)
            name = name.split(b'\x00')[0].decode('ascii', 'ignore')
            funcs.append(name)
        else:
            funcs.append(f"[ordinal {ilt_entry & 0xFFFF}]")
        j += 1
    
    # Show all DLLs but highlight input-related ones
    if any(k in dll.lower() for k in ['user32', 'kernel32', 'dinput']):
        print(f"\n=== {dll} ({len(funcs)} imports) ===")
        for f in sorted(funcs):
            marker = ""
            if any(k in f.lower() for k in ['key', 'input', 'proc', 'message', 'async', 'focus', 'window', 'foreground']):
                marker = " <<<" 
            print(f"  {f}{marker}")
    i += 1

pm.close_process()
print("\nDone!")

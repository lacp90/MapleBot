"""Find how MapleRoyals.exe resolves keyboard functions via IAT."""
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
    
    if 'user32' in dll.lower():
        print(f"\n--- {dll} ---")
        ilt_rva = pm.read_int(desc + 0)
        iat_rva = pm.read_int(desc + 16)
        
        j = 0
        while True:
            ilt_entry = pm.read_int(maple_base + ilt_rva + j*4)
            if ilt_entry == 0:
                break
            if not (ilt_entry & 0x80000000):
                name = pm.read_bytes(maple_base + ilt_entry + 2, 40)
                name = name.split(b'\x00')[0].decode('ascii', 'ignore')
                if 'Key' in name or 'Async' in name or 'Input' in name or 'Focus' in name or 'Active' in name or 'Foreground' in name:
                    iat_addr = maple_base + iat_rva + j*4
                    func_ptr = pm.read_int(iat_addr)
                    fb = pm.read_bytes(func_ptr, 8)
                    hex_fb = ' '.join(f'{b:02X}' for b in fb)
                    print(f"  {name}")
                    print(f"    IAT @ 0x{iat_addr:08X} -> 0x{func_ptr:08X}")
                    print(f"    First bytes: {hex_fb}")
            j += 1
    i += 1

pm.close_process()
print("\nDone!")

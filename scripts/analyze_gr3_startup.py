"""Read-only GR III startup JPEG evidence; does not infer display from a filename."""
import hashlib, json, struct, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'builds/gr3-extension-validation/official-rtos.bin'
b = path.read_bytes()
if hashlib.sha256(b).hexdigest() != '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67':
    raise ValueError('exact GR III 2.10 RTOS required')
base = 0x53000000
path_at, descriptor, table_at = 0xb22adc, 0xb5f520, 0x107e0bc
assert b[path_at:path_at+29] == b'B:\\Resource\\Jpeg\\StartUp.jpg\0'
assert struct.unpack_from('<HHI', b, descriptor) == (720,480,base+path_at)
assert struct.unpack_from('<I', b, table_at)[0] == base+descriptor
# Renderer reads table[request] from the initialized-data copy, including entry 0 LcdAdj.
assert struct.unpack_from('<I',b,0x22e4b4)[0] == 0xe302cb78
assert struct.unpack_from('<I',b,0x22e4bc)[0] == 0xe345c500
callers=[]
for p in range(0,0xb00000,4):
    word = struct.unpack_from('<I',b,p)[0]
    if word >> 24 not in (0xea,0xeb): continue
    imm = word & 0xffffff
    if imm & 0x800000: imm -= 0x1000000
    if base+p+8+imm*4 == 0x5322e4a8: callers.append(hex(base+p))
assert struct.unpack_from('<I',b,0x19f270)[0] == 0xe3a07003  # Street Collabo is a real shutdown request.
assert callers == ['0x5319f234','0x531aae5c','0x531da74c']
print(json.dumps(dict(schema='m10v-gr3-startup-evidence/v1',rtos_sha256=hashlib.sha256(b).hexdigest(),
    native_resource='B:\\Resource\\Jpeg\\StartUp.jpg',resource_capacity=16687,width=720,height=480,
    path_va=hex(base+path_at),descriptor_va=hex(base+descriptor),table_lma=hex(base+table_at),request_id=1,
    renderer='0x5322e4a8',renderer_direct_callers=callers,
    known_request_sets={'0x5319f234':[2,3,10,11,12],'0x531aae5c':[0],'0x531da74c':[4,5,6,7,8,9]},
    startup_display_entry_verified=False,
    limitation='Native StartUp resource and request 1 exist; no verified normal-startup display caller. Resource replacement is offline verified; camera display timing needs hardware validation.',
    gr2_addresses_used=False),indent=2))

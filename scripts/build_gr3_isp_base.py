"""GR III 2.10: use Standard ISP inputs for native still/LiveView carriers.

Only the local tone register is substituted. ShootingInfo (including its tone
and the large R2Y output areas) stays in place. Shared helpers require the exact
Still or LiveView object vtable; local-process requires its still-plan caller.
"""
import struct
from scripts.build_gr3_menu_patches import assembly

HOOKS = (
    (0x536db7f8, 0xe5d3277c, 2, 'ldr r0,[r0]', 'parameters'),
    (0x536dc26c, 0xe5d7277c, 2, 'ldr r0,[r6]', 'color_table'),
    (0x536dc4bc, 0xe5d7377c, 3, 'ldr r0,[r6]', 'color_flags'),
    (0x536dd3e0, 0xe5d7177c, 1, 'ldr r0,[r4,#-0x1e0]', 'curve'),
    (0x535131c0, 0xe5d1377c, 3, 'mov r0,lr', 'local_process'),
)
STILL_VTABLE = 0x53dbd8a0
LIVE_VTABLE = 0x53dbd938
STILL_PLAN_RETURN = 0x53513620


def build_isp_base(base):
    image = bytearray(); entries = {}; patches = []
    for address, expected, result, object_load, name in HOOKS:
        entry = base + len(image); offset = 4 + result * 4
        compare = STILL_PLAN_RETURN if name == 'local_process' else STILL_VTABLE
        object_gate=f'{object_load};movw r1,#{compare&65535};movt r1,#{compare>>16};cmp r0,r1;'
        if name!='local_process':
            object_gate+=f'beq active;movw r1,#{LIVE_VTABLE&65535};movt r1,#{LIVE_VTABLE>>16};cmp r0,r1;'
        object_gate+='bne done;active:;'
        # Save scratch registers AND condition/status flags. In particular the
        # curve load sits between CMP and MOVNE/MOVEQ in the stock function.
        code = assembly(
            'push {r0-r3,ip,lr};mrs ip,cpsr;push {ip};'
            f'.word {hex(expected)};str r{result},[sp,#{offset}];'
            +object_gate+
            f'ldr r2,[sp,#{offset}];cmp r2,#12;beq neutral;'
            'sub r2,r2,#18;cmp r2,#3;bhi done;'
            f'neutral:;mov r2,#11;str r2,[sp,#{offset}];'
            f'done:;pop {{ip}};msr cpsr_fs,ip;pop {{r0-r3,ip,lr}};b {hex(address+4)}', entry)
        image += code
        entries[name] = entry
        patches.append({'address':address, 'expected':expected, 'entry':entry})
    return bytes(image), {'schema':'m10v-gr3-isp-base/v2', 'base':base,
                          'bytes':len(image), 'entries':entries, 'patches':patches,
                          'carriers':[12,18,19,20,21], 'base_tone':11,
                          'still_vtable':STILL_VTABLE, 'live_vtable':LIVE_VTABLE,
                          'live_view':'standard', 'still_plan_return':STILL_PLAN_RETURN}

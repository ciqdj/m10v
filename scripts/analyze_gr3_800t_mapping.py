"""Read the exact GR III startup translation table; never modify firmware."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

RTOS_SHA256 = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
LOAD = 0x53000000
APPEND_START, APPEND_END = 0x540b6000, 0x540c2000


def section_mapping(rtos, table_address, address):
    offset = table_address - LOAD + (address >> 20) * 4
    if offset < 0 or offset + 4 > len(rtos):
        raise ValueError('translation table outside RTOS')
    word = struct.unpack_from('<I', rtos, offset)[0]
    if word & 3 != 2 or word & (1 << 18):
        raise ValueError('expected ordinary ARM short-descriptor section')
    return {'virtual': address, 'physical': (word & 0xfff00000) | (address & 0xfffff),
            'descriptor_address': LOAD + offset, 'descriptor': word,
            'execute_never': bool(word & 16), 'access_permissions': (word >> 10) & 3,
            'access_permissions_extension': bool(word & (1 << 15)),
            'domain': (word >> 5) & 15}


def inspect_mapping(rtos):
    if hashlib.sha256(rtos).hexdigest() != RTOS_SHA256:
        raise ValueError('exact GR III RTOS identity required')
    anchors = {0x2cc: 0xe59f0160, 0x2d0: 0xee020f10,
               0x2d4: 0xe3a00000, 0x2d8: 0xee020f50,
               0x2dc: 0xe59f0154, 0x2e0: 0xee030f10}
    for offset, expected in anchors.items():
        if struct.unpack_from('<I', rtos, offset)[0] != expected:
            raise ValueError(f'startup preimage differs at {LOAD + offset:#x}')
    table = struct.unpack_from('<I', rtos, 0x434)[0]
    domains = struct.unpack_from('<I', rtos, 0x438)[0]
    rows = [section_mapping(rtos, table, address)
            for address in (APPEND_START, APPEND_END - 1)]
    for row in rows:
        domain_mode = (domains >> (row['domain'] * 2)) & 3
        if row['physical'] != row['virtual'] or row['execute_never'] or domain_mode != 1:
            raise ValueError('append range is not executable identity-mapped client memory')
        if row['access_permissions'] != 2 or not row['access_permissions_extension']:
            raise ValueError('append range permissions differ from original code section')
    # Data banks are non-contiguous. The hardware trace contains a CFA source
    # in ACEBC470; reject 80000000..9FFFFFFF/E0000000 regions with AP=0.
    raw_regions=[]
    for start,end in ((0x55000000,0x80000000),(0xa0000000,0xe0000000)):
        for address in range(start,end,0x100000):
            row=section_mapping(rtos,table,address)
            if (row['physical']!=address or row['descriptor']&0xfffff!=0x14c26 or
                (domains>>(row['domain']*2))&3!=1):
                raise ValueError('RAW data-bank mapping differs')
        raw_regions.append({'start':start,'end_exclusive':end,'section_attributes':0x14c26})
    return {'schema': 'm10v-gr3-800t-startup-mapping/v1', 'rtos_sha256': RTOS_SHA256,
            'table_address': table, 'domain_access_control': domains,
            'append_start': APPEND_START, 'append_end_exclusive': APPEND_END,
            'mappings': rows, 'proved': 'startup executable read-only identity mapping',
            'raw_source_regions':raw_regions,
            'limits': ['Does not prove updater load extent or later page-table changes',
                       'Does not emulate hardware cache coherency or camera execution']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rtos', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = json.dumps(inspect_mapping(args.rtos.read_bytes()), indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report)
    print(report, end='')

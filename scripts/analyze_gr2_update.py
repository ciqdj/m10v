#!/usr/bin/env python3
"""Execute the official GR II updater's header recognition instructions only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct

UPDATER_SHA='13fa830bff194679628eb1bb3f233420ee23c4fca3a28c4b650c53692820de95'
FILE_BASE=0xA0020200
ENTRY=0xA0057684


def analyze(updater:bytes)->dict:
    if hashlib.sha256(updater).hexdigest()!=UPDATER_SHA:
        raise ValueError('exact GR II updater identity required')
    from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
    from unicorn.arm_const import (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,
                                   UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC)
    cases=[]
    for kind in ('official_header','low_bit_changed','high_bit_changed'):
        machine=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_BIG_ENDIAN)
        machine.mem_map(0xA0020000,(len(updater)+0x2200+4095)&~4095)
        machine.mem_write(FILE_BASE,updater)
        machine.mem_map(0x50000000,0x20000)
        header=bytearray(updater[:512])
        if kind=='low_bit_changed':header[0]^=1
        if kind=='high_bit_changed':header[0]^=0x80
        machine.mem_write(0x50000000,bytes(header))
        helper_calls=[]

        def helper(uc,address,size,context):
            if address not in (0xA00A027C,0xA009FE7C):
                return
            first,second,count=[uc.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
            if count!=16:
                raise ValueError('header checker helper length differs')
            if address==0xA00A027C:
                uc.mem_write(first,bytes(uc.mem_read(second,count)))
                operation='copy'
            else:
                left,right=bytes(uc.mem_read(first,count)),bytes(uc.mem_read(second,count))
                uc.reg_write(UC_ARM_REG_R0,0 if left==right else 1)
                operation='compare_equal_only'
            helper_calls.append({'entry':hex(address),'operation':operation,'bytes':count})
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))

        machine.hook_add(UC_HOOK_CODE,helper)
        machine.reg_write(UC_ARM_REG_SP,0x5000F000)
        machine.reg_write(UC_ARM_REG_LR,0x50010001)
        machine.reg_write(UC_ARM_REG_R0,0x50000000)
        machine.emu_start(ENTRY|1,0x50010000,count=1000)
        if machine.reg_read(UC_ARM_REG_PC)!=0x50010000:
            raise RuntimeError('GR II header checker exceeded instruction budget')
        cases.append({'input':kind,'returned':True,
                      'comparison_equal':machine.reg_read(UC_ARM_REG_R0)==0,
                      'helper_calls':helper_calls})
    entry,data_bytes,file_bytes,checksum=struct.unpack_from('>4I',updater,0x160)
    if file_bytes!=len(updater) or data_bytes!=len(updater)-512:
        raise ValueError('GR II updater header lengths differ')
    records=[]
    for index in range(16):
        source,address,length,aux_address,aux_length=struct.unpack_from('>5I',updater,0x20+index*20)
        records.append({'source_field':hex(source),'address_field':hex(address),
                        'length_field':length,'aux_address_field':hex(aux_address),
                        'aux_length_field':aux_length})
    return {'schema':'m10v-gr2-update-header-proof/v1','updater_sha256':UPDATER_SHA,
            'byte_order':'big-endian','header_check_entry':hex(ENTRY),
            'initial_instruction_mapping':{'file_base':hex(FILE_BASE),'entry_field':hex(entry)},
            'header':{'data_bytes':data_bytes,'file_bytes':file_bytes,'update_checksum':hex(checksum),
                      'verify_flags':list(struct.unpack_from('>4I',updater,0x170))},
            'raw_load_records':records,'cases':cases,'modified_checksum_proved':False,
            'limits':['Official header recognition CPU instructions executed with synthetic header and stack.',
                      'Copy and equality comparison helpers intercepted; inequality sign/result code is not asserted.',
                      'High-bit normalization of the 16-byte magic is proved; full file data verification is not.',
                      'Load-record auxiliary-field semantics and all peripheral/flash operations remain unproved.',
                      'This report supplies no checksum bypass or modified firmware writer.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--updater',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    result=analyze(args.updater.read_bytes())
    if args.updater.resolve()==args.out.resolve():
        raise ValueError('output must not overwrite updater input')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report':str(args.out),'cases':len(result['cases'])}))

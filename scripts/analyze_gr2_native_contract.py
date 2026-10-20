#!/usr/bin/env python3
"""Identity-locked original GR II native ABI probes; no firmware writes or flash I/O."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_unity_update import official_profile,_machine,FILE_BASE

def probe_rtc_get_time(code:bytes,fields:tuple[int,...])->dict:
    """Execute RTC_GetTime unchanged, substituting only the compact hardware read.

    This proves the wrapper ABI, not that the RTC is initialized/valid on a camera.
    Its R0 is the last second value, not a boolean or a driver status.
    """
    official_profile(code,'gr2')
    if len(fields)!=6 or any(type(v) is not int for v in fields) or not 0<=fields[0]<=65535 or any(not 0<=v<=255 for v in fields[1:]):
        raise ValueError('six compact RTC fields required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R4,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=_machine(code);output=0x50001000;stop=0x5001f000;calls=0
    machine.mem_write(output-4,b'\xa5'*20)
    machine.reg_write(UC_ARM_REG_R0,output);machine.reg_write(UC_ARM_REG_R4,0x12345678)
    machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,stop|1)
    def driver(uc,address,size,ctx):
        nonlocal calls
        calls+=1
        uc.mem_write(uc.reg_read(UC_ARM_REG_R0),struct.pack('>H6B',*fields,0))
        uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    machine.hook_add(UC_HOOK_CODE,driver,begin=0xA005AE20,end=0xA005AE20)
    machine.emu_start(0xA00341A9,stop,count=1000)
    if machine.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('RTC wrapper exceeded execution budget')
    result=bytes(machine.mem_read(output,12))
    return dict(entry='0xa00341a8',driver_entry='0xa005ae20',fields=list(struct.unpack('>6H',result)),
                output_hex=result.hex(),returned=machine.reg_read(UC_ARM_REG_R0),driver_calls=calls,
                guards_unchanged=bytes(machine.mem_read(output-4,4))+bytes(machine.mem_read(output+12,4))==b'\xa5'*8,
                callee_saved_preserved=machine.reg_read(UC_ARM_REG_R4)==0x12345678,
                helpers_intercepted=['RTC compact hardware read'],hardware_tested=False,
                scope='Original non-null RTC_GetTime wrapper, six big-endian u16 outputs. RTC readiness and driver validity are not proved.')

def probe_sd_io(code:bytes,operation:str,payload:bytes,*,read_count:int|None=None)->dict:
    """Prove normal-file wrapper ABI, using synthetic open handle and SD backend.

    File opening, media readiness and persistence are not proved by this fixture.
    """
    official_profile(code,'gr2')
    if operation not in ('read','write') or not isinstance(payload,bytes) or not 0<len(payload)<=4096:
        raise ValueError('read/write and 1..4096 payload bytes required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    read_count=len(payload) if read_count is None else read_count
    if type(read_count) is not int or not 0<=read_count<=len(payload) or (operation=='write' and read_count!=len(payload)):
        raise ValueError('valid read byte count required')
    machine=_machine(code);handle=0x50001000;buffer=0x50002000;stop=0x5001f000
    instruction=struct.unpack_from('>H',code,0xA002CABA-FILE_BASE)[0]
    if instruction&0xf800!=0x4800:raise ValueError('official file magic load differs')
    literal=((0xA002CABA+4)&~3)+(instruction&255)*4
    magic=struct.unpack_from('>I',code,literal-FILE_BASE)[0]
    fixture=bytearray(0x38);struct.pack_into('>II',fixture,0,magic,0x50003000)
    fixture[0x10:0x10+12]=b'H:/M10V.BIN\0';machine.mem_write(handle,bytes(fixture))
    machine.mem_write(buffer-4,b'\xa5'*(len(payload)+8))
    if operation=='write':machine.mem_write(buffer,payload)
    backend=[];transferred=b'';status_calls=0
    def helper(uc,address,size,ctx):
        nonlocal transferred,status_calls
        if address in (0xA0039F9C,0xA003A01A):raise RuntimeError('original file wrapper assertion')
        if address in (0xA0065386,0xA0065428):
            args=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            expected=[buffer,1,len(payload),0x50003000] if operation=='read' else [buffer,len(payload),1,0x50003000]
            if args!=expected:raise ValueError('original file backend argument contract differs')
            backend.append(args)
            if operation=='read':uc.mem_write(buffer,payload[:read_count]);result=read_count
            else:result=1
            transferred=bytes(uc.mem_read(buffer,len(payload)))
        elif address==0xA00652F0:
            status_calls+=1;result=int(status_calls>1 and read_count<len(payload)) # synthetic EOF after short read
        else:result=0 # filesystem readiness and errno boundaries
        uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    for address in (0xA002B0EE,0xA00652F0,0xA00652CE,0xA0065386,0xA0065428,0xA0039F9C,0xA003A01A):
        machine.hook_add(UC_HOOK_CODE,helper,begin=address,end=address)
    for register,value in ((UC_ARM_REG_R0,handle),(UC_ARM_REG_R1,buffer),(UC_ARM_REG_R2,len(payload)),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
        machine.reg_write(register,value)
    entry=0xA002CA98 if operation=='read' else 0xA002CC4A
    machine.emu_start(entry|1,stop,count=10000)
    if machine.reg_read(UC_ARM_REG_PC)!=stop or len(backend)!=1:raise RuntimeError('file wrapper exceeded execution budget')
    return dict(entry=hex(entry),operation=operation,returned=machine.reg_read(UC_ARM_REG_R0),
                backend_item_bytes=backend[0][1],backend_items=backend[0][2],transferred_hex=transferred.hex(),
                buffer_hex=bytes(machine.mem_read(buffer,len(payload))).hex(),
                guards_unchanged=bytes(machine.mem_read(buffer-4,4))+bytes(machine.mem_read(buffer+len(payload),4))==b'\xa5'*8,
                hardware_tested=False,helpers_intercepted=['filesystem readiness','file backend transfer','file status','errno'],
                scope='Original handle-magic/path dispatch and full-transfer wrapper semantics only; synthetic open handle, no SD I/O.')

def probe_sd_open_mode(code:bytes,flags:int)->dict:
    """Execute original H: open-mode selection up to fopen, without opening a file."""
    official_profile(code,'gr2')
    if type(flags) is not int or not 0<=flags<=0xffffffff:raise ValueError('u32 file flags required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=_machine(code);path=0x50001000;observed={}
    # Original filesystem control object, with synthetic readiness/lock state.
    ins=struct.unpack_from('>H',code,0xA002C74C-FILE_BASE)[0]
    literal=((0xA002C74C+4)&~3)+(ins&255)*4
    control=struct.unpack_from('>I',code,literal-FILE_BASE)[0]
    # The control object is initialized data in the original mapped module.
    machine.mem_read(control,32)
    machine.mem_write(path,b'H:/M10V.BIN\0')
    def cstring(uc,pointer):
        return bytes(uc.mem_read(pointer,32)).split(b'\0',1)[0].decode('ascii')
    def boundary(uc,address,size,ctx):
        if address==0xA0065324:
            observed.update(path=cstring(uc,uc.reg_read(UC_ARM_REG_R0)),mode=cstring(uc,uc.reg_read(UC_ARM_REG_R1)))
            uc.emu_stop();return
        uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    for address in (0xA002B0EE,0xA0027360,0xA00273A4,0xA00A2058,0xA0065324):
        machine.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    machine.reg_write(UC_ARM_REG_R0,path);machine.reg_write(UC_ARM_REG_R1,flags)
    machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,0x5001f001)
    machine.emu_start(0xA002C70F,0x5001f000,count=10000)
    if not observed:raise RuntimeError('original mode selector did not reach fopen')
    return dict(entry='0xa002c70e',flags=flags,**observed,opened=False,hardware_tested=False,
                helpers_intercepted=['filesystem readiness','media status','lock','unlock','fopen stop boundary'],
                scope='Original H: mode-selection instructions and string comparison; no file creation or handle allocation.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.component.resolve()==args.out.resolve():raise ValueError('output must not overwrite official input')
    code=args.component.read_bytes();profile=official_profile(code,'gr2')
    report=dict(schema='m10v-gr2-native-contract/v1',component_sha256=profile['sha'],
                rtc=probe_rtc_get_time(code,(2026,10,20,18,30,45)),
                sd_io=[probe_sd_io(code,operation,b'M10V\x00config\xff') for operation in ('read','write')],
                sd_modes=[probe_sd_open_mode(code,flags) for flags in (0,1,9,2,10,0x102)],can_build=False)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(args.out),can_build=False)))

if __name__=='__main__':main()

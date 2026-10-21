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

def runtime_machine(code:bytes,*,cpu_model:int|None=None):
    """Map stock segments using an ARMv5 BE32/MPU instruction model.

    ARM946 is an emulator execution model, not a claim of camera CPU identity.
    Unicorn defaults to ARM1176, whose endian state across kernel exceptions
    differs from the older BE32 instructions used by this firmware.
    """
    official_profile(code,'gr2')
    from scripts.analyze_unity_runtime import parse_executable_load_map
    from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_BIG_ENDIAN
    uc=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_BIG_ENDIAN)
    from unicorn.arm_const import UC_CPU_ARM_946
    uc.ctl_set_cpu_model(UC_CPU_ARM_946 if cpu_model is None else cpu_model)
    uc.mem_map(0xA0000000,0x1000000);uc.mem_map(0x50000000,0x20000)
    for row in parse_executable_load_map(code)[:15]:
        start=row['source_file_offset'];uc.mem_write(row['address'],code[start:start+row['length']])
    return uc

def probe_code_sync(code:bytes,*,native_runtime:dict)->dict:
    """Run User SVC5 via its original data dispatch, with CP15 as boundary."""
    from unicorn import UC_HOOK_CODE,UC_HOOK_INTR
    from unicorn import arm_const as r
    from scripts.analyze_unity_runtime import parse_executable_load_map
    uc=runtime_machine(code);uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
    from scripts.analyze_unity_runtime import load_gr2_low_record
    low_load=load_gr2_low_record(uc,code)
    if low_load['returned'] or not low_load['payload_matches'] or not low_load['bss_zeroed']:raise RuntimeError('original low-vector indexed load failed')
    original_callback=bytes(uc.mem_read(0xA0044F4C,4));original_vector=bytes(uc.mem_read(0xA00AF884,4))
    # Execute the original task-frame constructor with the actual startup entry
    # found in the kernel's static initial-task configuration.
    startup_entry=struct.unpack('>I',uc.mem_read(0xA00B5BB4,4))[0]
    for register,value in ((r.UC_ARM_REG_R0,startup_entry),(r.UC_ARM_REG_R1,0),(r.UC_ARM_REG_R2,0x50004000),
                           (r.UC_ARM_REG_SP,0x50018000),(r.UC_ARM_REG_LR,0x5001f000)):uc.reg_write(register,value)
    uc.emu_start(0xA00AF7A8,0x5001f000,count=1000)
    if uc.reg_read(r.UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('original startup task-frame construction failed')
    task_frame=struct.unpack('>20I',uc.mem_read(0x50004000,80))

    if original_vector!=struct.pack('>I',0xA00AF8A8):raise ValueError('original SVC5 data vector changed')
    operations=[];operands=[];behavior={'bufferable':0};checks=[]
    def cp15(machine,address,size,context):
        value=struct.unpack('>I',machine.mem_read(address,4))[0]
        if value&0x0f100f10==0x0e100f10:
            if ((value>>16)&15,value&15)!=(3,0):raise ValueError('unexpected cache policy read')
            machine.reg_write(r.UC_ARM_REG_R0+((value>>12)&15),behavior['bufferable']);machine.reg_write(r.UC_ARM_REG_PC,address+4)
        elif value&0x0f100f10==0x0e000f10:
            operations.append([(value>>16)&15,value&15,(value>>5)&7]);operands.append(machine.reg_read(r.UC_ARM_REG_R0+((value>>12)&15)));machine.reg_write(r.UC_ARM_REG_PC,address+4)
    uc.hook_add(UC_HOOK_CODE,cp15,begin=native_runtime['base'],end=native_runtime['base']+native_runtime['memory_bytes']-1)
    def interrupt(machine,number,context):
        if number!=2:raise RuntimeError('unexpected code-sync exception')
        previous=machine.reg_read(r.UC_ARM_REG_CPSR);resume=machine.reg_read(r.UC_ARM_REG_PC)
        machine.reg_write(r.UC_ARM_REG_CPSR,(previous&~0x3f)|0x13);machine.reg_write(r.UC_ARM_REG_SP,0x50017000)
        machine.reg_write(r.UC_ARM_REG_SPSR,previous);machine.reg_write(r.UC_ARM_REG_LR,resume);machine.reg_write(r.UC_ARM_REG_PC,0x844)
    uc.hook_add(UC_HOOK_INTR,interrupt)
    def run(entry,argument=0):
        old=uc.reg_read(r.UC_ARM_REG_CPSR);uc.reg_write(r.UC_ARM_REG_CPSR,(old&~0xff)|0x10)
        saved=[0x33550000+index for index in range(8)]
        for index,value in enumerate(saved):uc.reg_write(r.UC_ARM_REG_R4+index,value)
        uc.reg_write(r.UC_ARM_REG_R0,argument);uc.reg_write(r.UC_ARM_REG_R1,0x12345678)
        uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,0x5001f000)
        uc.emu_start(entry,0x5001f000,count=10000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('User code-sync return budget exceeded')
        checks.append((uc.reg_read(r.UC_ARM_REG_CPSR)&0xff==0x10 and uc.reg_read(r.UC_ARM_REG_SP)==0x50018000,
                       [uc.reg_read(r.UC_ARM_REG_R4+index) for index in range(8)]==saved))
        return uc.reg_read(r.UC_ARM_REG_R0),uc.reg_read(r.UC_ARM_REG_R1)
    unrelated_original=run(0xA00AF75C,0x12345678)
    missing=run(native_runtime['symbols']['gr2_code_sync'])[0]
    uc.mem_write(0xA00AF884,bytes.fromhex(native_runtime['cache_svc_vector_patch_hex']))
    good=run(native_runtime['symbols']['gr2_code_sync'])[0]
    sync_operations=list(operations);sync_operands=list(operands)
    operations.clear();operands.clear()
    data_returns=[run(native_runtime['symbols'][name])[0] for name in ('gr2_cache_before','gr2_cache_after')]
    data_operations=list(operations);data_operands=list(operands)
    operations.clear();operands.clear()
    unrelated_native=run(0xA00AF75C,0x12345678)
    behavior['bufferable']=32;bad=run(native_runtime['symbols']['gr2_code_sync'])[0]
    return dict(initial_task_entry=startup_entry,initial_task_mode=task_frame[1]&31,low_record_loader=low_load,
                returns=[missing,good,bad],operations=sync_operations,operands=sync_operands,
                data_cache_vector_supported=data_returns==[1,1] and data_operations==[[7,6,0],[7,10,4]] and data_operands==[0,0],
                rejected_policy_no_operations=not operations,
                callback_code_unchanged=bytes(uc.mem_read(0xA0044F4C,4))==original_callback,
                user_return_preserved=all(v[0] for v in checks),callee_saved_preserved=all(v[1] for v in checks),
                unrelated_svc_preserved=unrelated_original==unrelated_native,
                helpers_intercepted=['synthetic CP15 bufferable policy read','CP15 drain and instruction-cache invalidation observation'],hardware_tested=False,
                scope='Original indexed load of the complete low record, then its SVC dispatch and exception return plus native replacement of its data-table entry only. User call refuses absent vector/unexpected bufferable policy. CP15 is observed rather than physically modeled; no automatic boot installation or hardware coherency proof.')

def probe_image_pool_startup_phase(code:bytes)->dict:
    """Execute stock phase2 dispatch up to (not through) image-pool creation."""
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);calls=[];observed={};stack=0x50018000
    def boundary(machine,address,size,context):
        if address==0xA00E1DF0:
            observed['pool_caller']=(machine.reg_read(r.UC_ARM_REG_LR)&~1)-4
            observed['original_body_bytes']=struct.unpack('>I',machine.mem_read(0xA01137EC,4))[0]
            machine.emu_stop();return
        calls.append(hex(address));machine.reg_write(r.UC_ARM_REG_R0,0)
        machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    for address in (0xA00AFDA4,0xA00AFDAC,0xA00DFC08,0xA00E1DF0):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    uc.reg_write(r.UC_ARM_REG_R0,2);uc.reg_write(r.UC_ARM_REG_SP,stack);uc.reg_write(r.UC_ARM_REG_LR,0x5001f001)
    uc.emu_start(0xA00C63A7,0x5001f000,count=1000)
    if uc.reg_read(r.UC_ARM_REG_PC)!=0xA00E1DF0 or not observed:raise RuntimeError('phase2 did not reach original image-pool initialization')
    return dict(phase=2,calls_before_pool=calls,pool_entry='0xa00e1df0',
                pool_caller=hex(observed['pool_caller']),original_body_bytes=observed['original_body_bytes'],
                helpers_intercepted=calls,hardware_tested=False,
                scope='Original phase2 dispatch through its actual pool call. Prior phase helpers are boundaries; pool body is covered separately. No task scheduling or boot installation claim.')

def probe_c_heap_startup(code:bytes,*,reserved_end:int|None=None)->dict:
    """Execute stock stack/heap boundary getter and C heap initialization.

    A reservation changes only the literal in synthetic RAM, not the official
    input or a packaged firmware. This does not measure peak libc heap use.
    """
    official_profile(code,'gr2')
    if reserved_end is not None and (type(reserved_end) is not int or reserved_end%4096 or not 0xa0798000<reserved_end<0xa0900000):
        raise ValueError('page-aligned reserved end inside original C heap required')
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R10,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=runtime_machine(code);stop=0x5001f000;stack=0x50018000
    if reserved_end is not None:machine.mem_write(0xA0023154,struct.pack('>I',reserved_end))
    guard_start=0xA0798000;guard_length=(reserved_end or guard_start)-guard_start
    if guard_length:machine.mem_write(guard_start,b'\xa5'*guard_length)
    for reg,value in ((UC_ARM_REG_R10,0x50010000),(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop)):
        machine.reg_write(reg,value)
    machine.emu_start(0xA00A1A3C,stop,count=10000)
    if machine.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('original stack/heap boundary budget exceeded')
    base=machine.reg_read(UC_ARM_REG_R0);limit=machine.reg_read(UC_ARM_REG_R2)
    stack_preserved=machine.reg_read(UC_ARM_REG_SP)==stack
    machine.reg_write(UC_ARM_REG_R1,limit);machine.reg_write(UC_ARM_REG_LR,stop|1)
    machine.emu_start(0xA00A07E3,stop,count=100000)
    if machine.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('original C heap initialization budget exceeded')
    # The original initializer writes a heap control head at the supplied base.
    head=struct.unpack('>3I',machine.mem_read(base,12))
    return dict(boundary_entry='0xa0022d5c',boundary_caller='0xa00a1a3c',initializer='0xa00a07e2',
                heap_base=base,heap_limit=limit,heap_bytes=limit-base,heap_head=list(head),
                heap_initialized=head[2]==base,stack_preserved=stack_preserved,
                reserved_guard_preserved=not guard_length or bytes(machine.mem_read(guard_start,guard_length))==b'\xa5'*guard_length,
                helpers_intercepted=[],hardware_tested=False,
                scope='Stock C runtime heap boundary and allocator initialization; optional literal reservation only in synthetic RAM. Peak heap demand and other owners remain to audit.')

def probe_rtos_pool(code:bytes,*,native_runtime:dict|None=None)->dict:
    """Execute original region init, RTOS create/allocate/free with a synthetic kernel table."""
    official_profile(code,'gr2')
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stop=0x5001f000;table=0x50008000;out=0x50001000
    uc.mem_write(0xA00B5BFE,struct.pack('>H',1));uc.mem_write(0xA00B5BE0,struct.pack('>I',table))
    uc.mem_write(table,struct.pack('>h',-2))
    def run(entry,args,thumb=False):
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):uc.reg_write(reg,value)
        uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop|(1 if thumb else 0))
        try:uc.emu_start(entry|(1 if thumb else 0),stop,count=1000000)
        except Exception as error:raise RuntimeError(f'RTOS probe PC={uc.reg_read(UC_ARM_REG_PC):08x}: {error}') from error
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('original RTOS pool execution budget exceeded')
        return uc.reg_read(UC_ARM_REG_R0)
    run(0xA0024BCA,[],True)
    native_result={}
    if native_runtime is not None:
        runtime=bytes.fromhex(native_runtime['runtime_hex']);base=native_runtime['base']
        if base!=0xa0798000 or native_runtime['memory_bytes']>0x68000:raise ValueError('bounded native allocation bridge required')
        uc.mem_write(base,runtime)
        symbols=native_runtime['symbols'];pointer=run(symbols['gr2_allocate'],[0x60000]);results=[]
        for _ in range(8):
            exhausted=run(symbols['gr2_allocate'],[0x60000]);results.append(exhausted)
            if not exhausted:break
        else:raise ValueError('native allocation did not stop at pool exhaustion')
        released=run(symbols['gr2_release'],[pointer]);again=run(symbols['gr2_allocate'],[0x60000])
        return dict(native_allocated_pointer=pointer,native_exhausted_pointer=exhausted,native_release_returned=released,
                    native_reallocated_pointer=again,native_allocation_in_pool=0xa0900010<=pointer<0xa0b00010,
                    helpers_intercepted=[],hardware_tested=False,
                    scope='Compiled bridge calls original RTOS create/allocate/free code; synthetic kernel table, single thread and no camera scheduler.')
    allocated=run(0xA006798C,[1,0x60000,out]);pointer=struct.unpack('>I',uc.mem_read(out,4))[0]
    oversized=run(0xA006798C,[1,0x200000,out])
    allocation_returns=[]
    for _ in range(8):
        exhausted=run(0xA006798C,[1,0x60000,out]);allocation_returns.append(exhausted)
        if exhausted&0x80000000:break
    else:raise ValueError('synthetic pool did not exhaust within its capacity')
    released=run(0xA0067BE8,[1,pointer])
    allocated_again=run(0xA006798C,[1,0x60000,out]);again=struct.unpack('>I',uc.mem_read(out,4))[0]
    return dict(pool_id=1,allocate_returned=allocated,allocated_pointer=pointer,exhausted_returned=exhausted,
                oversized_returned=oversized,allocation_returns=allocation_returns,free_returned=released,reallocate_returned=allocated_again,reallocated_pointer=again,helpers_intercepted=[],
                hardware_tested=False,scope='Original RTOS pool arithmetic and lifecycle; synthetic one-pool kernel table and single-thread SVC CPU context. Scheduler/concurrency not emulated.')

def probe_rtos_mutex(code:bytes)->dict:
    """Original create/try-lock/unlock with two explicit kernel task identities.

    This exercises ownership and polling, not a concurrent task scheduler.
    No mutex, critical section or bookkeeping helper is substituted.
    """
    from unicorn import arm_const as r
    uc=runtime_machine(code);stop=0x5001f000;stack=0x50018000;table=0x50008000
    uc.mem_write(0xA00B5BF8,struct.pack('>h',2));uc.mem_write(0xA00B5BD4,struct.pack('>I',table))
    for index in range(2):uc.mem_write(table+14*index,struct.pack('>h',-2))
    # Active task/dispatch flags, two empty owned-mutex chains and equal base
    # and effective priorities. These are kernel state, not replacement code.
    uc.mem_write(0xA06B6DE0,b'\x01');uc.mem_write(0xA06B6DE3,b'\x01')
    for identity in (1,2):
        task=0xA05F5C28+68*identity
        uc.mem_write(task+8,struct.pack('>2h',-1,-1));uc.mem_write(task+24,struct.pack('>3h',20,0,20))
    uc.mem_write(0x50001000,struct.pack('>2HI',2,0,0))
    def run(entry,*args):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1),args):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_SP,stack);uc.reg_write(r.UC_ARM_REG_LR,stop)
        uc.emu_start(entry,stop,count=100000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=stack:raise RuntimeError('original mutex execution budget/stack failure')
        return struct.unpack('>i',struct.pack('>I',uc.reg_read(r.UC_ARM_REG_R0)))[0]
    created=run(0xA00665CC,0x50001000);returns=[];owners=[]
    if created!=1:raise RuntimeError('original mutex did not use first free table entry')
    for task,entry in ((1,0xA0066D94),(1,0xA0066D94),(2,0xA0066D94),(2,0xA00671B8),(1,0xA00671B8),(2,0xA0066D94),(2,0xA00671B8)):
        uc.mem_write(0xA00C22C0,struct.pack('>h',task));returns.append(run(entry,created,0));owners.append(struct.unpack('>h',uc.mem_read(table+12,2))[0])
    return dict(create_returned=created,returns=returns,owners=owners,stack_preserved=True,helpers_intercepted=[],hardware_tested=False,
                scope='Original kernel mutex create, polling lock, owner chain and unlock on synthetic task records; no preemption, wait queues or camera thread timing proof.')

def probe_fat_directory(code:bytes,*,entries:tuple[str,...]=(),read_error:int=0,short_read:bool=False,native_runtime:dict|None=None,ready:bool=True,cache_boundary:bool=False)->dict:
    """Original PrFILE initializer, SDK find-first/next and FAT16 root decoder.

    Synthetic mounted H: geometry and raw directory records; RTOS semaphore/
    thread identity, removable-media state and record I/O are boundaries.
    """
    import re
    if len(entries)>32 or any(not re.fullmatch(r'[A-Za-z0-9_]{1,8}\.[A-Za-z0-9_]{1,3}',name) for name in entries):raise ValueError('bounded synthetic ASCII 8.3 names required')
    if type(read_error) is not int or not 0<=read_error<=255 or type(short_read) is not bool or type(ready) is not bool or type(cache_boundary) is not bool:raise ValueError('bounded media boundary status required')
    from unicorn import UC_HOOK_CODE,arm_const as r
    uc=runtime_machine(code);sdk=0x50004000;volume=0xA06AA6A0;stop=0x5001f000;reads=[];found=[];semaphores=[]
    def call(entry,*args,thumb=True):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2),args):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,stop|int(thumb))
        uc.emu_start(entry|int(thumb),stop,count=3000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=0x50018000:raise RuntimeError('original PrFILE operation budget/stack failure')
        return uc.reg_read(r.UC_ARM_REG_R0)
    def os_boundary(machine,address,size,unused):
        value=0
        if address==0xA0067E90:semaphores.append(address);value=len(semaphores)
        elif address==0xA0068D74:machine.mem_write(machine.reg_read(r.UC_ARM_REG_R0),struct.pack('>H',1))
        elif address==0xA008A5AE:value=int(ready)
        machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    for address in (0xA0067E90,0xA0068C4C,0xA0068598,0xA0068D74,0xA008A5AE,0xA008A5D0):uc.hook_add(UC_HOOK_CODE,os_boundary,begin=address,end=address)
    if native_runtime:
        uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
        uc.mem_write(0xA00B5BFE,struct.pack('>H',1));uc.mem_write(0xA00B5BE0,struct.pack('>I',0x50007000));uc.mem_write(0x50007000,struct.pack('>h',-2));call(0xA0024BCA)
    if call(0xA0083C42,0,0)!=0:raise RuntimeError('original PrFILE initialization failed')
    uc.mem_write(volume,struct.pack('>H',512));uc.mem_write(volume+0xC,struct.pack('>I',1));uc.mem_write(volume+0x29,bytes([1,9,0]));uc.mem_write(volume+0x2E,struct.pack('>H',32));uc.mem_write(volume+0x38,struct.pack('>I',100))
    uc.mem_write(volume+0x61AC,b'H');uc.mem_write(volume+0x61A8,struct.pack('>I',3 if ready else 1));uc.mem_write(0x50001000,b'H:/*\0')
    media=bytearray(16384)
    for index,name in enumerate(entries):
        base,extension=name.upper().split('.');at=32*index
        media[at:at+11]=base.ljust(8).encode()+extension.ljust(3).encode();media[at+11]=0x20;struct.pack_into('<I',media,at+28,104+index)
    def record_read(machine,address,size,unused):
        a,b,c,d=[machine.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3)]
        count,out,flags=struct.unpack('>3I',machine.mem_read(machine.reg_read(r.UC_ARM_REG_SP),12))
        if a!=volume or count!=32 or not 100<=c<132 or d>=512 or d%32 or flags:raise RuntimeError('original FAT root record extent differs')
        reads.append([c,d]);at=(c-100)*512+d;n=count-int(short_read)
        machine.mem_write(b,bytes(media[at:at+n]));machine.mem_write(out,struct.pack('>I',n));machine.reg_write(r.UC_ARM_REG_R0,read_error);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    if cache_boundary:
        uc.mem_map(0x52000000,4096)
        def cache_read(machine,address,size,unused):
            a,b,c,d=[machine.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3)]
            if a!=volume or not 100<=b<132 or d:raise RuntimeError('original root sector cache request differs')
            reads.append([b,d]);at=(b-100)*512
            machine.mem_write(0x52000000,bytes(media[at:at+512]));machine.mem_write(0x5000B008,struct.pack('>I',0x52000000));machine.mem_write(c,struct.pack('>I',0x5000B000))
            machine.reg_write(r.UC_ARM_REG_R0,17 if short_read else read_error);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,cache_read,begin=0xA008BB8C,end=0xA008BB8C)
    else:uc.hook_add(UC_HOOK_CODE,record_read,begin=0xA00941B2,end=0xA00941B2)
    extra={};terminal=None
    if native_runtime:
        word=lambda pointer:struct.unpack('>I',uc.mem_read(pointer,4))[0]
        free=lambda:word(word(0x50007004)+12)*word(0x50007014)
        available=free();value=call(native_runtime['symbols']['gr2_journals_absent'],thumb=False)
        extra=dict(native_absent_return=struct.unpack('>i',struct.pack('>I',value))[0],pool_restored=free()==available)
    else:
        for index in range(34):
            result=call(0xA00653BC,0x50001000,0x77,sdk) if index==0 else call(0xA00653EE,sdk)
            if result:terminal=call(0xA00652CE);break
            name=bytes(uc.mem_read(sdk+0x472,13)).split(b'\0',1)[0].decode('ascii');size=struct.unpack('>I',uc.mem_read(sdk+0x46C,4))[0]
            found.append(dict(name=name,size=size))
        else:raise RuntimeError('original directory enumeration exceeded synthetic entry bound')
    return dict(**extra,entries=found,terminal_error=terminal,record_reads=reads,initializer_semaphores=len(semaphores),stack_preserved=True,
                helpers_intercepted=['RTOS semaphore and task identity','removable media readiness/change','sector cache acquisition' if cache_boundary else 'directory record media read'],hardware_tested=False,
                scope='Original PrFILE initialization/default character callbacks, SDK first/next/errno, root-sector arithmetic, FAT16 entries and wildcard/name conversion. Mounted geometry/records and OS/device boundaries are synthetic; no FAT32/exFAT, actual card, hot-swap or simultaneous writers proof.')

def probe_file_mode_flags(code:bytes)->dict:
    """Execute the stock stdio mode parser, without opening any files."""
    from unicorn import arm_const as r
    uc=runtime_machine(code);stop=0x5001f000;pointer=0x50001000;flags={}
    for mode in ('r','rb','r+','w','wb','w+','a','a+','wx','wbx','x'):
        uc.mem_write(pointer,mode.encode()+b'\0')
        uc.reg_write(r.UC_ARM_REG_R0,pointer);uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,stop|1)
        uc.emu_start(0xA00754AD,stop,count=10000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=0x50018000:raise RuntimeError('original stdio mode parser budget/stack failure')
        flags[mode]=uc.reg_read(r.UC_ARM_REG_R0)
    return dict(flags=flags,helpers_intercepted=[],hardware_tested=False,
                scope='Exact original stdio spellings and bitmasks only; no inference that other low-level exclusive-create APIs are absent.')

def probe_effect_names(code:bytes,*,native_runtime:dict)->dict:
    """Stock locale lookup through RAM-installed, stable private name values."""
    from unicorn import arm_const as r
    from scripts.gr2_text_contract import effect_name_contract
    import zlib
    uc=runtime_machine(code);uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']));stop=0x5001f000
    def word(pointer):return struct.unpack('>I',uc.mem_read(pointer,4))[0]
    def run(entry,*args,thumb=False):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3),args):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,stop|int(thumb))
        uc.emu_start(entry|int(thumb),stop,count=1000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=0x50018000:raise RuntimeError('effect label operation budget/stack failure')
        return uc.reg_read(r.UC_ARM_REG_R0)
    sym=native_runtime['symbols'];state=0x50002000;records=0x50002400
    uc.mem_write(0xA00B5BFE,struct.pack('>H',1));uc.mem_write(0xA00B5BE0,struct.pack('>I',0x50007000));uc.mem_write(0x50007000,struct.pack('>h',-2));run(0xA0024BCA,thumb=True)
    uc.mem_write(0xA00B5BF8,struct.pack('>h',1));uc.mem_write(0xA00B5BD4,struct.pack('>I',0x50006C00));uc.mem_write(0x50006C00,struct.pack('>h',-2))
    uc.mem_write(0xA06B6DE0,b'\1');uc.mem_write(0xA06B6DE3,b'\1');uc.mem_write(0xA00C22C0,struct.pack('>h',1))
    task=0xA05F5C28+68;uc.mem_write(task+8,struct.pack('>2h',-1,-1));uc.mem_write(task+24,struct.pack('>3h',20,0,20))
    free=lambda:word(word(0x50007004)+12)*word(0x50007014)
    available=free();contract=effect_name_contract(code);ids=contract['ids'];rows=contract['rows']
    tables=lambda:[bytes(uc.mem_read(row,847*4)) for row in rows]
    original=tables();run(sym['m10v_library_init'],state)
    if run(sym['gr2_configuration_publish'],state,records)!=1 or run(sym['gr2_effect_names_refresh'])!=1:raise RuntimeError('effect name installation failed')
    installed=tables()
    uc.mem_map(0x51000000,0x10000)
    uc.mem_write(0x51000000,(bytes(20)+bytes.fromhex('ffffffff'))*0x383);uc.mem_write(0x51006000,(bytes(4)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x51000000,0x50005000,0x383));uc.mem_write(0x50005000,struct.pack('>6I',0,0x51006000,0x383,0x5000D000,0,0))
    pointers=[[word(row+4*(identity-1)) for identity in ids] for row in rows]
    def caption(identity,language):
        pointer=run(sym['gr2_original_text'],identity,language)
        return bytes(uc.mem_read(pointer,192)).decode('utf-16-be').split('\0')[0]
    initial=[caption(identity,1) for identity in ids]
    match=True
    for language in range(21):
        uc.mem_write(0x5000D000+0x1e4*4,struct.pack('>I',language))
        for index,identity in enumerate(ids):
            current=run(0xA03A4AEE,identity,thumb=True)
            match=match and caption(identity,language)==initial[index] and bytes(uc.mem_read(current,192)).decode('utf-16-be').split('\0')[0]==initial[index]
    unrelated=all(before[4*i:4*i+4]==after[4*i:4*i+4] for before,after in zip(original,installed) for i in range(847) if i+1 not in ids)
    next_state=bytearray(uc.mem_read(state,104));struct.pack_into('>H',next_state,12,33);struct.pack_into('>I',next_state,100,zlib.crc32(next_state[:100]));uc.mem_write(state,bytes(next_state))
    if run(sym['gr2_configuration_publish'],state,records)!=1:raise RuntimeError('effect name configuration update failed')
    retained=[run(sym['gr2_allocate'],size) for size in (available-4096,0xe00)]
    if not all(retained):raise RuntimeError(f'effect name low-memory fixture did not retain its bounded blocks: pointers={retained} free={free()} available={available}')
    low_memory_rejected=run(sym['gr2_effect_names_refresh'])==0 and caption(112,1)==initial[0] and tables()==installed
    for pointer in retained:run(sym['gr2_release'],pointer)
    if run(sym['gr2_effect_names_refresh'])!=1:raise RuntimeError('effect name update failed')
    updated=caption(112,1);stable=pointers==[[word(row+4*(identity-1)) for identity in ids] for row in rows]
    target=rows[0]+4*(ids[0]-1);own=word(target);uc.mem_write(target,struct.pack('>I',0xdeadbeef));foreign=tables()
    rejected=run(sym['gr2_effect_names_refresh'])==0 and run(sym['gr2_effect_names_restore'])==0 and tables()==foreign
    uc.mem_write(target,struct.pack('>I',own));restored=run(sym['gr2_effect_names_restore'])==1 and tables()==original
    run(sym['gr2_configuration_clear'])
    return dict(low_memory_rejected=low_memory_rejected,languages=21,aliases=7,initial_names=initial,all_languages_match=match,stable_pointers=stable,updated_first_name=updated,
                unrelated_labels_preserved=unrelated,foreign_change_rejected=rejected,all_original_tables_restored=restored,pool_restored=free()==available,
                helpers_intercepted=[],hardware_tested=False,scope='Original explicit-language stock accessor, 21 complete pointer tables, native label buffers and actual RTOS pool/mutex; no native screen pixels, hardware display or cached widget redraw proof.')

def probe_producer_iq(code:bytes,disk:bytes,*,native_runtime:dict|None=None,tone:int=0,deep:bool=False,active_configuration:bool=False)->dict:
    """Original IQ library constructor/parser and full capture producer body.

    Only ISP engine completion is substituted. The complete official IQ and
    COMMON files feed the original relocator, lookup and color-profile code.
    """
    import hashlib
    if hashlib.sha256(disk).hexdigest()!='9e0d291f5b9b74f76a2dd269c4b23fe8f524b5db92b86bf82150d5dc3096abf8':raise ValueError('exact GR II official resource component identity required')
    if type(tone) is not int or not 0<=tone<=20:raise ValueError('stock frame color mode required')
    if active_configuration and (native_runtime is None or deep):raise ValueError('active configuration fixture requires native runtime and unmixed mutex evidence')
    resources={}
    for index in range(121):
        at=0x786000+index*64;name=disk[at:at+32].split(b'\0',1)[0].decode('ascii');offset,size=struct.unpack_from('>2I',disk,at+32)
        if name in ('A:/isp/IQ.bin','A:/isp/COMMON.BIN'):
            start=512+offset
            if start>len(disk) or size>len(disk)-start:raise ValueError('official ISP resource extent differs')
            resources[name]=disk[start:start+size]
    iq=resources['A:/isp/IQ.bin'];common=resources['A:/isp/COMMON.BIN']
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code)
    for address,size in ((0x51000000,0x10000),(0x52000000,0x10000),(0x53000000,0x100000),(0x54000000,0x40000),(0x55000000,4096)):uc.mem_map(address,size)
    uc.mem_write(0x52000000,(bytes(20)+bytes.fromhex('ffffffff'))*0x383);uc.mem_write(0x52006000,(bytes(4)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x52000000,0x50005000,0x383));uc.mem_write(0x50005000,struct.pack('>6I',0,0x52006000,0x383,0x5000D000,0,0))
    context=0x51000008;arena=0x53000010;stack=0x50018000;stop=0x5001f000;captured=[];engine_modes=[];requests=[];responses=[];hardware=[];mutex_calls=[]
    uc.mem_write(arena-16,b'\xa5'*16);uc.mem_write(arena+0x80000,b'\xa5'*16)
    uc.mem_write(0x54000000,iq);uc.mem_write(0x55000000,common)
    response=b''.join(struct.pack('>H',0x1200+i) for i in range(33))
    def boundary(machine,address,size,unused):
        if address==0xA02AD6F0:
            responses.append(bytes(machine.mem_read(requests[-1]+0x54,66)));return
        if address in (0xA0027360,0xA00273A4):mutex_calls.append(hex(address))
        elif address==0xA013B4F0:hardware.append(bytes(machine.mem_read(machine.reg_read(r.UC_ARM_REG_R0),128)))
        elif address==0xA0130D72:
            request=machine.reg_read(r.UC_ARM_REG_R0);requests.append(request);captured.append(bytes(machine.mem_read(request,152)));engine_modes.append(bytes(machine.mem_read(context+0x408,1))[0])
            if deep:return
            machine.mem_write(request+0x54,response)
        else:raise RuntimeError('original IQ/producer assertion')
        machine.reg_write(r.UC_ARM_REG_R0,0);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    boundaries=(0xA0130D72,0xA02AD6F0,0xA0039F9C,0xA003A01A)+((0xA013B4F0,0xA0027360,0xA00273A4) if deep else ())
    for address in boundaries:uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    def run(entry,*args,thumb=True):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3),args):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_SP,stack);uc.reg_write(r.UC_ARM_REG_LR,stop|1 if thumb else stop)
        uc.emu_start(entry|1 if thumb else entry,stop,count=5000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=stack:raise RuntimeError('original IQ/producer stack or instruction budget failure')
        return uc.reg_read(r.UC_ARM_REG_R0)
    constructor=run(0xA014DDE8,arena);loaded=run(0xA01507CC,0,0x54000000,0x55000000)
    for offset,handle,data in ((0x1e0,0x5000A000,0x68000000),(0x1f0,0x5000A100,0x60000000)):
        uc.mem_write(context+offset,struct.pack('>I',handle));uc.mem_write(handle,b'BUFF'+struct.pack('>5I',data,256,0,0,256))
    for offset,value in ((0x258,(4<<16)|32),(0x3e4,(4<<16)|32),(0x2b8,32),(0x2bc,4)):uc.mem_write(context+offset,struct.pack('>I',value))
    uc.mem_write(context+0x408,bytes([tone]));snapshot_valid=None
    if native_runtime:
        uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
        block=0xfb94
        uc.mem_write(context-8,b'IMG '+bytes(4));uc.mem_write(0xA0129C54,struct.pack('>I',0xA05FB0E8));uc.mem_write(0xA01137EC,struct.pack('>I',block-8))
        uc.mem_write(0xA05FB0E8,b'MPL '+struct.pack('>4I',0x01000000,block,60*block,0)+struct.pack('>2H',1,0))
        uc.mem_write(0xA00B5BFC,struct.pack('>H',1));uc.mem_write(0xA00B5BDC,struct.pack('>I',0x50008000))
        uc.mem_write(0x50008000,struct.pack('>6I',0xffffffff,0x51000000,0,60*block,block,0x51000000))
        run(native_runtime['symbols']['m10v_library_init'],0x50006000,thumb=False)
        if active_configuration:
            uc.mem_write(0xA00B5BFE,struct.pack('>H',1));uc.mem_write(0xA00B5BE0,struct.pack('>I',0x50007000));uc.mem_write(0x50007000,struct.pack('>h',-2));run(0xA0024BCA)
            uc.mem_write(0xA00B5BF8,struct.pack('>h',2));uc.mem_write(0xA00B5BD4,struct.pack('>I',0x50009000))
            for index in range(2):uc.mem_write(0x50009000+14*index,struct.pack('>h',-2))
            uc.mem_write(0xA06B6DE0,b'\x01');uc.mem_write(0xA06B6DE3,b'\x01');uc.mem_write(0xA00C22C0,struct.pack('>h',1))
            task=0xA05F5C28+68;uc.mem_write(task+8,struct.pack('>2h',-1,-1));uc.mem_write(task+24,struct.pack('>3h',20,0,20))
            if run(native_runtime['symbols']['gr2_configuration_publish'],0x50006000,0x50006200,thumb=False)!=1:raise RuntimeError('native initial configuration publication failed')
            uc.mem_write(0xA02AD48C,bytes.fromhex(native_runtime['producer_hook_patch_hex']))
            result=run(0xA02AD48A,context,0)
        else:result=run(native_runtime['symbols']['gr2_producer_run'],context,0,0x50006000,1234,thumb=False)
        snapshot_valid=run(native_runtime['symbols']['gr2_frame_read'],context,0x50006080,thumb=False)
    else:result=run(0xA02AD48A,context,0)
    if len(captured)!=1 or len(responses)!=1 or (deep and len(hardware)!=1):raise RuntimeError('original producer engine request/response count differs')
    raw,yuv=struct.unpack_from('>2I',captured[0]);frame=struct.unpack_from('>I',captured[0],0x48)[0]
    return dict(hardware_mode=hardware[0][0] if hardware else None,hardware_raw_address=struct.unpack_from('>I',hardware[0],4)[0] if hardware else None,hardware_yuv_address=struct.unpack_from('>I',hardware[0],8)[0] if hardware else None,computed_response_nonzero=any(responses[0]),mutex_boundaries=len(mutex_calls),engine_mode=engine_modes[0],restored_mode=bytes(uc.mem_read(context+0x408,1))[0],snapshot_valid=snapshot_valid,iq_bytes=len(iq),common_bytes=len(common),constructor_return=constructor,load_return=loaded,
                library_ready=struct.unpack('>I',uc.mem_read(arena,4))[0],raw_address=raw,yuv_address=yuv,frame_address=frame,
                producer_return=result,request_hex=captured[0].hex(),response_copied=bytes(uc.mem_read(context+0xf730,66))==responses[0],
                source_resources_unchanged=bytes(uc.mem_read(0x54000000,len(iq)))==iq and bytes(uc.mem_read(0x55000000,len(common)))==common,
                arena_guards_unchanged=all(bytes(uc.mem_read(address,16))==b'\xa5'*16 for address in (arena-16,arena+0x80000)),
                stack_preserved=uc.reg_read(r.UC_ARM_REG_SP)==stack,helpers_intercepted=['mutex lock/unlock','ISP hardware pipeline'] if deep else ['ISP engine completion'],hardware_tested=False,
                scope='Original IQ constructor, official IQ/COMMON parsing and relocation, profile lookups, full A02AD48A request construction and returned matrix copy. Synthetic metadata/no-observer property bank and bounded arena; completion or deeper hardware pipeline and mutex operations are explicit boundaries; deep mode executes A0130D72 and original IQ calculations, no sensor/DMA/IRQ or peak-memory proof.')

def probe_isp_color_recipe(code:bytes,tone:int,*,native_runtime:dict|None=None)->dict:
    """Original frame->ISP color descriptor, including software-float helpers.

    No function interception. A no-observer global property bank supplies the
    initialized service dependency; synthetic image metadata is not DMA input.
    """
    if type(tone) is not int or not 0<=tone<=20:raise ValueError('stock frame color mode required')
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);uc.mem_map(0x51000000,0x10000);uc.mem_map(0x52000000,0x10000)
    uc.mem_write(0x52000000,(bytes(20)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0x52006000,(bytes(4)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x52000000,0x50005000,0x383))
    uc.mem_write(0x50005000,struct.pack('>6I',0,0x52006000,0x383,0x5000D000,0,0))
    context=0x51000008;output=0x50002008;aux=0x50004000;stack=0x50018000;stop=0x5001f000
    def run_native(name,*args):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3),args):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_SP,stack);uc.reg_write(r.UC_ARM_REG_LR,stop)
        uc.emu_start(native_runtime['symbols'][name],stop,count=100000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=stack:raise RuntimeError('native producer preparation stack/budget failure')
        return uc.reg_read(r.UC_ARM_REG_R0)
    uc.mem_write(context+0x408,bytes([tone]));native_prepare=None;native_restore=None
    if native_runtime:
        uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
        block=0xfb94
        uc.mem_write(context-8,b'IMG '+bytes(4));uc.mem_write(0xA0129C54,struct.pack('>I',0xA05FB0E8));uc.mem_write(0xA01137EC,struct.pack('>I',block-8))
        uc.mem_write(0xA05FB0E8,b'MPL '+struct.pack('>4I',0x01000000,block,60*block,0)+struct.pack('>2H',1,0))
        uc.mem_write(0xA00B5BFC,struct.pack('>H',1));uc.mem_write(0xA00B5BDC,struct.pack('>I',0x50008000))
        uc.mem_write(0x50008000,struct.pack('>6I',0xffffffff,0x51000000,0,60*block,block,0x51000000))
        run_native('m10v_library_init',0x50006000)
        native_prepare=run_native('gr2_producer_ingress',context,0x50006000,1234)
    before=bytes(uc.mem_read(context,0xfb0c))
    uc.mem_write(output-8,b'\xa5'*80);uc.mem_write(aux-8,b'\xa5'*28)
    def assertion(*args):raise RuntimeError('original ISP color recipe assertion')
    uc.hook_add(UC_HOOK_CODE,assertion,begin=0xA0039F9C,end=0xA0039F9C)
    for register,value in ((r.UC_ARM_REG_R0,context),(r.UC_ARM_REG_R1,output),(r.UC_ARM_REG_R2,aux),(r.UC_ARM_REG_R3,0),(r.UC_ARM_REG_SP,stack),(r.UC_ARM_REG_LR,stop|1)):uc.reg_write(register,value)
    uc.emu_start(0xA0141E69,stop,count=100000)
    if uc.reg_read(r.UC_ARM_REG_PC)!=stop:raise RuntimeError('original ISP color descriptor execution budget exceeded')
    descriptor=bytes(uc.mem_read(output,64));unchanged=bytes(uc.mem_read(context,0xfb0c))==before
    if native_runtime:native_restore=run_native('gr2_producer_leave',context)
    return dict(native_prepare=native_prepare,native_restore=native_restore,restored_mode=bytes(uc.mem_read(context+0x408,1))[0],color_mode=tone,recipe=descriptor[5],monochrome=descriptor[17],descriptor_hex=descriptor.hex(),aux_hex=bytes(uc.mem_read(aux,12)).hex(),
                context_unchanged=unchanged,
                output_guards_unchanged=all(bytes(uc.mem_read(at,8))==b'\xa5'*8 for at in (output-8,output+64,aux-8,aux+12)),
                stack_preserved=uc.reg_read(r.UC_ARM_REG_SP)==stack,helpers_intercepted=[],hardware_tested=False,
                scope='Original A0141E68 frame color-mode +408 dispatch, complete 64-byte descriptor and auxiliary output, original software-float and property helpers. Synthetic metadata and initialized no-observer property bank; no ISP hardware or neutralization hook installation.')

def probe_image_object_pools(code:bytes,*,extra:int=0,native_runtime:dict|None=None,custom_record:bytes|None=None)->dict:
    """Original fixed-block image pool/factory/clone/retirement CPU evidence.

    Extra bytes change only the size table in synthetic RAM. Mutex operations
    are explicit single-thread boundaries; MPF arithmetic and object ownership
    helpers, property setters, zeroing/copying and releases execute unchanged.
    """
    if type(extra) is not int or not 0<=extra<=16384 or extra&3:raise ValueError('bounded aligned synthetic inline extension required')
    if custom_record is not None and (not native_runtime or extra!=128+12288 or len(custom_record)!=12288):raise ValueError('native runtime and complete inline custom record required')
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);uc.mem_map(0xA1000000,0x400000);stop=0x5001f000;stack=0x50018000
    word=lambda address:struct.unpack('>I',uc.mem_read(address,4))[0]
    for maximum,pointer,table,count,stride in ((0xA00B5BFE,0xA00B5BE0,0x50007000,1,28),(0xA00B5BFC,0xA00B5BDC,0x50008000,2,24)):
        uc.mem_write(maximum,struct.pack('>H',count));uc.mem_write(pointer,struct.pack('>I',table))
        for index in range(count):uc.mem_write(table+index*stride,struct.pack('>h',-2))
    def run(entry,*args,thumb=True):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3),args):uc.reg_write(register,value)
        for index,value in enumerate(args[4:]):uc.mem_write(stack+4*index,struct.pack('>I',value))
        uc.reg_write(r.UC_ARM_REG_SP,stack);uc.reg_write(r.UC_ARM_REG_LR,stop|1 if thumb else stop)
        uc.emu_start(entry|1 if thumb else entry,stop,count=3000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=stack:raise RuntimeError('original fixed-pool/factory budget or stack failure')
        return uc.reg_read(r.UC_ARM_REG_R0)
    run(0xA0024BCA);pool_creates=[];mutex_calls=[]
    def boundary(machine,address,size,context):
        if address==0xA0024E16:
            pool_creates.append([machine.reg_read(register) for register in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2)]);return
        if address in (0xA0039F9C,0xA003A01A):raise RuntimeError('original fixed-pool/factory assertion')
        mutex_calls.append(hex(address));machine.reg_write(r.UC_ARM_REG_R0,0x50009000 if address==0xA0027270 else 0)
        machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    for address in (0xA0024E16,0xA0027270,0xA0027360,0xA00273A4,0xA0039F9C,0xA003A01A):uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    if extra:uc.mem_write(0xA01137EC,struct.pack('>I',0xfb0c+extra))
    run(0xA00E1DF0)
    linear_base=run(0xA00542D0);linear_limit=linear_base+run(0xA00542D4)-0x40000
    linear_cursor=word(0xA00C2BA4)
    uc.mem_map(0x51000000,0x10000)
    uc.mem_write(0x51000000,(bytes(20)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0x51006000,(bytes(4)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x51000000,0x50003000,0x383))
    uc.mem_write(0x50003000,struct.pack('>6I',0,0x51006000,0x383,0x5000D000,0,0))
    source=run(0xA029B4E0,0);header=bytes(uc.mem_read(source-8,8));payload_bytes=0xfb0c+extra
    if native_runtime:uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
    owner_entry=native_runtime['symbols']['gr2_image_owner_bytes'] if native_runtime else None
    constructor_zeroed=bytes(uc.mem_read(source,payload_bytes))==b'\x01'+bytes(payload_bytes-1)
    count_after=word(0x5000D000+0x347*4)
    frame_clone={}
    if owner_entry and extra in (128,128+12288):
        run(native_runtime['symbols']['m10v_library_init'],0x50002000,thumb=False)
        if custom_record is not None:
            import zlib
            uc.mem_map(0x56000000,0x4000);uc.mem_write(0x56000000,custom_record)
            state=bytearray(uc.mem_read(0x50002000,104));struct.pack_into('>H',state,28,struct.unpack_from('<I',custom_record,8)[0]);state[78]=1;struct.pack_into('>I',state,100,zlib.crc32(state[:100]));uc.mem_write(0x50002000,bytes(state))
            frame_clone['freeze']=run(native_runtime['symbols']['gr2_frame_freeze_custom'],source,0x50002000,2,0x12345678,0x56000000,thumb=False)
        else:frame_clone['freeze']=run(native_runtime['symbols']['gr2_frame_freeze'],source,0x50002000,2,0x12345678,thumb=False)
    elif extra:uc.mem_write(source+0xfb0c,b'\xa5'*extra)
    original=bytes(uc.mem_read(source,payload_bytes));clone=run(0xA029B57C if owner_entry else 0xA00E1E9E,source)
    clone_matches=bytes(uc.mem_read(clone,payload_bytes))==original
    inline_cloned=not extra or bytes(uc.mem_read(clone+0xfb0c,extra))==original[0xfb0c:]
    if frame_clone:
        uc.mem_write(0x50002000,b'\xa5'*104)
        if custom_record is not None:uc.mem_write(0x56000000,b'\xa5'*12288)
        frame_clone['read']=run(native_runtime['symbols']['gr2_frame_read'],clone,0x50003080,thumb=False)
        frame_clone['matches']=bytes(uc.mem_read(0x50003080,128))==original[0xfb0c:0xfb8c]
        if custom_record is not None:frame_clone['custom_record_matches']=bytes(uc.mem_read(clone+0xfb8c,12288))==custom_record
    owner_live=[];owner_rejected=[];owner_retired=[]
    if owner_entry:
        owner_live=[run(owner_entry,pointer,thumb=False) for pointer in (source,clone)]
        uc.mem_write(0x50005000,b'IMG '+bytes(4))
        owner_rejected=[run(owner_entry,pointer,thumb=False) for pointer in (source+4,clone+4,0x50005008,source+60*(payload_bytes+8))]
        uc.mem_write(0xA01137EC,struct.pack('>I',payload_bytes+4));owner_rejected.append(run(owner_entry,source,thumb=False));uc.mem_write(0xA01137EC,struct.pack('>I',payload_bytes))
        uc.mem_write(0x50008010,struct.pack('>I',payload_bytes+12));owner_rejected.append(run(owner_entry,source,thumb=False));uc.mem_write(0x50008010,struct.pack('>I',payload_bytes+8))
    if owner_entry:
        uc.mem_write(0x50004004,struct.pack('>I',clone));run(0xA029B522,0x50004004)
    else:run(0xA00E2020,clone)
    uc.mem_write(0x50004000,struct.pack('>I',source));run(0xA029B522,0x50004000)
    retired_slot_cleared=word(0x50004000)==0;count_retired=word(0x5000D000+0x347*4)
    if owner_entry:owner_retired=[run(owner_entry,pointer,thumb=False) for pointer in (source,clone)]
    # MPF links overwrite the poison word after the generic free marks 'void'.
    # Assert the actual released header is no longer live, not a retained tag.
    invalid=bytes(uc.mem_read(source-8,4))!=b'IMG ' and bytes(uc.mem_read(clone-8,4))!=b'IMG '
    allocated=[];allocation_results=[]
    for index in range(61):
        value=run(0xA00674B0,1,0x50001000,thumb=False);allocation_results.append(value)
        if value&0x80000000:break
        allocated.append(word(0x50001000))
    else:raise RuntimeError('original fixed pool exceeded its declared count')
    released=[run(0xA0067640,1,pointer,thumb=False) for pointer in allocated]
    again=run(0xA00674B0,1,0x50001000,thumb=False);again_pointer=word(0x50001000)
    final_release=run(0xA0067640,1,again_pointer,thumb=False) if again==0 else 0xffffffff
    return dict(linear_region_base=linear_base,linear_region_limit=linear_limit,linear_cursor_after_pools=linear_cursor,
                pools_within_linear_region=all(linear_base<=address and address+count*block<=linear_limit for address,count,block in pool_creates),
                pools_exclude_runtime=all(address>=0xA0800000 or address+count*block<=0xA0798000 for address,count,block in pool_creates),
                native_frame_clone=frame_clone,native_owner_live=owner_live,native_owner_rejected=owner_rejected,native_owner_retired=owner_retired,pool_counts=[row[1] for row in pool_creates],pool_block_bytes=[row[2] for row in pool_creates],
                pool_data=[hex(row[0]) for row in pool_creates],inline_extra=extra,constructor_zeroed=constructor_zeroed,
                header_magic=header[:4].decode('ascii'),object_kind=struct.unpack_from('>I',header,4)[0],
                source=hex(source),clone=hex(clone),counter_after_construct=count_after,clone_matches=clone_matches,
                inline_extension_cloned=inline_cloned,freed_magic_invalid=invalid,counter_after_retirement=count_retired,
                retired_slot_cleared=retired_slot_cleared,exhausted_return=allocation_results[-1],unique_blocks=len(set(allocated)),
                all_blocks_released=len(allocated)==60 and released==[0]*60 and again==0 and final_release==0,
                stack_preserved=uc.reg_read(r.UC_ARM_REG_SP)==stack,mutex_calls=len(mutex_calls),helpers_intercepted=['mutex create/lock/unlock'],hardware_tested=False,
                scope='Original image fixed-pool initialization, MPF create/allocate/free, type0 factory/property count, zeroing, clone and slot retirement. Synthetic kernel tables, no-observer property bank, mutex boundaries and optional RAM-only size-table extension; no firmware patch, capture concurrency or peak-memory proof.')

def probe_memory_regions(code:bytes,sizes:list[int])->dict:
    """Original region initialization and bump allocator; only RTOS pool creation is synthetic."""
    official_profile(code,'gr2')
    if not sizes or any(type(n) is not int or not 0<n<=0x10000 for n in sizes):raise ValueError('small positive region sizes required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=runtime_machine(code);calls=[];stop=0x5001f000
    def boundary(uc,address,size,ctx):
        if address!=0xA0067794:raise RuntimeError('original region allocator assertion')
        descriptor=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0),16));calls.append(struct.unpack('>4I',descriptor))
        uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    for address in (0xA0067794,0xA0039F9C,0xA003A01A):machine.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    def run(entry,first=0,second=0):
        for reg,value in ((UC_ARM_REG_R0,first),(UC_ARM_REG_R1,second),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
            machine.reg_write(reg,value)
        machine.emu_start(entry|1,stop,count=10000)
        if machine.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('region allocator exceeded execution budget')
        return machine.reg_read(UC_ARM_REG_R0)
    base=run(0xA00542D0)
    machine.mem_write(base-4,b'\xa5'*4)
    run(0xA0024BCA)
    header=struct.unpack('>3I',machine.mem_read(base,12))
    allocated=[];guards=[]
    for size in sizes:
        address=run(0xA0024B68,size,0x50001000);allocated.append(address)
        machine.mem_write(address,b'\xa5'*size);guards.append((address,size))
    return dict(region_base=base,pool_data=header[1],pool_bytes=header[2],pool_create_calls=len(calls),
                allocated=allocated,guards_unchanged=bytes(machine.mem_read(base-4,4))==b'\xa5'*4 and all(bytes(machine.mem_read(a,n))==b'\xa5'*n for a,n in guards),
                private_gap_proved=False,hardware_tested=False,helpers_intercepted=['RTOS pool creation'],
                scope='Original region base getter, initial 2MiB pool reservation and bump alignment/metadata; no ownership claim for lower RAM gap.')

def probe_task_context(code:bytes)->dict:
    """Execute the original ARM task-frame constructor, without scheduler stubs."""
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);base=0x50004000;stop=0x5001f000
    uc.mem_write(base-4,b'\xa5'*88)
    for register,value in ((UC_ARM_REG_R0,0xA02AE5C1),(UC_ARM_REG_R1,0x50008000),(UC_ARM_REG_R2,base),(UC_ARM_REG_LR,stop)):
        uc.reg_write(register,value)
    uc.emu_start(0xA00AF7A8,stop,count=1000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('task frame construction budget exceeded')
    words=struct.unpack('>20I',uc.mem_read(base,80))
    return dict(entry='0xa00af7a8',scheduler_cpsr=words[0],initial_task_cpsr=words[1],frame=list(words),
                guards_unchanged=bytes(uc.mem_read(base-4,4))==b'\xa5'*4 and bytes(uc.mem_read(base+80,4))==b'\xa5'*4,
                helpers_intercepted=[],hardware_tested=False,
                scope='Original initial task-frame construction. Actual capture task identity and live exception-vector installation still need validation.')

def probe_memory_policy(code:bytes,*,boot_mode:int=0)->dict:
    """Observe original MPU/cache register programming, not a hardware cache simulation."""
    official_profile(code,'gr2')
    if type(boot_mode) is not int or not 0<=boot_mode<=4:raise ValueError('bounded boot mode required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);registers={};writes=[];stop=0x5001f000
    def observe(machine,address,size,ctx):
        if address==0xA0040D5E:
            machine.reg_write(UC_ARM_REG_R0,boot_mode);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR));return
        word=struct.unpack('>I',machine.mem_read(address,4))[0]
        if word&0x0f000f10!=0x0e000f10:return
        if (word>>12)&15:raise ValueError('unexpected original CP15 transfer register')
        key=((word>>21)&7,(word>>16)&15,word&15,(word>>5)&7)
        if word&(1<<20):machine.reg_write(UC_ARM_REG_R0,registers.get(key,0))
        else:
            value=machine.reg_read(UC_ARM_REG_R0);registers[key]=value;writes.append(dict(pc=hex(address),register=list(key),value=value))
        machine.reg_write(UC_ARM_REG_PC,address+4)
    uc.hook_add(UC_HOOK_CODE,observe,begin=0xA00AF200,end=0xA00AF3C0)
    uc.hook_add(UC_HOOK_CODE,observe,begin=0xA0040D5E,end=0xA0040D5E)
    uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop)
    uc.emu_start(0xA00AF200,stop,count=10000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('original memory policy execution budget exceeded')
    return dict(entry='0xa00af200',boot_mode=boot_mode,regions=[registers[(0,6,i,0)] for i in range(8)],
                instruction_cache_mask=registers[(0,2,0,1)],data_cache_mask=registers[(0,2,0,0)],
                write_buffer_mask=registers[(0,3,0,0)],control=registers[(0,1,0,0)],writes=writes,
                hardware_cache_emulated=False,helpers_intercepted=['boot mode getter','CP15 read/write register boundaries'],
                scope='Original register-value arithmetic and branches, synthetic CP15 initial values. No cache contents, physical address aliases or DMA coherence simulation.')

def probe_raw_for_dng(code:bytes,*,present:bool)->dict:
    """Run original named imgProp RAW-for-DNG assertion against synthetic property RAM."""
    official_profile(code,'gr2')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
    uc=runtime_machine(code);stack=0x50010000;context=0x50004000;asserted=False;continued=False;messages=[]
    uc.mem_write(stack+0x18,struct.pack('>I',context));uc.mem_write(context+0x1e4,struct.pack('>I',0x50008000 if present else 0))
    def observe(machine,address,size,ctx):
        nonlocal asserted,continued
        if address==0xA0162C9E:continued=True;machine.emu_stop();return
        if address==0xA003A01A:asserted=True;machine.emu_stop();return
        pointer=machine.reg_read(UC_ARM_REG_R0)
        messages.append(bytes(machine.mem_read(pointer,128)).split(b'\0',1)[0].decode('ascii'))
        machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA0162C9E,0xA0039F9C,0xA003A01A):uc.hook_add(UC_HOOK_CODE,observe,begin=address,end=address)
    uc.reg_write(UC_ARM_REG_SP,stack);uc.emu_start(0xA0162C7D,0,count=1000)
    return dict(entry='0xa0162c7c',handle_offset=0x1e4,asserted=asserted,reached_continuation=continued,
                assertion_text=' '.join(messages),helpers_intercepted=['diagnostic log','panic stop'],hardware_tested=False,
                scope='Original named imgProp->bufferInfo.hRawForDng null assertion; property address and handle are synthetic.')

def probe_isp_completion_wait(code:bytes)->dict:
    """Stock ISP wait adapter with explicit synthetic RTOS event boundaries."""
    official_profile(code,'gr2')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stack=0x50018000;stop=0x5001f000;output=0x50004000;calls={}
    def boundary(machine,address,size,ctx):
        if address==0xA00686C4:
            calls.update(event_id=machine.reg_read(UC_ARM_REG_R0),requested_bits=machine.reg_read(UC_ARM_REG_R1),wait_mode=machine.reg_read(UC_ARM_REG_R2))
            machine.mem_write(machine.reg_read(UC_ARM_REG_R3),struct.pack('>I',0x91))
        else:
            calls.update(clear_event_id=machine.reg_read(UC_ARM_REG_R0),clear_mask=machine.reg_read(UC_ARM_REG_R1))
        machine.reg_write(UC_ARM_REG_R0,0);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA00686C4,0xA0067F8C):uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    for reg,value in ((UC_ARM_REG_R0,output),(UC_ARM_REG_R1,0x11),(UC_ARM_REG_R2,0xffffffff),(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop|1)):uc.reg_write(reg,value)
    uc.emu_start(0xA010C465,stop,count=10000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('ISP wait execution budget exceeded')
    return dict(**calls,observed_bits=struct.unpack('>I',uc.mem_read(output,4))[0],returned=uc.reg_read(UC_ARM_REG_R0),
                stack_preserved=uc.reg_read(UC_ARM_REG_SP)==stack,hardware_tested=False,
                helpers_intercepted=['RTOS wait-event result','RTOS clear-event result'],
                scope='Original ISP completion adapter masks unrelated event bits before clearing and publishing; no real interrupt or DMA execution.')

def probe_main_yuv_handoff(code:bytes)->dict:
    """Execute the stock equal-dimension producer-to-main-JPEG handoff.

    Only the buffer-kind capacity service is synthetic. This is not proof of
    ISP completion: the upstream producer is deliberately outside this probe.
    """
    official_profile(code,'gr2')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);context=0x50004000;handle=0x50008000
    width,height=4928,3264;length=width*height*2;stop=0x5001f000;stack=0x50018000
    uc.mem_write(handle,b'BUFF'+struct.pack('>5I',0x60000000,0,0,0,length))
    uc.mem_write(context+0x1f0,struct.pack('>I',handle))
    for offset in (0x258,0x3e4):uc.mem_write(context+offset,struct.pack('>I',(height<<16)|width))
    kinds=[]
    def boundary(machine,address,size,ctx):
        kinds.append(machine.reg_read(UC_ARM_REG_R0))
        machine.reg_write(UC_ARM_REG_R0,length)
        machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE,boundary,begin=0xA029AB3C,end=0xA029AB3C)
    uc.reg_write(UC_ARM_REG_R0,context);uc.reg_write(UC_ARM_REG_SP,stack);uc.reg_write(UC_ARM_REG_LR,stop|1)
    uc.emu_start(0xA02AE0AF,stop,count=10000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('YUV handoff execution budget exceeded')
    return dict(entry='0xa02ae0ae',source_offset=0x1f0,destination_offset=0x1f4,
                source_cleared=bytes(uc.mem_read(context+0x1f0,4))==bytes(4),
                same_handle=struct.unpack('>I',uc.mem_read(context+0x1f4,4))[0]==handle,
                used_before=0,used_after=struct.unpack('>I',uc.mem_read(handle+8,4))[0],
                queried_buffer_kinds=kinds,stack_preserved=uc.reg_read(UC_ARM_REG_SP)==stack,
                helpers_intercepted=['buffer-kind capacity lookup'],hardware_tested=False,
                scope='Original equal-dimension handle move and BUFF valid-length setter; synthetic capacity, no ISP/DMA execution.')

def probe_capture_owner(code:bytes,kind:int,*,complete:bool=False)->dict:
    """Original per-image encode owner constructs the real wrapper descriptor.

    Uses synthetic reference-counted image/JPEG handles. Getters and descriptor
    construction execute unchanged; quality/settings services are boundaries.
    """
    official_profile(code,'gr2')
    if kind not in (1,2,3):raise ValueError('original image kind 1..3 required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);context=0x50004000;source_handle=0x50008000;output_handle=0x50008100
    width,height=((4928,3264),(1280,848),(160,120))[kind-1]
    source_offset=(0x1f4,0x1fc,0x200)[kind-1];output_offset=(0x204,0x208,0x20c)[kind-1]
    source=0x60000000;output=0x64000000;image_bytes=width*height*2
    # Read the original handle magic literal, not an invented object tag.
    magic=bytes(uc.mem_read(0xA00E08C8,4))
    for handle,address,size in ((source_handle,source,image_bytes),(output_handle,output,0x1000000)):
        uc.mem_write(handle,magic+struct.pack('>5I',address,size,0,0,size))
    uc.mem_write(context+source_offset,struct.pack('>I',source_handle));uc.mem_write(context+output_offset,struct.pack('>I',output_handle))
    uc.mem_write(context+0x3e0+kind*4,struct.pack('>I',(height<<16)|width));uc.mem_write(context+0x400,b'\x02')
    captured=None;getter_calls=0;lifetime=[]
    if complete:
        if kind not in (1,3):raise ValueError('outer lifetime callers currently proved for image kinds 1 and 3')
        uc.mem_map(output,0x1000)
    def boundary(machine,address,size,ctx):
        nonlocal captured,getter_calls
        if address==0xA00E0714:getter_calls+=1;return # observe original handle checks/getter
        if address==0xA01324BA:
            captured=bytes(machine.mem_read(machine.reg_read(UC_ARM_REG_R0),48))
            if not complete:machine.emu_stop();return
            lifetime.append('encoder_enter');machine.mem_write(machine.reg_read(UC_ARM_REG_R0)+0x28,struct.pack('>I',512));lifetime.append('encoder_return')
            machine.reg_write(UC_ARM_REG_R0,0);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR));return
        if address==0xA029AA1A:
            pointer=machine.reg_read(UC_ARM_REG_R0)
            if pointer!=context+source_offset:raise RuntimeError('unexpected source release slot')
            lifetime.append('source_release');machine.mem_write(pointer,bytes(4))
            machine.reg_write(UC_ARM_REG_R0,0);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR));return
        if address in (0xA0039F9C,0xA003A01A):raise RuntimeError('original capture handle assertion')
        result=0x2b if address==0xA02ADB7C else 0x100000
        machine.reg_write(UC_ARM_REG_R0,result);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA00E0714,0xA01324BA,0xA02ADB7C,0xA029AB3C,0xA0039F9C,0xA003A01A,*((0xA029AA1A,) if complete else ())):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    uc.reg_write(UC_ARM_REG_R0,context);uc.reg_write(UC_ARM_REG_R1,kind)
    uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,0x5001f001)
    uc.emu_start(({1:0xA02AE5C1,3:0xA02AE611}[kind] if complete else 0xA02ADC15),0x5001f000,count=10000)
    if complete and uc.reg_read(UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('capture lifetime execution budget exceeded')
    if captured is None:raise RuntimeError('original capture owner did not reach JPEG wrapper')
    dims=struct.unpack_from('>I',captured,8)[0]
    return dict(entry='0xa02adc14',kind=kind,source_handle_offset=source_offset,output_handle_offset=output_offset,
                source=struct.unpack_from('>I',captured,0)[0],output=struct.unpack_from('>I',captured,4)[0],
                width=dims&65535,height=dims>>16,source_handle_data=source,source_handle_bytes=image_bytes,
                minimum_planar_bytes=width*height*2,output_handle_data=output,original_handle_getters=getter_calls,
                descriptor_hex=captured.hex(),hardware_tested=False,lifetime_events=lifetime,
                source_cleared_after_encode=bytes(uc.mem_read(context+source_offset,4))==bytes(4),
                stack_preserved=uc.reg_read(UC_ARM_REG_SP)==0x50018000,
                helpers_intercepted=['quality selection','JPEG target-size setting']+(['JPEG encoder completion','source release effect'] if complete else []),
                scope='Original image-kind dispatch and handle validation. Optional original outer caller executes through synthetic synchronous encoder completion and release effect. This proves call order, not producer readiness, kernel concurrency or DMA completion.')

def probe_jpeg_input(code:bytes,width:int,height:int,*,format_kind:int=2,overrides:tuple[int,int,int,int]|None=None)->dict:
    """Run stock still-JPEG wrapper and config builder up to encoder submission.

    Synthetic descriptors, lock/hardware boundaries. Does not access image pixels.
    """
    official_profile(code,'gr2')
    if any(type(n) is not int or not 0<n<=65535 for n in (width,height)):raise ValueError('u16 image dimensions required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=runtime_machine(code);descriptor=0x50001000;intermediate=None;encoder=None;stop=0x5001f000
    original=bytearray(0x30)
    struct.pack_into('>3I',original,0,0x60000000,0x64000000,(height<<16)|width)
    if format_kind not in (2,3,4):raise ValueError('proved input format kind required')
    if overrides is not None and (len(overrides)!=4 or any(type(v) is not int or not 0<=v<=0xffffffff for v in overrides)):
        raise ValueError('four u32 plane/pitch overrides required')
    original[0xc:0xe]=bytes((2,format_kind));struct.pack_into('>I',original,0x10,0x1000000)
    if overrides is not None:struct.pack_into('>4I',original,0x18,*overrides)
    machine.mem_write(descriptor,bytes(original))
    def boundary(uc,address,size,ctx):
        nonlocal intermediate,encoder
        if address==0xA0134D44:
            intermediate=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0),0x30));uc.emu_stop();return
        if address==0xA0107010:
            encoder=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0),0x4c));uc.emu_stop();return
        uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    for address in (0xA01425EE,0xA01067FE,0xA0134D44,0xA010678C,0xA0106854,0xA0106878,0xA0106C56,0xA0107010):
        machine.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    machine.reg_write(UC_ARM_REG_R0,descriptor);machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,stop|1)
    machine.emu_start(0xA01324BB,stop,count=10000)
    if intermediate is None:raise RuntimeError('still-JPEG wrapper did not reach configuration boundary')
    machine.mem_write(0x50002000,intermediate)
    for reg,value in ((UC_ARM_REG_R0,0x50002000),(UC_ARM_REG_R1,2),(UC_ARM_REG_R2,0),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
        machine.reg_write(reg,value)
    machine.emu_start(0xA0134B13,stop,count=10000)
    if encoder is None:raise RuntimeError('JPEG config builder did not reach submission boundary')
    half=lambda offset:struct.unpack_from('>H',encoder,offset)[0]
    word=lambda offset:struct.unpack_from('>I',encoder,offset)[0]
    return dict(wrapper='0xa01324ba',config_builder='0xa0134b12',submission='0xa0107010',
                width=half(4),height=half(6),y_stride=half(0),chroma_stride=half(2),
                y=word(0x18),u=word(0x1c),v=word(0x20),jpeg=word(0x24),subsampling=encoder[0x29],
                input_format=struct.unpack_from('>H',intermediate,0x14)[0],
                wrapper_config_hex=intermediate.hex(),encoder_config_hex=encoder.hex(),
                hardware_encoder_executed=False,hardware_tested=False,
                helpers_intercepted=['ISP lock/status','JPEG reset/config hardware','encoder submission stop'],
                scope='Original wrapper and JPEG configuration field/plane arithmetic only. Producer completion, cache ownership, mode admission and pixel access remain to prove.')

def probe_rtc_get_time(code:bytes,fields:tuple[int,...],*,native_runtime:dict|None=None)->dict:
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
    entry=0xA00341A9
    if native_runtime is not None:
        runtime=bytes.fromhex(native_runtime['runtime_hex']);base=native_runtime['base']
        if base!=0xa0798000 or native_runtime['memory_bytes']>0x68000:raise ValueError('bounded native RTC bridge required')
        machine.mem_map(base,0x68000);machine.mem_write(base,runtime);entry=native_runtime['symbols']['gr2_read_clock']
    machine.emu_start(entry,stop,count=10000)
    if machine.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('RTC wrapper exceeded execution budget')
    result=bytes(machine.mem_read(output,12))
    return dict(entry='0xa00341a8',native_entry=hex(entry) if native_runtime is not None else None,driver_entry='0xa005ae20',fields=list(struct.unpack('>6H',result)),
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

def probe_sd_tell(code:bytes,position:int,*,fail:bool=False)->dict:
    """Execute original normal FILE position copying, including error atomicity."""
    if type(position) is not int or not 0<=position<1<<64:raise ValueError('u64 position required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);handle=0x50004000;out=0x50008004;stop=0x5001f000
    uc.mem_write(handle,b'FILE'+struct.pack('>I',0x50009000)+bytes(8)+b'H:/M10V/FILMS.M10\0');uc.mem_write(out-4,b'\xa5'*16)
    def boundary(machine,address,size,ctx):
        if address in (0xA0039F9C,0xA003A01A):raise RuntimeError('original FILE tell assertion')
        result=0
        if address==0xA0065318:
            if machine.reg_read(UC_ARM_REG_R0)!=0x50009000:raise ValueError('backend tell FILE token differs')
            machine.mem_write(machine.reg_read(UC_ARM_REG_R1),position.to_bytes(8,'big'));result=0xffffffff if fail else 0
        elif address==0xA00652CE:result=31
        elif address==0xA00267BA:result=1
        machine.reg_write(UC_ARM_REG_R0,result);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA002B0EE,0xA0065318,0xA00652CE,0xA00267BA,0xA0039DE4,0xA0039F9C,0xA003A01A):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    for register,value in ((UC_ARM_REG_R0,handle),(UC_ARM_REG_R1,out),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
        uc.reg_write(register,value)
    uc.emu_start(0xA002E39F,stop,count=10000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('FILE tell execution budget exceeded')
    return dict(entry='0xa002e39e',returned=uc.reg_read(UC_ARM_REG_R0),position_hex=bytes(uc.mem_read(out,8)).hex(),
                guards_unchanged=bytes(uc.mem_read(out-4,4))==b'\xa5'*4 and bytes(uc.mem_read(out+8,4))==b'\xa5'*4,
                helpers_intercepted=['media readiness','stdio tell backend','errno/thread id','diagnostic log'],hardware_tested=False,
                scope='Original FILE validation and 64-bit position copy only after backend success; synthetic media/stdio, no disk I/O.')

def probe_sd_seek(code:bytes,offset:int,origin:int,*,fail:bool=False)->dict:
    """Execute normal FILE seek through signed-32 to backend signed-64 ABI."""
    if type(offset) is not int or not -(1<<31)<=offset<(1<<31) or type(origin) is not int or origin not in (0,1,2):
        raise ValueError('signed 32-bit offset and standard origin required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);handle=0x50004000;stop=0x5001f000;observed={}
    uc.mem_write(handle,b'FILE'+struct.pack('>I',0x50008000)+bytes(8)+b'H:/M10V/FILMS.M10\0')
    def boundary(machine,address,size,ctx):
        if address in (0xA0039F9C,0xA003A01A):raise RuntimeError('original FILE seek assertion')
        result=0
        if address==0xA00653A0:
            observed.update(backend_file=machine.reg_read(UC_ARM_REG_R0),offset_high=machine.reg_read(UC_ARM_REG_R2),
                            offset_low=machine.reg_read(UC_ARM_REG_R3),origin=struct.unpack('>I',machine.mem_read(machine.reg_read(UC_ARM_REG_SP),4))[0])
            result=0xffffffff if fail else 0
        elif address==0xA00652CE:result=31
        elif address==0xA00267BA:result=1
        machine.reg_write(UC_ARM_REG_R0,result);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA002B0EE,0xA00653A0,0xA00652CE,0xA00267BA,0xA0039DE4,0xA0039F9C,0xA003A01A):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    for register,value in ((UC_ARM_REG_R0,handle),(UC_ARM_REG_R1,offset&0xffffffff),(UC_ARM_REG_R2,origin),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
        uc.reg_write(register,value)
    uc.emu_start(0xA002E491,stop,count=10000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop or not observed:raise RuntimeError('FILE seek did not complete within budget')
    return dict(entry='0xa002e490',**observed,returned=uc.reg_read(UC_ARM_REG_R0),stack_preserved=uc.reg_read(UC_ARM_REG_SP)==0x50018000,
                helpers_intercepted=['media readiness','stdio seek backend','errno/thread id','diagnostic log'],hardware_tested=False,
                scope='Original normal FILE validation and signed-64 seek argument marshalling; synthetic media/stdio, no disk movement.')

def probe_sd_file_lifecycle(code:bytes,*,native_runtime:dict|None=None,fail_write:bool=False,fail_close:bool=False,read_offset:int|None=None,fail_seek:bool=False,query_size:bool=False,fail_tell:bool=False,reported_size:int|None=None,fail_open:bool=False)->dict:
    """Execute normal open/read/write/close with synthetic stdio, media and metadata pool boundaries."""
    official_profile(code,'gr2')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stop=0x5001f000;control=0xA00C2C6C;pool=0x5000c000
    uc.mem_write(control+0x1c,struct.pack('>I',pool))
    if native_runtime is not None:uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
    path=0x50001000;source=0x50002000;target=0x50003000
    payload=bytes((i*23+19)&255 for i in range(104));name='H:/M10V5A.bin' if read_offset is None and not query_size else 'H:/M10V/FILMS.M10'
    uc.mem_write(path,name.encode()+bytes(1));uc.mem_write(source,payload);uc.mem_write(target,b'\xa5'*105)
    file=bytearray() if read_offset is None and not query_size else bytearray(payload);position=0;file_token=0x5000b000;handles=[];closed=[];freed=[];cleared=True
    def string(pointer):return bytes(uc.mem_read(pointer,32)).split(b'\0',1)[0].decode('ascii')
    def boundary(machine,address,size,ctx):
        nonlocal file,position,cleared
        a,b,c,d=[machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if address in (0xA0039F9C,0xA003A01A):raise RuntimeError(f'original filesystem assertion at {address:x}')
        if address==0xA0065324:
            if string(a)!=name or string(b) not in ('r','w'):raise ValueError('private file open arguments differ')
            if string(b)=='w':file=bytearray()
            position=0;result=0 if fail_open else file_token
        elif address==0xA0024C3C:
            if (a,b)!=(pool,0x38):raise ValueError('file metadata pool allocation differs')
            result=0x50009000+len(handles)*0x100;handles.append(result)
        elif address==0xA0024D76:
            if a!=pool or b not in handles:raise ValueError('file metadata free ownership differs')
            cleared=cleared and bytes(machine.mem_read(b,4))==bytes(4);freed.append(b);result=0
        elif address==0xA0065428:
            if (b,c,d)!=(104,1,file_token):raise ValueError('file write backend items differ')
            data=bytes(machine.mem_read(a,b));file.extend(data[:29] if fail_write else data);position=len(file);result=0 if fail_write else 1
        elif address==0xA0065386:
            if (b,d)!=(1,file_token):raise ValueError('file read backend items differ')
            data=bytes(file[position:position+c]);machine.mem_write(a,data);position+=len(data);result=len(data)
        elif address==0xA00653A0:
            origin=struct.unpack('>I',machine.mem_read(machine.reg_read(UC_ARM_REG_SP),4))[0]
            if a!=file_token or c!=0 or d!=(0 if query_size else read_offset) or origin!=(2 if query_size else 0):raise ValueError('range/size seek contract differs')
            if not fail_seek:position=(len(file) if reported_size is None else reported_size) if query_size else d
            result=0xffffffff if fail_seek else 0
        elif address==0xA0065318:
            if a!=file_token:raise ValueError('size query tell token differs')
            machine.mem_write(b,position.to_bytes(8,'big'));result=0xffffffff if fail_tell else 0
        elif address==0xA00652F0:result=int(position>=len(file))
        elif address==0xA00652E2:
            if a!=file_token:raise ValueError('file close token differs')
            closed.append(a);result=0xffffffff if fail_close else 0
        elif address==0xA00652CE:result=31
        elif address==0xA00267BA:result=1
        else:result=0
        machine.reg_write(UC_ARM_REG_R0,result);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA002B0EE,0xA0027360,0xA00273A4,0xA00A2058,0xA0065324,0xA0024C3C,0xA0024D76,
                    0xA0065428,0xA0065386,0xA00653A0,0xA0065318,0xA00652F0,0xA00652E2,0xA00652CE,0xA00267BA,0xA0039DE4,0xA0039F9C,0xA003A01A):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    def run(entry,args):
        for register,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):uc.reg_write(register,value)
        uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop|1)
        uc.emu_start(entry,stop,count=100000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('file lifecycle execution budget exceeded')
        return uc.reg_read(UC_ARM_REG_R0)
    size_returned=None
    if query_size:
        if native_runtime is None:raise ValueError('size query probe requires compiled bridge')
        written=read=None;size_returned=run(native_runtime['symbols']['gr2_file_size'],[path,target])
    elif read_offset is not None:
        if native_runtime is None:raise ValueError('range read probe requires compiled bridge')
        written=None;read=run(native_runtime['symbols']['gr2_file_read_at'],[path,read_offset,target,105])
    elif native_runtime is None:
        handle=run(0xA002C70F,[path,1]);written=run(0xA002CC4B,[handle,source,len(payload)]);run(0xA002C905,[handle])
        handle=run(0xA002C70F,[path,0]);read=run(0xA002CA99,[handle,target,105]);run(0xA002C905,[handle])
    else:
        symbols=native_runtime['symbols'];written=run(symbols['gr2_file_write'],[path,source,len(payload)]);read=run(symbols['gr2_file_read'],[path,target,105])
    return dict(write_returned=written,read_returned=read,size_returned=size_returned,buffer_hex=bytes(uc.mem_read(target,105)).hex(),payload_matches=bytes(uc.mem_read(target,len(payload)))==payload,
                backend_close_calls=len(closed),metadata_free_calls=len(freed),magic_cleared_before_free=cleared,
                hardware_tested=False,helpers_intercepted=['stdio backend','media readiness/locks','metadata pool allocate/free','errno/thread id','diagnostic log'],
                scope='Original normal-file wrappers and optional compiled private bridge; synthetic media and stdio bytes, no disk I/O.')

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

def probe_menu_descriptor(code:bytes,*,native_runtime:dict)->dict:
    """Compare actual metadata entry before/after its RAM-installed adapter."""
    from unicorn import arm_const as r
    uc=runtime_machine(code);uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x50002000,0x50003000,0x383))
    uc.mem_write(0x50003000,struct.pack('>5I',0,0,0x383,0x5000D000,0))
    context=0x50009000;descriptor=0x50008000;site=0xA039D168;original=bytes(uc.mem_read(site,8));checks=[]
    uc.mem_write(context,struct.pack('>6H',0,0,0,0,720,480))
    def run(identity,language,patched):
        value=bytearray(84);struct.pack_into('>IHH',value,0,identity,100,350);struct.pack_into('>I',value,12,0x40000)
        uc.mem_write(descriptor,bytes(value));uc.mem_write(0x5000D000+0x1e4*4,struct.pack('>I',language))
        uc.mem_write(site,bytes.fromhex(native_runtime['menu_descriptor_hook_patch_hex']) if patched else original);uc.ctl_remove_cache(site,site+8)
        saved=[0x66770000+index for index in range(8)]
        for index,value in enumerate(saved):uc.reg_write(r.UC_ARM_REG_R4+index,value)
        uc.reg_write(r.UC_ARM_REG_R0,context);uc.reg_write(r.UC_ARM_REG_R1,descriptor)
        uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,0x5001f001)
        uc.emu_start(0xA039D167,0x5001f000,count=10000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('original descriptor adapter budget exceeded')
        checks.append((uc.reg_read(r.UC_ARM_REG_SP)==0x50018000,[uc.reg_read(r.UC_ARM_REG_R4+index) for index in range(8)]==saved))
        return uc.reg_read(r.UC_ARM_REG_R0),bytes(uc.mem_read(descriptor,84))
    same=True
    for language in range(21):
        for identity in (0,1,105,670,847,848,0x70000,0x70067,0x7006a):same=run(identity,language,False)==run(identity,language,True) and same
    _,reference=run(670,4,False);metrics=True;captions=[]
    for identity in (0x70068,0x70069):
        _,value=run(identity,4,True);metrics=value[4:48]==reference[4:48] and value[52:]==reference[52:] and metrics
        pointer=struct.unpack_from('>I',value,48)[0];wire=bytearray()
        for index in range(16):
            pair=bytes(uc.mem_read(pointer+index*2,2))
            if pair==bytes(2):break
            wire.extend(pair)
        captions.append(wire.decode('utf-16-be'))
    return dict(all_stock_descriptors_preserved=same,private_metrics_match_stock=metrics,private_captions=captions,
                stack_preserved=all(v[0] for v in checks),callee_saved_preserved=all(v[1] for v in checks),helpers_intercepted=[],hardware_tested=False,
                scope='Original metadata resolver entered through installed RAM adapter: all21 locales, complete84-byte descriptors/return for stock IDs, private captions retain stock setup-title geometry and font metadata. Synthetic context/property bank; no hardware display claim.')

def probe_menu_entries(code:bytes,*,native_runtime:dict)->dict:
    """Execute original category refresh before/after owned action-row append."""
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']));symbols=native_runtime['symbols']
    word=lambda address:struct.unpack('>I',uc.mem_read(address,4))[0]
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x50002000,0x50003000,0x383))
    uc.mem_write(0x50003000,struct.pack('>5I',0,0,0x383,0x5000D000,0))
    uc.mem_write(word(0xA0398DC4),struct.pack('>I',0x50008000));uc.mem_write(0x50008000,struct.pack('>2I',0,0x17))
    category=0xA0439718+3*24;original_rows=0xA0438B38;stack_ok=[];refresh=[]
    def observe(machine,address,size,context):refresh.append((word(category+12),word(category+20)))
    uc.hook_add(UC_HOOK_CODE,observe,begin=0xA03C1388,end=0xA03C1388)
    def run(entry,value,thumb=False):
        uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,0x5001f001)
        uc.emu_start(entry|1 if thumb else entry,0x5001f000,count=1000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('menu category refresh execution budget exceeded')
        stack_ok.append(uc.reg_read(r.UC_ARM_REG_SP)==0x50018000);return uc.reg_read(r.UC_ARM_REG_R0)
    run(0xA03C1380,3,True);before=bytes(uc.mem_read(original_rows,47*32))
    if run(symbols['gr2_menu_entries_enable'],1)!=1:raise RuntimeError('native menu extension preimage rejected')
    uc.mem_write(0xA03C1380,bytes.fromhex(native_runtime['menu_categories_hook_patch_hex']));uc.ctl_remove_cache(0xA03C1380,0xA03C1388)
    run(0xA03C1380,3,True);owned=word(category+20);count=word(category+12)
    private=[word(owned+(47+index)*32+12) for index in range(2)]
    original_preserved=bytes(uc.mem_read(owned,47*32))==before and bytes(uc.mem_read(original_rows,47*32))==before
    run(0xA03C1380,3,True);stable=word(category+20)==owned
    uc.mem_write(category+12,struct.pack('>I',48));foreign=bytes(uc.mem_read(category,24))
    rejected=run(symbols['gr2_menu_entries_enable'],0)==0 and bytes(uc.mem_read(category,24))==foreign
    uc.mem_write(category+12,struct.pack('>I',49));disabled=run(symbols['gr2_menu_entries_enable'],0)
    restored=disabled==1 and word(category+12)==47 and word(category+20)==original_rows
    return dict(item_count=count,private_routes=private,original_rows_preserved=original_preserved,stable_rows=stable,
                original_refresh_bounded=bool(refresh) and all(v==(47,original_rows) for v in refresh),
                restored=restored,foreign_change_rejected=rejected,stack_preserved=all(stack_ok),
                helpers_intercepted=[],hardware_tested=False,
                scope='Compiled owned49-row extension around actual original47-row category refresh, synthetic property bank/active menu root. No extra definition indices, original rows preserved, cached owned pointers stable and disable restores source metadata. Drawing/navigation/joint page launch still require integration proof.')

def probe_menu_text_adapter(code:bytes,*,native_runtime:dict)->dict:
    """Native caption adapter delegates all stock IDs to the live accessor."""
    from unicorn import arm_const as r
    uc=runtime_machine(code);uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
    word=lambda address:struct.unpack('>I',uc.mem_read(address,4))[0]
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x50002000,0x50003000,0x383))
    uc.mem_write(0x50003000,struct.pack('>5I',0,0,0x383,0x5000D000,0))
    preserved=[]
    def run(identity,language,patched=True):
        uc.mem_write(0x5000D000+0x1e4*4,struct.pack('>I',language))
        saved=[0x77880000+index for index in range(8)]
        for index,value in enumerate(saved):uc.reg_write(r.UC_ARM_REG_R4+index,value)
        uc.reg_write(r.UC_ARM_REG_R0,identity);uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,0x5001f001)
        try:uc.emu_start(native_runtime['symbols']['gr2_menu_text'] if patched else 0xA03A4AEF,0x5001f000,count=10000)
        except Exception as error:raise RuntimeError(f'text hook id={identity:x} lang={language} patched={patched} pc={uc.reg_read(r.UC_ARM_REG_PC):x} sp={uc.reg_read(r.UC_ARM_REG_SP):x}: {error}') from error
        if uc.reg_read(r.UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('current locale private-ID hook budget exceeded')
        preserved.append((uc.reg_read(r.UC_ARM_REG_SP)==0x50018000,[uc.reg_read(r.UC_ARM_REG_R4+index) for index in range(8)]==saved))
        return uc.reg_read(r.UC_ARM_REG_R0)
    same=True
    for language in range(21):
        for identity in (0,1,105,847,848,0x70000,0x70067,0x7006a):
            same=run(identity,language,False)==run(identity,language) and same
    captions=[]
    for identity in (0x70068,0x70069):
        pointer=run(identity,4);wire=bytearray()
        for index in range(96):
            pair=bytes(uc.mem_read(pointer+index*2,2))
            if pair==bytes(2):break
            wire.extend(pair)
        else:raise RuntimeError('private caption is not bounded')
        captions.append(wire.decode('utf-16-be'))
    dynamic=word(0xA03A4C24);live=True
    for pointer in (0x50006000,0x50006010):
        uc.mem_write(dynamic+103*4,struct.pack('>I',pointer));live=run(0x70067,4)==pointer and live
    return dict(private_captions=captions,all_locales_preserved=same,dynamic_updates_live=live,
                stack_preserved=all(v[0] for v in preserved),callee_saved_preserved=all(v[1] for v in preserved),
                helpers_intercepted=[],hardware_tested=False,
                scope='Native two-caption adapter delegates stock IDs to the unmodified current-language accessor/property getter; all21 locales and live dynamic updates. No accessor hook or startup installation.')

def probe_menu_route_hook(code:bytes,*,native_runtime:dict)->dict:
    """Execute installed route veneer; page open and queue/timer are boundaries."""
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
    symbols=native_runtime['symbols'];site=0xA03948C4;original=bytes(uc.mem_read(site,8));root=0x50008000
    word=lambda address:struct.unpack('>I',uc.mem_read(address,4))[0]
    uc.mem_write(word(0xA0398DC4),struct.pack('>I',root))
    provider=0x50009000;converter=0x5001D000
    uc.mem_write(word(0xA0394B28),struct.pack('>I',provider))
    uc.mem_write(provider+0x1c,struct.pack('>I',converter));calls=[];opened=[];preserved=[]
    def boundary(machine,address,size,context):
        a=machine.reg_read(r.UC_ARM_REG_R0);result=0
        if address==symbols['gr2_settings_open']:
            if a:raise ValueError('menu route must bind native backend')
            opened.append(machine.reg_read(r.UC_ARM_REG_R1)) # Fail open deliberately.
        elif address==0xA0027D96:result=0x11223344;calls.append(['tick'])
        elif address==converter:result=0x60002001;calls.append(['convert',a])
        else:
            pointer=machine.reg_read(r.UC_ARM_REG_R1);calls.append(['queue',*struct.unpack('>3I',machine.mem_read(pointer,12))])
        machine.reg_write(r.UC_ARM_REG_R0,result);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    for address in (symbols['gr2_settings_open'],0xA0027D96,converter,0xA00547C2):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    def run(route,patched,kind=0x17):
        uc.mem_write(root,struct.pack('>2I',0,kind));uc.mem_write(site,bytes.fromhex(native_runtime['menu_route_hook_patch_hex']) if patched else original)
        uc.ctl_remove_cache(site,site+8);calls.clear();opened.clear()
        saved=[0x44550000+index for index in range(8)]
        for register,value in zip((r.UC_ARM_REG_R4,r.UC_ARM_REG_R5,r.UC_ARM_REG_R6,r.UC_ARM_REG_R7,r.UC_ARM_REG_R8,r.UC_ARM_REG_R9,r.UC_ARM_REG_R10,r.UC_ARM_REG_R11),saved):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_R0,route);uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,0x5001f001)
        uc.emu_start(0xA03948C1,0x5001f000,count=10000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('original menu route hook budget exceeded')
        preserved.append((uc.reg_read(r.UC_ARM_REG_SP)==0x50018000,[uc.reg_read(r.UC_ARM_REG_R4+index) for index in range(8)]==saved))
        return list(calls),list(opened)
    baseline=run(0x60004067,False);ordinary=run(0x60004067,True)
    films=run(0x6D100001,True);stamp=run(0x6D100003,True)
    wrong_original=run(0x6D100001,False,0x1a);wrong_hook=run(0x6D100001,True,0x1a)
    return dict(opened_screens=films[1]+stamp[1],private_stock_deliveries=len(films[0])+len(stamp[0]),
                ordinary_route_preserved=baseline==ordinary,wrong_root_preserved=wrong_original==wrong_hook,
                stack_preserved=all(v[0] for v in preserved),callee_saved_preserved=all(v[1] for v in preserved),
                helpers_intercepted=['page open failure','tick getter','public-route converter','queue send'],hardware_tested=False,
                scope='Original route function entered through RAM-installed native veneer; private routes consume even when page allocation/open fails. Ordinary and wrong-root callback/queue traces match stock. Actual private page lifetime/render tested separately; no startup installation claim.')

def probe_main_menu_root(code:bytes,*,activate:bool=False)->dict:
    """Identify the actual menu from stock shooting OK action and run CREATE.

    The action predicate and FSM transition are not substituted evidence for a
    live key press. The push operation is observed at its explicit boundary.
    """
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);root=0x50004000;event=0x50001000;stop=0x5001f000;stack=0x50018000;requests=[]
    word=lambda address:struct.unpack('>I',uc.mem_read(address,4))[0]
    def push(machine,address,size,context):
        requests.append([machine.reg_read(r.UC_ARM_REG_R0),machine.reg_read(r.UC_ARM_REG_R1)])
        machine.reg_write(r.UC_ARM_REG_R0,0);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    def run(entry,*args):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2),args):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_SP,stack);uc.reg_write(r.UC_ARM_REG_LR,stop|1)
        uc.emu_start(entry|1,stop,count=1000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=stack:raise RuntimeError('original menu action/create budget or stack failure')
    uc.hook_add(UC_HOOK_CODE,push,begin=0xA003B8BA,end=0xA003B8BA)
    run(0xA039242E)
    if len(requests)!=1 or requests[0][1]!=0x60028:raise ValueError('stock shooting OK action target changed')
    state=word(0xA040177C+(requests[0][1]&0xffff)*4);configuration=word(state+24);handler=word(configuration)
    uc.mem_write(root-16,b'\xa5'*16);uc.mem_write(root,bytes(uc.mem_read(configuration,64)));uc.mem_write(root+0x600,b'\xa5'*16)
    uc.mem_write(event,struct.pack('>3I',0x60000000,0,0));run(handler,root,event)
    menu={}
    if activate:
        # Initialized no-observer property bank and active root are required by
        # the stock category predicates; do not stub them to force eligibility.
        uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x50002000,0x50003000,0x383))
        uc.mem_write(0x50003000,struct.pack('>5I',0,0,0x383,0x5000D000,0))
        uc.mem_write(word(0xA0398DC4),struct.pack('>I',root))
        uc.mem_write(event,struct.pack('>3I',0x60000001,0,0));run(handler,root,event)
        descriptor=word(root+0x3ac);categories=struct.unpack('>H',uc.mem_read(descriptor,2))[0];rows=word(descriptor+8)
        if categories!=5:raise ValueError('stock menu category count changed')
        menu=dict(category_count=categories,category_item_counts=[word(rows+index*24+12) for index in range(categories)],
                  category_titles=[word(rows+index*24+4) for index in range(categories)])
        routes=[]
        def route(machine,address,size,context):
            routes.append(machine.reg_read(r.UC_ARM_REG_R0));machine.reg_write(r.UC_ARM_REG_R0,0)
            machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,route,begin=0xA03948C0,end=0xA03948C0)
        # Detached private row in synthetic RAM. No original category storage
        # is overwritten; this proves only the original type1 confirm route.
        original_rows=word(root+0x170);private_rows=0x50008000
        for target in (0x6D100001,0x6D100003):
            uc.mem_write(private_rows,bytes(uc.mem_read(original_rows,32)))
            uc.mem_write(private_rows+8,struct.pack('>2I',0x01000000,target))
            uc.mem_write(root+0x170,struct.pack('>I',private_rows));uc.mem_write(root+0xB8,bytes(2));uc.mem_write(root+0x3B0,b'\x01')
            uc.mem_write(event,struct.pack('>3I',0x60002001,0,0));run(word(root+0x10),root,event)
        menu['private_confirmation_targets']=routes
        menu['confirmation_boundary']='0xa03948c0'
        uc.mem_write(root+0x170,struct.pack('>I',original_rows))

    count=struct.unpack('>H',uc.mem_read(root+24,2))[0];children=word(root+20)
    if count>32 or not root<=children<root+0x600-count*4:raise ValueError('menu child array exceeds private observation bounds')
    return dict(**menu,requested_state=requests[0][1],public_state=word(state+32),configuration=hex(configuration),handler=hex(handler),
                child_count=count,child_offsets=[word(children+index*4)-root for index in range(count)],
                guards_unchanged=bytes(uc.mem_read(root-16,16))==b'\xa5'*16 and bytes(uc.mem_read(root+0x600,16))==b'\xa5'*16,
                stack_preserved=uc.reg_read(r.UC_ARM_REG_SP)==stack,helpers_intercepted=['FSM push observation']+(['menu route conversion observation'] if activate else []),hardware_tested=False,
                scope='Stock shooting OK action and menu CREATE; optional INIT/category predicates plus type1 confirm on detached private rows. Synthetic active-root/property state; FSM push and route conversion are observation boundaries. Real eligibility, rendering and launcher installation remain under research.')

def probe_ui_undo(code:bytes,*,commit:bool)->dict:
    """Execute stock UI preview capture/end and real system-pool allocation.

    Synthetic valid property bank has no subscribers/mutex and no aliases.
    No preview UI pixels, property observers or concurrent tasks are simulated.
    """
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stop=0x5001f000;table=0x50007000;context=0x50009000;data=0x5000D000
    uc.mem_map(0x51000000,0x10000)
    uc.mem_write(0x51000000,(bytes(20)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0x51006000,(bytes(4)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x51000000,0x50003000,0x383))
    uc.mem_write(0x50003000,struct.pack('>6I',0,0x51006000,0x383,data,0,0))
    uc.mem_write(data+43*4,struct.pack('>I',5))
    uc.mem_write(0xA00B5BFE,struct.pack('>H',1));uc.mem_write(0xA00B5BE0,struct.pack('>I',table));uc.mem_write(table,struct.pack('>h',-2))
    def word(pointer):return struct.unpack('>I',uc.mem_read(pointer,4))[0]
    def run(entry,*args):
        for register,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2),args):uc.reg_write(register,value)
        uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop|1)
        uc.emu_start(entry,stop,count=100000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('UI undo execution budget exceeded')
        return uc.reg_read(UC_ARM_REG_R0)
    def free_bytes():return word(word(table+4)+12)*word(table+20)
    run(0xA0024BCB);before=free_bytes();run(0xA03A0107,context);run(0xA03A013F,context)
    preview=[];saved=[]
    for effect in (6,7):
        run(0xA039FFA9,43,effect);preview.append(word(data+43*4));saved.append(word(word(context)+43*4))
    run(0xA03A0303 if commit else 0xA03A01FB,context)
    final=word(data+43*4);active=word(context+8);depth=word(word(0xA03A03B0)+8)
    run(0xA03A0121,context)
    return dict(commit=commit,preview_values=preview,saved_original_values=saved,final_effect=final,
                active_after=active,stack_depth_after=depth,pool_bytes_before=before,pool_bytes_after=free_bytes(),
                helpers_intercepted=[],hardware_tested=False,
                scope='Original pool creation, UI undo allocation/begin, property preview setter, restore-or-commit and free. Synthetic one-pool/property bank; no page ownership, GUI rendering, property listeners or hardware effect preview claim.')

def probe_effect_view_init(code:bytes,*,native_runtime:dict|None=None,activate:bool=False,settle_animation:bool=False,navigate:bool=False)->dict:
    """Execute stock page creation/INIT, optionally graphics and animation.

    Only palette device upload/apply is substituted in the graphics variant.
    """
    if settle_animation and not activate:raise ValueError('animation settling requires INIT')
    if navigate and not settle_animation:raise ValueError('navigation requires initialized graphics and settled animation')
    from unicorn import UC_HOOK_MEM_WRITE,UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);root=0x50004000;event=0x50001000;stop=0x5001f000;highest=0;external=set();display_writes=0;navigation=[];graphics_contexts=0
    uc.mem_write(root-16,b'\xa5'*16);uc.mem_write(root+0x600,b'\xa5'*16)
    entry=0xA03AD0C7;argument=event
    if native_runtime is None:uc.mem_write(root,bytes(uc.mem_read(0xA0411A18,64)))
    else:
        uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']));entry=native_runtime['symbols']['gr2_effect_view_init'];argument=0x600
    uc.mem_write(event,struct.pack('>3I',0x60000000,0,0))
    def write(machine,access,address,size,value,ctx):
        nonlocal highest,display_writes
        if navigate and 0x68000000<=address<0x68300000:
            display_writes+=1;return
        if root<=address<root+0x600:highest=max(highest,address+size-root)
        elif not 0x50010000<=address<0x50018000:external.add(address)
    if activate:
        # Synthetic initialized property bank with no mutex and an already
        # awake deferred UI worker. No queue callback or widget is intercepted.
        uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x50002000,0x50003000,0x383))
        uc.mem_write(0x50003000,struct.pack('>5I',0,0,0x383,0x5000D000,0))
        uc.mem_write(0x5000D000+43*4,struct.pack('>I',5));uc.mem_write(0x5000D000+0x1e4*4,struct.pack('>I',1))
        control=struct.unpack('>I',uc.mem_read(0xA039CF20,4))[0]
        uc.mem_write(control+0x1c,struct.pack('>I',0x5000C000));uc.mem_write(0x5000C000,struct.pack('>I',32))
        uc.mem_write(control+0x10,struct.pack('>I',1))
    palette_calls=[];context_address=0xA043E844
    uc.hook_add(UC_HOOK_MEM_WRITE,write)
    for register,value in ((UC_ARM_REG_R0,root),(UC_ARM_REG_R1,argument),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
        uc.reg_write(register,value)
    uc.emu_start(entry,stop,count=100000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('effect view initializer execution budget exceeded')
    if activate:
        uc.mem_write(event,struct.pack('>3I',0x60000001,0,0))
        for register,value in ((UC_ARM_REG_R0,root),(UC_ARM_REG_R1,event),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
            uc.reg_write(register,value)
        uc.emu_start(0xA03AD0C7,stop,count=100000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('effect view INIT execution budget exceeded')
    returned=uc.reg_read(UC_ARM_REG_R0)
    if settle_animation:
        buffer_table=struct.unpack('>I',uc.mem_read(0xA03938A4,4))[0]
        palette_control=struct.unpack('>I',uc.mem_read(0xA0393D48,4))[0]
        for index,address in ((4,0x68000000),(5,0x68100000),*(((6,0x68200000),) if navigate else ())):
            uc.mem_map(address,0xb0000 if navigate else 0x55000);handle=0x5000B000+index*0x20
            uc.mem_write(handle,b'BUFF'+struct.pack('>5I',address,720*480*(2 if index==6 else 1),0,0,720*480*(2 if index==6 else 1)))
            uc.mem_write(buffer_table+index*4,struct.pack('>I',handle))
        uc.mem_write(palette_control+0x24,struct.pack('>I',1))
        def palette(machine,address,size,ctx):
            palette_calls.append(address);machine.reg_write(UC_ARM_REG_R0,0)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
        for address in (0xA00F5ED6,0xA00F5F92,*((0xA00F5FE2,) if navigate else ())):uc.hook_add(UC_HOOK_CODE,palette,begin=address,end=address)
        for register,value in ((UC_ARM_REG_R0,context_address),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
            uc.reg_write(register,value)
        uc.emu_start(0xA03BC94D,stop,count=100000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('original graphics context initialization budget exceeded')
        graphics_contexts=1
        if navigate:
            # Synthetic active display geometry comes from the same 720x480
            # fixture as the actual BUFFs; all six constructor bodies are stock.
            display_control=struct.unpack('>I',uc.mem_read(0xA039387C,4))[0]
            uc.mem_write(display_control+0x20,struct.pack('>I',(480<<16)|720))
            for index in (0,1,3,4,5):
                for register,value in ((UC_ARM_REG_R0,index),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):uc.reg_write(register,value)
                uc.emu_start(0xA039DA57,stop,count=100000)
                if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('graphics context lookup budget exceeded')
                pointer=uc.reg_read(UC_ARM_REG_R0);constructor=struct.unpack('>I',uc.mem_read(pointer+0x20,4))[0]
                for register,value in ((UC_ARM_REG_R0,pointer),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):uc.reg_write(register,value)
                uc.emu_start(constructor,stop,count=100000)
                if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('graphics context constructor budget exceeded')
                graphics_contexts+=1

    if settle_animation:
        clock=struct.unpack('>I',uc.mem_read(0xA00695FC,4))[0]
        uc.mem_write(clock,struct.pack('>2I',0,1000))
        uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop|1)
        uc.emu_start(0xA039C56B,stop,count=100000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('original UI animation execution budget exceeded')
    if navigate:
        # Initialized no-alias/no-subscriber property registry, not setter stubs.
        uc.mem_map(0x51000000,0x10000)
        uc.mem_write(0x51000000,(bytes(20)+bytes.fromhex('ffffffff'))*0x383)
        uc.mem_write(0x51006000,(bytes(4)+bytes.fromhex('ffffffff'))*0x383)
        uc.mem_write(0xA0129C3C,struct.pack('>I',0x51000000));uc.mem_write(0x50003004,struct.pack('>I',0x51006000))
        active_root=struct.unpack('>I',uc.mem_read(0xA0398DC4,4))[0];uc.mem_write(active_root,struct.pack('>I',root))
        for action in (0x60002004,0x60002004,0x60002003):
            uc.mem_write(event,struct.pack('>3I',action,1,0))
            for register,value in ((UC_ARM_REG_R0,root+0x84),(UC_ARM_REG_R1,event),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):uc.reg_write(register,value)
            uc.emu_start(0xA03BA7A7,stop,count=30000000)
            if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('effect widget navigation budget exceeded')
            navigation.append(dict(event=action,index=struct.unpack('>H',uc.mem_read(root+0x84+0x60,2))[0],effect=struct.unpack('>I',uc.mem_read(0x5000D000+43*4,4))[0]))
    word=lambda pointer:struct.unpack('>I',uc.mem_read(pointer,4))[0]
    count=struct.unpack('>H',uc.mem_read(root+0x18,2))[0]
    if count>32:raise ValueError('effect embedded widget count exceeds probe bound')
    return dict(navigation=navigation,graphics_contexts=graphics_contexts,display_writes=display_writes,entry='0xa03ad0c6',returned=returned,widget_offsets=[word(word(root+0x14)+4*i)-root for i in range(count)],
                focus=uc.mem_read(root+0x514,1)[0],event_handler=hex(word(root+0x518)),highest_written_offset=highest,
                list_count=struct.unpack('>H',uc.mem_read(root+0x84+0x56,2))[0],list_cursor=struct.unpack('>H',uc.mem_read(root+0x84+0x64,2))[0],
                animation_state=uc.mem_read(root+0x84+0xfc,1)[0],effect_property=word(0x5000D000+43*4) if activate else None,
                pending_draw_mask=word(control+0x20) if activate else 0,
                physical_size=list(struct.unpack('>2H',uc.mem_read(context_address+4,4))),
                logical_size=list(struct.unpack('>2H',uc.mem_read(context_address+8,4))),palette_backend_calls=len(palette_calls),
                external_writes=[hex(value) for value in sorted(external)],guards_unchanged=bytes(uc.mem_read(root-16,16))==b'\xa5'*16 and bytes(uc.mem_read(root+0x600,16))==b'\xa5'*16,
                stack_preserved=uc.reg_read(UC_ARM_REG_SP)==0x50018000,helpers_intercepted=['palette backend upload/apply'] if settle_animation else [],hardware_tested=False,
                scope='Stock 64-byte effect-page configuration and embedded widget initialization in synthetic zeroed 0x600-byte storage. Optional INIT uses a synthetic property bank and already-awake deferred UI worker. For the isolated animation phase the original graphics context is initialized after detached view setup, using synthetic BUFF display planes and kernel clock; palette device operations are boundaries. Optional widget navigation uses six stock graphics constructors, a synthetic active display geometry, and a no-alias/no-subscriber bank; widget handlers and property setters execute unchanged to return. No screen registration, full font rendering or hardware display proof.')

def probe_osd_colors(code:bytes)->dict:
    """Execute stock indexed/16-bit symbolic color conversion, no helper stubs."""
    from unicorn import arm_const as r
    uc=runtime_machine(code);rows=[];stop=0x5001f000
    for index in range(256):
        results=[]
        for mode in (0,1):
            for register,value in ((r.UC_ARM_REG_R0,mode),(r.UC_ARM_REG_R1,0x20000+index),(r.UC_ARM_REG_SP,0x50018000),(r.UC_ARM_REG_LR,stop|1)):uc.reg_write(register,value)
            uc.emu_start(0xA03A4B35,stop,count=10000)
            if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=0x50018000:raise RuntimeError('original OSD color conversion budget/stack failure')
            results.append(uc.reg_read(r.UC_ARM_REG_R0))
        packed=struct.unpack('>I',uc.mem_read(0xA04EA83C+results[0]*4,4))[0]
        alpha=(uc.mem_read(0xA04EAC42+((packed>>24)&7),1)[0]*241)>>12
        rows.append(dict(symbol=0x20000+index,index=results[0],palette=packed,rgb4444=results[1],alpha=alpha))
    return dict(colors=rows,helpers_intercepted=[],hardware_tested=False,
                scope='Original palette lookup, fixed-point YUV to RGB and channel/alpha nibble packing. CPU format evidence, no display hardware or compositing proof.')

def probe_effect_view_draw(code:bytes,disk:bytes,*,frame_out:Path|None=None,native_runtime:dict|None=None,native_font_missing:bool=False,native_card:bool=False,native_card_allocation_failure:bool=False,attach:bool=False,overlay:bool=False,native_fill:bool=False,native_text_full:bool=False,settings_overlay:bool=False,language:int=1,settings_out_dir:Path|None=None,settings_raw_hook:bool=False,menu_entries_draw:bool=False)->dict:
    """Original stock list/graphics/font bodies, with bounded ROM-file reads.

    All display planes, active geometry and property/kernel state are synthetic.
    The resource read and palette device are explicit boundaries, never glyph
    generation, widget drawing, navigation, allocation or property mutation.
    """
    import hashlib
    if (overlay or settings_overlay) and not attach:raise ValueError('overlay evidence requires the original active root transition')
    if settings_overlay and native_runtime is None:raise ValueError('native settings overlay requires compiled runtime')
    if menu_entries_draw and (native_runtime is None or not attach):raise ValueError('menu entries require native runtime and active root')
    if settings_raw_hook and not settings_overlay:raise ValueError('raw hook evidence requires owned settings page')
    if not isinstance(language,int) or not 0<=language<=20:raise ValueError('official language index out of range')
    official_profile(code,'gr2')
    if hashlib.sha256(disk).hexdigest()!='9e0d291f5b9b74f76a2dd269c4b23fe8f524b5db92b86bf82150d5dc3096abf8':
        raise ValueError('exact GR II official resource component identity required')
    resources={}
    for index in range(121):
        at=0x786000+index*64;name=disk[at:at+32].split(b'\0',1)[0].decode('ascii')
        offset,size=struct.unpack_from('>2I',disk,at+32)
        if name.startswith('A:/font/'):resources[name]=disk[512+offset:512+offset+size]
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);root=0x50004000;event=0x50001000;stop=0x5001f000;stack=0x50018000
    word=lambda pointer:struct.unpack('>I',uc.mem_read(pointer,4))[0]
    def run(entry,*args,thumb=True):
        for register,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3),args):uc.reg_write(register,value)
        uc.reg_write(r.UC_ARM_REG_SP,stack);uc.reg_write(r.UC_ARM_REG_LR,stop|1)
        uc.emu_start(entry|1 if thumb else entry,stop,count=30000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_SP)!=stack:raise RuntimeError('original UI/font operation did not return within budget with its stack intact')
        return uc.reg_read(r.UC_ARM_REG_R0)
    # One no-lock/no-alias/no-subscriber property bank and an awake UI worker.
    uc.mem_map(0x51000000,0x10000)
    uc.mem_write(0x51000000,(bytes(20)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0x51006000,(bytes(4)+bytes.fromhex('ffffffff'))*0x383)
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x51000000,0x50003000,0x383))
    uc.mem_write(0x50003000,struct.pack('>6I',0,0x51006000,0x383,0x5000D000,0,0))
    for property_id,value in ((43,5),(0x1e4,language)):uc.mem_write(0x5000D000+property_id*4,struct.pack('>I',value))
    control=word(0xA039CF20)
    uc.mem_write(control+0x1c,struct.pack('>I',0x5000C000));uc.mem_write(0x5000C000,struct.pack('>I',32));uc.mem_write(control+0x10,struct.pack('>I',1))
    uc.mem_write(0xA00B5BFE,struct.pack('>H',1));uc.mem_write(0xA00B5BE0,struct.pack('>I',0x50007000));uc.mem_write(0x50007000,struct.pack('>h',-2))
    run(0xA0024BCA)
    for index,address in ((4,0x68000000),(5,0x68100000),(6,0x68200000)):
        uc.mem_map(address,0xb0000);handle=0x5000B000+index*32;size=720*480*(2 if index==6 else 1)
        uc.mem_write(handle,b'BUFF'+struct.pack('>5I',address,size,0,0,size));uc.mem_write(word(0xA03938A4)+index*4,struct.pack('>I',handle))
    uc.mem_write(word(0xA0393D48)+0x24,struct.pack('>I',1))
    uc.mem_write(word(0xA039387C)+0x20,struct.pack('>I',(480<<16)|720))
    palette_calls=[];read_names=[];font_engine_calls=0;page_events=[]
    def boundary(machine,address,size,context):
        nonlocal font_engine_calls
        if address==0xA03CE5F8:font_engine_calls+=1;return
        if address==0xA03AD0C6:page_events.append(word(machine.reg_read(r.UC_ARM_REG_R1)));return
        value=0
        if address==0xA002CD2C:
            name=bytes(machine.mem_read(machine.reg_read(r.UC_ARM_REG_R0),100)).split(b'\0',1)[0].decode('ascii')
            pointer=machine.reg_read(r.UC_ARM_REG_R1);limit=machine.reg_read(r.UC_ARM_REG_R2)
            payload=resources.get(name);read_names.append(name)
            if payload is None:value=0xffffffff
            elif len(payload)>limit:raise RuntimeError('original font resource exceeds requested capacity')
            else:machine.mem_write(pointer,payload);value=len(payload)
        else:palette_calls.append(hex(address))
        machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    for address in (0xA002CD2C,0xA00F5ED6,0xA00F5F92,0xA00F5FE2,0xA03CE5F8,0xA03AD0C6):uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    # Boot-time service order matters: initialize all constructors and official
    # font services before the list computes its text measurements in INIT.
    for index in range(6):
        pointer=run(0xA039DA56,index);run(word(pointer+0x20),pointer)
    arena_bytes=word(0xA03938B8)
    if arena_bytes!=2246020:raise RuntimeError('original font work arena size identity mismatch')
    uc.mem_map(0x68300000,(arena_bytes+4095)&~4095);uc.mem_write(word(0xA039387C)+0x2c,struct.pack('>I',0x68300000))
    run(0xA039955A)
    uc.mem_write(root-16,b'\xa5'*16);uc.mem_write(root+0x600,b'\xa5'*16)
    uc.mem_write(root,bytes(uc.mem_read(0xA0411A18,64)))
    page_returns=[]
    if attach:
        # The complete draw loop also reaches original ARM code at low 2004.
        # Map the deferred official record explicitly for this CPU fixture;
        # this does not claim the physical ROM/deferred commit was established.
        from scripts.analyze_unity_runtime import parse_executable_load_map
        low=parse_executable_load_map(code)[15];uc.mem_map(0,0x10000)
        uc.mem_write(low['address'],code[low['source_file_offset']:low['source_file_offset']+low['length']])
        uc.mem_write(word(0xA0398DC4),bytes(4))
        page_returns.append(run(0xA0398CD8,root,0))
    else:
        uc.mem_write(word(0xA0398DC4),struct.pack('>I',root))
        for action in (0x60000000,0x60000001):
            uc.mem_write(event,struct.pack('>3I',action,0,0));page_returns.append(run(0xA03AD0C6,root,event))
    uc.mem_write(word(0xA00695FC),struct.pack('>2I',0,1000));run(0xA039C56A)
    navigation=[];draw_returns=[]
    for action in (0x60000003,0x60002004,0x60002004,0x60002003,0x60000003):
        uc.mem_write(event,struct.pack('>3I',action,1,0))
        value=run(0xA0398F20) if attach and action==0x60000003 else run(0xA03BA7A6,root+0x84,event)
        if action==0x60000003:draw_returns.append(value)
        else:navigation.append(word(0x5000D000+43*4))
    overlay_report={}
    if overlay:
        pointer=0x50005000;overlay_events=[];destructor_calls=0
        uc.mem_write(pointer,struct.pack('>9I',0x5001D001,0,0,0,0x5001D101,0,0,0,0))
        def overlay_callback(machine,address,size,context):
            nonlocal destructor_calls
            if address==0x5001D000:overlay_events.append(word(machine.reg_read(r.UC_ARM_REG_R1)))
            else:destructor_calls+=1
            machine.reg_write(r.UC_ARM_REG_R0,1);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in (0x5001D000,0x5001D100):uc.hook_add(UC_HOOK_CODE,overlay_callback,begin=address,end=address)
        if native_runtime is not None:uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
        def attach_overlay():
            if native_runtime is not None:return run(native_runtime['symbols']['gr2_overlay_attach'],pointer,thumb=False)
            uc.mem_write(stack,bytes(4));run(0xA0399094,pointer,0,0,1);return run(0xA0399182,pointer)
        def detach_overlay():
            if native_runtime is not None:return run(native_runtime['symbols']['gr2_overlay_detach'],pointer,thumb=False)
            if not run(0xA0399182,pointer):return 0
            run(0xA0398A5E,pointer,0);return int(not run(0xA0399182,pointer))
        attached=attach_overlay();duplicate=attach_overlay() if native_runtime is not None else 0
        run(0xA0398F20)
        uc.mem_write(event,struct.pack('>3I',0x60002004,1,0));run(0xA0398E6C,event)
        effects=[word(0x5000D000+43*4)];detached=detach_overlay();second_detach=detach_overlay()
        run(0xA0398E6C,event);effects.append(word(0x5000D000+43*4))
        full_rejected=False
        if native_runtime is not None:
            # Occupied slots are a synthetic capacity fixture; the wrapper
            # must reject before touching them or invoking registration.
            views=word(0xA0398DC4);saved=bytes(uc.mem_read(views+4,20))
            uc.mem_write(views+4,struct.pack('>5I',*[pointer]*5))
            fresh=pointer+0x80;uc.mem_write(fresh,struct.pack('>9I',0x5001D001,0,0,0,0x5001D101,0,0,0,0))
            original=bytes(uc.mem_read(fresh,36));full_rejected=run(native_runtime['symbols']['gr2_overlay_attach'],fresh,thumb=False)==0 and bytes(uc.mem_read(fresh,36))==original
            uc.mem_write(views+4,saved)
        overlay_report=dict(overlay_attach_return=attached,overlay_duplicate_return=duplicate,overlay_detach_return=detached,
            overlay_second_detach_return=second_detach,overlay_events=overlay_events,overlay_destructor_calls=destructor_calls,
            overlay_underlying_effects=effects,overlay_full_rejected=full_rejected)
    settings_report={}
    if settings_overlay:
        import zlib
        uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
        functions=[0x5001D200+4*i for i in range(5)];ops=0x50006100;out=0x50006400
        run(native_runtime['symbols']['m10v_library_init'],0x50006000,thumb=False)
        saved=bytearray(uc.mem_read(0x50006000,104));ids=[33,*range(66,79),*range(34,66)];writes=[]
        uc.mem_write(ops,struct.pack('>6I',0x50006200,*functions))
        def settings_backend(machine,address,size,unused):
            if machine.reg_read(r.UC_ARM_REG_R0)!=0x50006200:raise RuntimeError('private settings backend context mismatch')
            a,b,c=[machine.reg_read(reg) for reg in (r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3)];value=0
            if address==functions[0]:machine.mem_write(a,bytes(saved))
            elif address==functions[1]:value=ids[a] if a<len(ids) else 0
            elif address==functions[2]:
                if a>=len(ids) or ids[a]!=b or c>=5:raise RuntimeError('private settings install identity mismatch')
                struct.pack_into('>H',saved,12+c*8,b);writes.append(['install',c,b])
            elif address==functions[3]:
                color=word(machine.reg_read(r.UC_ARM_REG_SP));saved[52:56]=bytes((a,b,c,color));writes.append(['stamp',a,b,c,color])
            else:struct.pack_into('>I',saved,96,a);writes.append(['name',a])
            struct.pack_into('>I',saved,100,zlib.crc32(saved[:100]))
            machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,settings_backend,begin=functions[0],end=functions[-1])
        def snapshot():
            if run(native_runtime['symbols']['gr2_settings_peek'],out,thumb=False)!=1:raise RuntimeError('private settings page unexpectedly closed')
            return list(struct.unpack('>7I',uc.mem_read(out+104,28)))
        raw_deliveries=[];raw_inflight=False
        preserved=[r.UC_ARM_REG_R4,r.UC_ARM_REG_R5,r.UC_ARM_REG_R6,r.UC_ARM_REG_R7,r.UC_ARM_REG_R8,r.UC_ARM_REG_R9,r.UC_ARM_REG_R10,r.UC_ARM_REG_R11]
        original_ui_hook=bytes(uc.mem_read(0xA0394950,8))
        if settings_raw_hook:
            uc.mem_write(0xA0394950,bytes.fromhex(native_runtime['ui_event_hook_patch_hex']))
            def observe_raw(machine,address,size,unused):
                if raw_inflight:raw_deliveries.append(address)
            for address in (0xA0394B60,0xA0398E6C):uc.hook_add(UC_HOOK_CODE,observe_raw,begin=address,end=address)
        def key(identity):
            nonlocal raw_inflight
            raw={0x60002001:0x60001009,0x60002002:0x60001008,0x60002003:0x60001006,0x60002004:0x60001007,0x60002005:0x6000100a,0x60002006:0x6000100e}.get(identity,identity if 0x60001000<=identity<0x60001100 else None)
            uc.mem_write(event,struct.pack('>3I',raw if settings_raw_hook and raw else identity,1,0))
            if not settings_raw_hook or raw is None:return run(0xA0398E6C,event)
            for index,register in enumerate(preserved):uc.reg_write(register,0x12340000+index)
            raw_inflight=True
            result=run(0xA039494E,0,event);raw_inflight=False
            if result!=1 or any(uc.reg_read(register)!=0x12340000+index for index,register in enumerate(preserved)):
                raise RuntimeError('private raw key did not consume once with original ABI intact')
            return result
        def pool_free():return word(word(0x50007004)+12)*word(0x50007014)
        def save_settings(name):
            if settings_out_dir is None:return
            from PIL import Image
            # CPU reconstruction of two stock planes; not a hardware screenshot.
            palette={row['index']:row['rgb4444'] for row in probe_osd_colors(code)['colors']}
            indexed=bytes(uc.mem_read(0x68000000,720*480));rgb=bytes(uc.mem_read(0x68200000,720*480*2));pixels=bytearray(720*480*3)
            for i,index in enumerate(indexed):
                base=int.from_bytes(rgb[2*i:2*i+2],'big');over=palette.get(index,0);alpha=(over&15)/15
                for channel,shift in enumerate((12,8,4)):
                    pixels[3*i+channel]=round(((over>>shift&15)*alpha+(base>>shift&15)*(1-alpha))*17)
            target=Path(settings_out_dir);target.mkdir(parents=True,exist_ok=True)
            Image.frombytes('RGB',(720,480),bytes(pixels)).save(target/(name+'.png'))
        available=pool_free();before_settings=bytes(uc.mem_read(0x68200000,720*480*2))
        opened=run(native_runtime['symbols']['gr2_settings_open'],ops,1,thumb=False)
        duplicate=run(native_runtime['symbols']['gr2_settings_open'],ops,1,thumb=False)
        initial=snapshot()
        uc.mem_write(event,struct.pack('>3I',0x60001013,1,0))
        if run(native_runtime['symbols']['gr2_settings_raw_event'],event,thumb=False)!=0 or snapshot()!=initial:
            raise RuntimeError('private raw handler consumed an unmapped power event')
        if settings_raw_hook:
            for identity in (0x60001018,0x60001017,0x60001015,0x60001014,0x60001007,0x60001006):key(identity)
            if snapshot()!=initial:raise RuntimeError('GR II dial/directional round trip changed page state')
        run(0xA0398F20);save_settings('films')
        changed=sum(a!=b for a,b in zip(before_settings,bytes(uc.mem_read(0x68200000,720*480*2))))
        key(0x60002001);after_right=snapshot();key(0x60002005);after_catalog=snapshot();run(0xA0398F20);save_settings('catalog');key(0x60002001);key(0x60002006)
        if writes:raise RuntimeError('private catalog cancel performed a write')
        for identity in (0x60002005,0x60002001,0x60002005):key(identity)
        after_install=snapshot();run(0xA0398F20);key(0x60002006)
        closed=[run(native_runtime['symbols']['gr2_settings_close'],thumb=False)]
        if not run(native_runtime['symbols']['gr2_settings_open'],ops,3,thumb=False):raise RuntimeError('private stamp page failed to reopen')
        run(0xA0398F20);save_settings('stamp')
        for identity in (0x60002005,0x60002001,0x60002006):key(identity)
        if len(writes)!=1:raise RuntimeError('private value cancel performed a write')
        for identity in (0x60002005,0x60002001,0x60002005):key(identity)
        run(0xA0398F20);key(0x60002006);closed.append(run(native_runtime['symbols']['gr2_settings_close'],thumb=False))
        raw_scope_restored=run(native_runtime['symbols']['gr2_settings_raw_event'],event,thumb=False)==0
        if settings_raw_hook:
            raw_scope_restored=raw_scope_restored and run(0xA039494E,0,0)==0
            # No private page: execute the full original provider chain twice,
            # with and without the installed RAM veneer. Only the provider's
            # application callback is a boundary, just as in stock firmware.
            provider=0x50006A00;pre_calls=[]
            uc.mem_write(provider,struct.pack('>7I',0,0x5001D301,0,0,0,0,0))
            provider_slot=word(0xA0394B28);prior_provider=bytes(uc.mem_read(provider_slot,4));uc.mem_write(provider_slot,struct.pack('>I',provider))
            def provider_pre(machine,address,size,unused):
                pre_calls.append([machine.reg_read(r.UC_ARM_REG_R0),machine.reg_read(r.UC_ARM_REG_R1)])
                machine.reg_write(r.UC_ARM_REG_R0,1);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
            uc.hook_add(UC_HOOK_CODE,provider_pre,begin=0x5001D300,end=0x5001D300)
            uc.mem_write(event,struct.pack('>3I',0x60001009,1,0));returns=[]
            for patched in (False,True):
                uc.mem_write(0xA0394950,bytes.fromhex(native_runtime['ui_event_hook_patch_hex']) if patched else original_ui_hook)
                uc.ctl_remove_cache(0xA039494E,0xA03949D6)
                try:returns.append(run(0xA039494E,provider,event))
                except Exception as error:raise RuntimeError(f'provider chain failed patched={patched} PC={uc.reg_read(r.UC_ARM_REG_PC):08x} LR={uc.reg_read(r.UC_ARM_REG_LR):08x} SP={uc.reg_read(r.UC_ARM_REG_SP):08x}') from error
            uc.mem_write(provider_slot,prior_provider)
            raw_scope_restored=raw_scope_restored and returns==[1,1] and pre_calls==[[provider,event],[provider,event]]
        settings_report=dict(settings_raw_scope_restored=raw_scope_restored,settings_raw_double_deliveries=len(raw_deliveries),settings_opened=opened,settings_duplicate=duplicate,settings_initial=initial,settings_after_right=after_right,
            settings_after_catalog=after_catalog,settings_after_install=after_install,settings_writes=writes,settings_changed_bytes=changed,
            settings_camera_root_preserved=word(word(0xA0398DC4))==root,settings_pool_restored=pool_free()==available,
            settings_closed=closed,settings_underlying_effect=word(0x5000D000+43*4))
    native_text_return=None;native_text_changed_bytes=0;native_text_outside_bounds=0
    if native_runtime is not None:
        uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
        if native_font_missing:uc.mem_write(0xA077D70C+0x14,bytes(4))
        before=bytes(uc.mem_read(0x68000000,720*480))
        text_box=(600,60,719,120) if native_text_full else (380,60,639,120)
        uc.mem_write(0x50001200,'M10V\0'.encode('utf-16-be'));uc.mem_write(0x50001300,struct.pack('>4h',*text_box))
        native_text_return=run(native_runtime['symbols']['gr2_text_draw_full' if native_text_full else 'gr2_text_draw'],0x50001200,4,0x50001300,0x20001,thumb=False)
        after=bytes(uc.mem_read(0x68000000,720*480));native_text_changed_bytes=sum(a!=b for a,b in zip(before,after))
        native_text_outside_bounds=sum(a!=b for i,(a,b) in enumerate(zip(before,after)) if not (text_box[0]<=i%720<=text_box[2] and text_box[1]<=i//720<=text_box[3]))
    native_fill_report={}
    if native_runtime is not None and native_fill:
        returns=[];match=True;outside=0;samples=[]
        uc.mem_write(0x50001300,struct.pack('>4h',10,20,14,25))
        for index,address,bytes_per_pixel in ((0,0x68000000,1),(1,0x68200000,2)):
            color=run(0xA03A4B34,index,0x20001)
            before_fill=bytes(uc.mem_read(address,720*480*bytes_per_pixel))
            returns.append(run(native_runtime['symbols']['gr2_fill_rect'],index,0x50001300,0x20001,thumb=False))
            after_fill=bytes(uc.mem_read(address,720*480*bytes_per_pixel))
            expected=bytes([color]) if index==0 else struct.pack('>H',color)
            actual=b''.join(after_fill[((20+row)*720+10)*bytes_per_pixel:((20+row)*720+15)*bytes_per_pixel] for row in range(6))
            samples.append(dict(index=index,actual=actual[:60].hex(),expected=expected.hex()))
            match=match and actual==expected*30
            outside+=sum(a!=b for i,(a,b) in enumerate(zip(before_fill,after_fill)) if not (10<=(i//bytes_per_pixel)%720<=14 and 20<=(i//bytes_per_pixel)//720<=25))
        native_fill_report=dict(native_fill_samples=samples,native_fill_returns=returns,native_fill_matches_reference=match,native_fill_outside_bounds=outside)
    native_card_report={}
    if native_runtime is not None and native_card:
        def pool_free():return word(word(0x50007004)+12)*word(0x50007014)
        def save_settings(name):
            if settings_out_dir is None:return
            from PIL import Image
            # CPU reconstruction of two stock planes; not a hardware screenshot.
            palette={row['index']:row['rgb4444'] for row in probe_osd_colors(code)['colors']}
            indexed=bytes(uc.mem_read(0x68000000,720*480));rgb=bytes(uc.mem_read(0x68200000,720*480*2));pixels=bytearray(720*480*3)
            for i,index in enumerate(indexed):
                base=int.from_bytes(rgb[2*i:2*i+2],'big');over=palette.get(index,0);alpha=(over&15)/15
                for channel,shift in enumerate((12,8,4)):
                    pixels[3*i+channel]=round(((over>>shift&15)*alpha+(base>>shift&15)*(1-alpha))*17)
            target=Path(settings_out_dir);target.mkdir(parents=True,exist_ok=True)
            Image.frombytes('RGB',(720,480),bytes(pixels)).save(target/(name+'.png'))
        if native_card_allocation_failure:
            run(native_runtime['symbols']['gr2_allocate'],pool_free(),thumb=False)
        available=pool_free();before_card=bytes(uc.mem_read(0x68200000,720*480*2))
        result=run(native_runtime['symbols']['gr2_card_draw'],33,2,1,(106<<16)|300,thumb=False)
        after_card=bytes(uc.mem_read(0x68200000,720*480*2))
        uc.mem_map(0x68600000,0x20000)
        # Independent decoded reference uses the already host-verified shared
        # RGBA bridge; set the fifth argument before entering its ARM function.
        for register,value in ((r.UC_ARM_REG_R0,0x68600000),(r.UC_ARM_REG_R1,120*196*4),(r.UC_ARM_REG_R2,33),(r.UC_ARM_REG_R3,2),(r.UC_ARM_REG_SP,stack),(r.UC_ARM_REG_LR,stop)):uc.reg_write(register,value)
        uc.mem_write(stack,struct.pack('>I',1));uc.emu_start(native_runtime['symbols']['gr2_film_card_rgba'],stop,count=30000000)
        if uc.reg_read(r.UC_ARM_REG_PC)!=stop or uc.reg_read(r.UC_ARM_REG_R0)!=1:raise RuntimeError('card reference did not return')
        rgba=bytes(uc.mem_read(0x68600000,120*196*4));reference=bytearray()
        for at in range(0,len(rgba),4):
            channels=[(value+8)//17 for value in rgba[at:at+4]]
            reference.extend(struct.pack('>H',(channels[0]<<12)|(channels[1]<<8)|(channels[2]<<4)|channels[3]))
        actual=b''.join(after_card[((106+row)*720+300)*2:((106+row)*720+420)*2] for row in range(196))
        native_card_report=dict(native_card_return=result,native_card_changed_bytes=sum(a!=b for a,b in zip(before_card,after_card)),
            native_card_outside_bounds=sum(a!=b for i,(a,b) in enumerate(zip(before_card,after_card)) if not (300<=(i//2)%720<420 and 106<=(i//2)//720<302)),
            native_card_matches_reference=actual==bytes(len(reference)) if native_card_allocation_failure else actual==reference,
            native_card_pool_restored=pool_free()==available)
    menu_report={}
    if menu_entries_draw:
        menu_text_calls=[];menu_resolved_titles=[]
        def observe_menu_text(machine,address,size,unused):
            identity=machine.reg_read(r.UC_ARM_REG_R0)
            if identity>=0x70000:menu_text_calls.append([hex(address),hex(identity)])
        for address in (0xA03A4AEE,0xA03A4E84):uc.hook_add(UC_HOOK_CODE,observe_menu_text,begin=address,end=address)
        def observe_descriptor(machine,address,size,unused):
            descriptor=machine.reg_read(r.UC_ARM_REG_R1)
            if word(descriptor) in (0x70068,0x70069):
                pointer=word(descriptor+48);wire=bytearray()
                for index in range(16):
                    pair=bytes(machine.mem_read(pointer+2*index,2))
                    if pair==bytes(2):break
                    wire.extend(pair)
                title=wire.decode('utf-16-be')
                if title in ('胶卷库','时间水印'):menu_resolved_titles.append(title)
        uc.hook_add(UC_HOOK_CODE,observe_descriptor,begin=0xA039D5F2,end=0xA039D5F2)

        for address,key in ((0xA03C1380,'menu_categories_hook_patch_hex'),(0xA039D168,'menu_descriptor_hook_patch_hex')):
            uc.mem_write(address,bytes.fromhex(native_runtime[key]));uc.ctl_remove_cache(address,address+8)
        uc.mem_write(0xA039D60E,bytes.fromhex(native_runtime['menu_raster_classifier_patch_hex']));uc.ctl_remove_cache(0xA039D60E,0xA039D610)
        if run(native_runtime['symbols']['gr2_menu_entries_enable'],1,thumb=False)!=1:raise RuntimeError('private menu row enable failed')
        root=0x50008000;uc.mem_write(root-16,b'\xa5'*16);uc.mem_write(root,bytes(uc.mem_read(0xA040D494,64)));uc.mem_write(root+0x600,b'\xa5'*16)
        run(0xA0398CD8,root,0);run(0xA0398F20)
        rows=word(root+0x170)
        selection=[]
        for _ in range(64):
            uc.mem_write(event,struct.pack('>3I',0x60002004,1,0));run(0xA0398E6C,event)
            selection.append(struct.unpack('>H',uc.mem_read(root+0xB8,2))[0])
            if selection[-1]==47:break
        uc.mem_write(word(0xA00695FC),struct.pack('>2I',0,2000));run(0xA039C56A)
        run(0xA0398F20)
        menu_widget=bytes(uc.mem_read(root+0x78,0x100)).hex()
        menu_open=[];menu_events=[]
        def menu_observe(machine,address,size,unused):
            menu_events.append([hex(address),word(machine.reg_read(r.UC_ARM_REG_R1)) if address==0xA03AB8EC else machine.reg_read(r.UC_ARM_REG_R0)])
        for address in (0xA03AB8EC,0xA03948C0):uc.hook_add(UC_HOOK_CODE,menu_observe,begin=address,end=address)
        menu_mode=bytes(uc.mem_read(root+0x3b0,1)).hex()
        def observe_menu_open(machine,address,size,unused):
            menu_open.append([machine.reg_read(r.UC_ARM_REG_R0),machine.reg_read(r.UC_ARM_REG_R1)])
            machine.reg_write(r.UC_ARM_REG_R0,0);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,observe_menu_open,begin=native_runtime['symbols']['gr2_settings_open'],end=native_runtime['symbols']['gr2_settings_open'])
        uc.mem_write(0xA03948C4,bytes.fromhex(native_runtime['menu_route_hook_patch_hex']));uc.ctl_remove_cache(0xA03948C4,0xA03948CC)
        uc.mem_write(event,struct.pack('>3I',0x60002001,1,0));run(0xA0398E6C,event)
        right_open=list(menu_open);menu_open.clear()
        uc.mem_write(event,struct.pack('>3I',0x6000100a,1,0))
        raw_result=run(native_runtime['symbols']['gr2_settings_raw_event'],event,thumb=False)
        if raw_result:
            uc.mem_write(0xA0394950,bytes.fromhex(native_runtime['ui_event_hook_patch_hex']));uc.ctl_remove_cache(0xA0394950,0xA0394958)
            run(0xA039494E,0,event)
            uc.mem_write(event,struct.pack('>3I',0x60002004,1,0));run(0xA0398E6C,event)
            uc.mem_write(event,struct.pack('>3I',0x60001016,1,0));run(0xA039494E,0,event)
        raw_scope=[];raw_before=list(menu_open)
        for offset,replacement in ((0xb8,bytes(2)),(0x3b0,bytes(1)),(0x170,struct.pack('>I',0xA0438B38)),(4,struct.pack('>I',0x1a))):
            prior=bytes(uc.mem_read(root+offset,len(replacement)));uc.mem_write(root+offset,replacement)
            raw_scope.append(run(native_runtime['symbols']['gr2_settings_raw_event'],event,thumb=False))
            uc.mem_write(root+offset,prior)
        raw_scope_preserved=raw_scope==[0]*4 and menu_open==raw_before
        menu_report=dict(menu_raw_scope_preserved=raw_scope_preserved,menu_resolved_titles=menu_resolved_titles,menu_text_calls=menu_text_calls,menu_widget=menu_widget,menu_raw_result=raw_result,menu_raw_open=list(menu_open),menu_events=menu_events,menu_mode=menu_mode,menu_open=right_open,menu_selected_rows=selection,menu_root_active=word(word(0xA0398DC4))==root,menu_rows_owned=rows!=0xA0438B38,
                         menu_private_titles=[word(rows+index*32) for index in (47,48)],menu_font_calls=font_engine_calls)
    frame=bytes(uc.mem_read(0x68000000,720*480))
    if menu_entries_draw:menu_report['menu_caption_ink']=sum(frame[y*720+x]==255 for y in range(360,388) for x in range(100,200))
    if frame_out is not None:
        Path(frame_out).write_bytes(frame)
        if menu_entries_draw:
            from PIL import Image
            palette={row['index']:row['rgb4444'] for row in probe_osd_colors(code)['colors']}
            rgb=bytes(uc.mem_read(0x68200000,720*480*2));pixels=bytearray(720*480*3)
            for index,color in enumerate(frame):
                base=int.from_bytes(rgb[2*index:2*index+2],'big');over=palette.get(color,0);alpha=(over&15)/15
                for channel,shift in enumerate((12,8,4)):
                    pixels[3*index+channel]=round(((over>>shift&15)*alpha+(base>>shift&15)*(1-alpha))*17)
            target=Path(frame_out).with_suffix('.png');Image.frombytes('RGB',(720,480),bytes(pixels)).save(target)
            menu_report['menu_composite_path']=str(target)
    return dict(**menu_report,**settings_report,**native_fill_report,**overlay_report,page_events=page_events,active_root_matches=word(word(0xA0398DC4))==root,low_module_loaded=attach,**native_card_report,native_text_outside_bounds=native_text_outside_bounds,native_text_return=native_text_return,native_text_changed_bytes=native_text_changed_bytes,font_resources=read_names,font_engine_calls=font_engine_calls,font_arena_bytes=arena_bytes,
                page_returns=page_returns,navigation_effects=navigation,draw_returns=draw_returns,
                display_nonzero_bytes=sum(value!=0 for value in frame),display_sha256=hashlib.sha256(frame).hexdigest(),
                palette_backend_calls=palette_calls,guards_unchanged=bytes(uc.mem_read(root-16,16))==b'\xa5'*16 and bytes(uc.mem_read(root+0x600,16))==b'\xa5'*16,
                stack_preserved=uc.reg_read(r.UC_ARM_REG_SP)==stack,helpers_intercepted=['bounded original ROM-resource file read','palette backend upload/apply']+(['private overlay event/destruction callbacks'] if overlay else [])+(['private settings backend callbacks'] if settings_overlay else []),hardware_tested=False,
                scope='Six original graphics constructors and official Latin/monitor fonts initialized before detached stock effect page CREATE/INIT, then original list DRAW and property-mutating navigation. Synthetic display/active geometry, kernel and no-observer property fixtures; optional root transition starts with an empty active root and original draw dispatcher using an explicitly loaded low-address module; no real ROM filesystem, hardware state transition/display or custom M10V page installation.')

def probe_effect_key_routes(code:bytes)->dict:
    """Execute original actions from the MONSETEFFECTMODE state event table.

    Predicate addresses and their accepted focus bytes are executed against a
    synthetic original root. The queue service is an explicit boundary.
    """
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stop=0x5001f000;event=0x50004000;queued=[];routes=[]
    word=lambda pointer:struct.unpack('>I',uc.mem_read(pointer,4))[0]
    state=word(0xA040177C+49*4);events=word(state+0x14)
    root=0x50008000;uc.mem_write(word(0xA0398DC4),struct.pack('>I',root))
    names={}
    for index in range(38):
        identity,pointer=struct.unpack('>2I',uc.mem_read(0xA040A620+index*8,8))
        names[identity]=bytes(uc.mem_read(pointer,80)).split(b'\0',1)[0].decode('ascii')
    def queue(machine,address,size,ctx):
        queued.append([machine.reg_read(register) for register in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)])
        machine.reg_write(UC_ARM_REG_R0,0);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE,queue,begin=0xA03948F6,end=0xA03948F6)
    for index in range(64):
        descriptor=word(events+index*4)
        if not descriptor:break
        data=word(descriptor);action=word(descriptor+8)
        if not data or not action:continue
        source=word(data);predicate=word(data+24)
        uc.mem_write(event,struct.pack('>3I',source,0x12345678,0x23456789));queued.clear()
        for register,value in ((UC_ARM_REG_R0,0x50008000),(UC_ARM_REG_R1,0),(UC_ARM_REG_R2,event),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
            uc.reg_write(register,value)
        uc.emu_start(action,stop,count=1000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop or len(queued)!=1:raise RuntimeError('effect key action failed bounded queue contract')
        target,*payload=queued[0];returned=uc.reg_read(UC_ARM_REG_R0);accepted=[]
        for focus in range(7):
            if not predicate:accepted.append(focus);continue
            uc.mem_write(root+0x514,bytes([focus]));uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop|1)
            uc.emu_start(predicate,stop,count=1000)
            if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('effect focus predicate execution budget exceeded')
            if uc.reg_read(UC_ARM_REG_R0)==1:accepted.append(focus)
        routes.append(dict(source_event=source,source_name=names.get(source,'not in base key table'),action=hex(action),
                           predicate=predicate,accepted_focus=accepted,queued_event=target,payload=payload,returned=returned))
    else:raise ValueError('effect event list exceeds bounded probe count')
    return dict(state_id=word(state+32),state_record=hex(state),routes=routes,helpers_intercepted=['UI event queue'],hardware_tested=False,
                scope='Original effect-screen key actions, names and focus predicates 0..6. Focus transition ownership, actual queue, screen lifecycle and display remain under research.')

def probe_ui_text(code:bytes,text_id:int,language:int,*,native_runtime:dict|None=None)->dict:
    """Execute the original UI localized text lookup without helper substitution."""
    if type(text_id) is not int or not 0<=text_id<=0xffffffff or type(language) is not int or not 0<=language<(0x100000000 if native_runtime is not None else 21):
        raise ValueError('u32 text id and original language index 0..20 required')
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stop=0x5001f000;entry=0xA03A4AD1
    if native_runtime is not None:
        uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']));entry=native_runtime['symbols']['gr2_original_text']
    for register,value in ((UC_ARM_REG_R0,text_id),(UC_ARM_REG_R1,language),(UC_ARM_REG_SP,0x50018000),(UC_ARM_REG_LR,stop|1)):
        uc.reg_write(register,value)
    uc.emu_start(entry,stop,count=1000)
    if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('original text lookup execution budget exceeded')
    pointer=uc.reg_read(UC_ARM_REG_R0);wire=bytearray()
    if not pointer:return dict(pointer=0,text='',wire_hex='',helpers_intercepted=[],hardware_tested=False)
    for index in range(256):
        pair=bytes(uc.mem_read(pointer+index*2,2));wire.extend(pair)
        if pair==bytes(2):break
    else:raise ValueError('original text exceeds bounded probe string length')
    return dict(entry='0xa03a4ad0',text_id=text_id,language=language,pointer=pointer,text=bytes(wire[:-2]).decode('utf-16-be'),
                wire_hex=wire.hex(),helpers_intercepted=[],hardware_tested=False,
                scope='Original loaded locale pointer table and bounded UTF-16BE string; no font rendering or screen display.')

def probe_effect_menu(code:bytes)->dict:
    """Execute the original effect menu's display/property conversion both ways.

    Property-bank reads, property change dispatch and screen refresh are explicit
    boundaries. Definitions, permutation, transform and menu callbacks are stock.
    """
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stop=0x5001f000;current=[0];changes=[];reads=[]
    # Synthetic initialized property registry: stock config and empty callbacks.
    uc.mem_write(0xA0129C38,struct.pack('>4I',0xA0129ADC,0x50002000,0x50001000,0x383))
    def boundary(machine,address,size,ctx):
        r0=machine.reg_read(UC_ARM_REG_R0);r1=machine.reg_read(UC_ARM_REG_R1);result=0
        if address==0xA0037566:
            if r0!=0x50001000 or r1!=43:raise RuntimeError('unexpected effect property bank access')
            reads.append(r1);result=current[0]
        elif address==0xA039FFA8:
            if r0!=43:raise RuntimeError('effect menu changed another property')
            changes.append([r0,r1]);current[0]=r1
        machine.reg_write(UC_ARM_REG_R0,result)
        machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA0037516,0xA0037566,0xA0037540,0xA039FFA8,0xA0398CC8,0xA039FCBE):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    def run(entry,*args):
        for register,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1),args):uc.reg_write(register,value)
        uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop|1)
        uc.emu_start(entry|1,stop,count=10000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('effect menu execution budget exceeded')
        return uc.reg_read(UC_ARM_REG_R0)
    definition=run(0xA0396900,102);property_id=struct.unpack('>I',uc.mem_read(definition+4,4))[0]
    count=struct.unpack('>H',uc.mem_read(definition+12,2))[0]
    rows=[]
    for index in range(count):
        run(0xA03C0AD0,102,index);value=current[0]
        displayed=run(0xA03C0A50,102)
        rows.append(dict(display_index=index,property_value=value,roundtrip=displayed==index))
    return dict(item_id=102,property_id=property_id,definition=hex(definition),choices=rows,
                invalid_definition=run(0xA0396900,0x148),property_reads=len(reads),property_changes=changes,
                helpers_intercepted=['property bank lock/read/unlock','property change dispatch','screen refresh/status'],
                hardware_tested=False,scope='Stock 18-choice effect menu conversion, not a custom menu installation or live camera selection.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--resource-component',type=Path,help='Optional exact official b01firm6 for full stock font/DRAW evidence')
    args=parser.parse_args()
    if args.component.resolve()==args.out.resolve() or (args.resource_component and args.resource_component.resolve()==args.out.resolve()):raise ValueError('output must not overwrite official input')
    code=args.component.read_bytes();profile=official_profile(code,'gr2')
    report=dict(schema='m10v-gr2-native-contract/v1',component_sha256=profile['sha'],
                rtc=probe_rtc_get_time(code,(2026,10,20,18,30,45)),
                memory_policy=[probe_memory_policy(code,boot_mode=mode) for mode in (0,1,3,4)],
                raw_for_dng=[probe_raw_for_dng(code,present=present) for present in (False,True)],
                ui_undo=[probe_ui_undo(code,commit=commit) for commit in (False,True)],
                osd_colors=probe_osd_colors(code),effect_menu=probe_effect_menu(code),effect_key_routes=probe_effect_key_routes(code),effect_view_init=probe_effect_view_init(code),effect_view_activate=probe_effect_view_init(code,activate=True),
                effect_view_animation=probe_effect_view_init(code,activate=True,settle_animation=True),effect_widget_navigation=probe_effect_view_init(code,activate=True,settle_animation=True,navigate=True),task_context=probe_task_context(code),
                ui_text=[probe_ui_text(code,106,language) for language in range(21)],
                sd_file_lifecycle=probe_sd_file_lifecycle(code),
                sd_tell=[probe_sd_tell(code,position) for position in (0,104,0x100000001)],
                sd_seek=[probe_sd_seek(code,offset,origin) for offset,origin in ((0,0),(4096,0),(-1,1),(-4096,2))],
                c_heap=probe_c_heap_startup(code),reserved_c_heap=probe_c_heap_startup(code,reserved_end=0xa0800000),
                isp_color_recipes=[probe_isp_color_recipe(code,tone) for tone in range(21)],memory_regions=probe_memory_regions(code,[1,17,1024]),rtos_pool=probe_rtos_pool(code),image_object_pools=[probe_image_object_pools(code,extra=extra) for extra in (0,128)],
                isp_completion_wait=probe_isp_completion_wait(code),
                main_yuv_handoff=probe_main_yuv_handoff(code),
                capture_owner=[probe_capture_owner(code,kind) for kind in (1,2,3)],
                capture_lifetime=[probe_capture_owner(code,kind,complete=True) for kind in (1,3)],
                jpeg_input=[probe_jpeg_input(code,4928,3264,format_kind=kind) for kind in (2,3,4)],
                sd_io=[probe_sd_io(code,operation,b'M10V\x00config\xff') for operation in ('read','write')],
                sd_modes=[probe_sd_open_mode(code,flags) for flags in (0,1,9,2,10,0x102)],can_build=False)
    if args.resource_component:
        disk=args.resource_component.read_bytes()
        report['producer_iq']=probe_producer_iq(code,disk)
        report['producer_iq_engine']=probe_producer_iq(code,disk,deep=True)
        report['effect_font_draw']=probe_effect_view_draw(code,disk)
        report['effect_root_lifecycle']=probe_effect_view_draw(code,disk,attach=True)
        report['effect_modal_lifecycle']=probe_effect_view_draw(code,disk,attach=True,overlay=True)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(args.out),can_build=False)))

if __name__=='__main__':main()

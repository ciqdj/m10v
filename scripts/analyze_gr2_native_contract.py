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

def probe_sd_file_lifecycle(code:bytes,*,native_runtime:dict|None=None,fail_write:bool=False,fail_close:bool=False)->dict:
    """Execute normal open/read/write/close with synthetic stdio, media and metadata pool boundaries."""
    official_profile(code,'gr2')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    uc=runtime_machine(code);stop=0x5001f000;control=0xA00C2C6C;pool=0x5000c000
    uc.mem_write(control+0x1c,struct.pack('>I',pool))
    if native_runtime is not None:uc.mem_write(native_runtime['base'],bytes.fromhex(native_runtime['runtime_hex']))
    path=0x50001000;source=0x50002000;target=0x50003000
    payload=bytes((i*23+19)&255 for i in range(104));uc.mem_write(path,b'H:/M10V5A.bin\0');uc.mem_write(source,payload)
    file=bytearray();position=0;file_token=0x5000b000;handles=[];closed=[];freed=[];cleared=True
    def string(pointer):return bytes(uc.mem_read(pointer,32)).split(b'\0',1)[0].decode('ascii')
    def boundary(machine,address,size,ctx):
        nonlocal file,position,cleared
        a,b,c,d=[machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if address in (0xA0039F9C,0xA003A01A):raise RuntimeError(f'original filesystem assertion at {address:x}')
        if address==0xA0065324:
            if string(a)!='H:/M10V5A.bin' or string(b) not in ('r','w'):raise ValueError('private file open arguments differ')
            if string(b)=='w':file=bytearray()
            position=0;result=file_token
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
        elif address==0xA00652F0:result=int(position>=len(file))
        elif address==0xA00652E2:
            if a!=file_token:raise ValueError('file close token differs')
            closed.append(a);result=0xffffffff if fail_close else 0
        elif address==0xA00652CE:result=31
        elif address==0xA00267BA:result=1
        else:result=0
        machine.reg_write(UC_ARM_REG_R0,result);machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    for address in (0xA002B0EE,0xA0027360,0xA00273A4,0xA00A2058,0xA0065324,0xA0024C3C,0xA0024D76,
                    0xA0065428,0xA0065386,0xA00652F0,0xA00652E2,0xA00652CE,0xA00267BA,0xA0039DE4,0xA0039F9C,0xA003A01A):
        uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    def run(entry,args):
        for register,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):uc.reg_write(register,value)
        uc.reg_write(UC_ARM_REG_SP,0x50018000);uc.reg_write(UC_ARM_REG_LR,stop|1)
        uc.emu_start(entry,stop,count=100000)
        if uc.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('file lifecycle execution budget exceeded')
        return uc.reg_read(UC_ARM_REG_R0)
    if native_runtime is None:
        handle=run(0xA002C70F,[path,1]);written=run(0xA002CC4B,[handle,source,len(payload)]);run(0xA002C905,[handle])
        handle=run(0xA002C70F,[path,0]);read=run(0xA002CA99,[handle,target,105]);run(0xA002C905,[handle])
    else:
        symbols=native_runtime['symbols'];written=run(symbols['gr2_file_write'],[path,source,len(payload)]);read=run(symbols['gr2_file_read'],[path,target,105])
    return dict(write_returned=written,read_returned=read,payload_matches=bytes(uc.mem_read(target,len(payload)))==payload,
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
    args=parser.parse_args()
    if args.component.resolve()==args.out.resolve():raise ValueError('output must not overwrite official input')
    code=args.component.read_bytes();profile=official_profile(code,'gr2')
    report=dict(schema='m10v-gr2-native-contract/v1',component_sha256=profile['sha'],
                rtc=probe_rtc_get_time(code,(2026,10,20,18,30,45)),
                memory_policy=[probe_memory_policy(code,boot_mode=mode) for mode in (0,1,3,4)],
                raw_for_dng=[probe_raw_for_dng(code,present=present) for present in (False,True)],
                effect_menu=probe_effect_menu(code),effect_key_routes=probe_effect_key_routes(code),task_context=probe_task_context(code),
                ui_text=[probe_ui_text(code,106,language) for language in range(21)],
                sd_file_lifecycle=probe_sd_file_lifecycle(code),
                c_heap=probe_c_heap_startup(code),reserved_c_heap=probe_c_heap_startup(code,reserved_end=0xa0800000),
                memory_regions=probe_memory_regions(code,[1,17,1024]),rtos_pool=probe_rtos_pool(code),
                capture_owner=[probe_capture_owner(code,kind) for kind in (1,2,3)],
                capture_lifetime=[probe_capture_owner(code,kind,complete=True) for kind in (1,3)],
                jpeg_input=[probe_jpeg_input(code,4928,3264,format_kind=kind) for kind in (2,3,4)],
                sd_io=[probe_sd_io(code,operation,b'M10V\x00config\xff') for operation in ('read','write')],
                sd_modes=[probe_sd_open_mode(code,flags) for flags in (0,1,9,2,10,0x102)],can_build=False)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(args.out),can_build=False)))

if __name__=='__main__':main()

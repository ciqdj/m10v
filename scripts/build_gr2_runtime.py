#!/usr/bin/env python3
"""Build/audit the GR II BE32 ABI foundation. Does not package camera firmware."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_unity_update import official_profile
ROOT=Path(__file__).resolve().parents[1]
BASE=0xA0798000
LIMIT=0xA0800000
FLAGS=['--target=armeb-none-eabi','-march=armv4t','-marm','-mfloat-abi=soft','-Os','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-vectorize','-fno-slp-vectorize','-Wall','-Wextra','-Werror']

def audit_elf(data:bytes)->dict:
    if data[:7]!=b'\x7fELF\x01\x02\x01' or struct.unpack_from('>HH',data,16)!=(2,40):raise ValueError('big-endian ARM ELF32 executable required')
    flags=struct.unpack_from('>I',data,36)[0]
    if flags&0x800000:raise ValueError('BE8 instructions cannot execute as original BE32')
    phoff,shoff=struct.unpack_from('>II',data,28)
    phsize,phcount,shsize,shcount,shnames=struct.unpack_from('>5H',data,42)
    if phsize!=32 or shsize!=40 or phoff+phcount*32>len(data) or shoff+shcount*40>len(data):raise ValueError('ELF directory bounds invalid')
    loads=[]
    for i in range(phcount):
        row=struct.unpack_from('>8I',data,phoff+i*32)
        if row[0]!=1:continue
        _,offset,address,physical,filesize,memsize,permissions,alignment=row
        if offset+filesize>len(data) or filesize>memsize or address!=BASE or memsize>LIMIT-BASE:raise ValueError('runtime load range exceeds reserved window')
        loads.append((offset,address,filesize,memsize))
    if len(loads)!=1:raise ValueError('one bounded runtime load segment required')
    offset,address,filesize,memsize=loads[0]
    sections=[struct.unpack_from('>10I',data,shoff+i*40) for i in range(shcount)]
    symbols={};undefined=[]
    for row in sections:
        if row[1]!=2:continue
        if row[9]!=16 or row[6]>=shcount or row[4]+row[5]>len(data):raise ValueError('ELF symbol table invalid')
        st=sections[row[6]];strings=data[st[4]:st[4]+st[5]]
        for at in range(row[4],row[4]+row[5],16):
            name,value,size,info,other,index=struct.unpack_from('>IIIBBH',data,at)
            label=strings[name:].split(b'\0',1)[0].decode('ascii')
            if label and not index:undefined.append(label)
            if label.startswith(('gr2_','m10v_library_','m10v_sd_','m10v_settings_')) and info>>4:
                if not BASE<=value<BASE+memsize:raise ValueError('export outside runtime')
                symbols[label]=value
    if undefined:raise ValueError('unresolved runtime helpers: '+','.join(undefined))
    required={'gr2_post_load','gr2_boot_count','gr2_capture_decode','gr2_date_valid','gr2_startup_chain'}
    if not required<=symbols.keys():raise ValueError('required GR II ABI exports missing')
    return dict(base=address,code_bytes=filesize,memory_bytes=memsize,runtime_hex=data[offset:offset+filesize].hex(),symbols=symbols,undefined_symbols=undefined,endianness='big',be8=False)

def configuration_state(configuration:dict)->tuple[dict,bytes,bytes]:
    """Use the existing page normalizer; convert its LE wire value to BE32 ABI.

    HDF is a separate producer/ISP contract, never a silently ignored field.
    This emits research runtime data, not a downloadable firmware.
    """
    if not isinstance(configuration,dict):raise ValueError('five-slot configuration object required')
    node=shutil.which('node')
    if not node:raise RuntimeError('Node.js required for the shared page configuration contract')
    script="import {readFileSync} from 'node:fs';import {defaultConfiguration,normalizeConfiguration} from './web/gr3/native-library-state.mjs';import {initialState} from './node/gr3-native-library.mjs';const value=JSON.parse(readFileSync(0,'utf8'));const configuration=normalizeConfiguration(Object.keys(value).length?value:defaultConfiguration());console.log(JSON.stringify({configuration,wire:initialState(configuration).toString('hex')}));"
    result=subprocess.run([node,'--input-type=module','-e',script],input=json.dumps(configuration),cwd=ROOT,text=True,capture_output=True,timeout=15)
    if result.returncode:
        message=next((line[6:].strip() for line in result.stderr.splitlines() if line.startswith('Error:')),'shared normalizer rejected the configuration')
        raise ValueError('invalid shared page configuration: '+message)
    decoded=json.loads(result.stdout);normalized=decoded['configuration'];wire=bytes.fromhex(decoded['wire'])
    if normalized['hdf']!=0:raise ValueError('GR II HDF configuration binding remains under reverse engineering')
    if len(wire)!=104 or struct.unpack_from('<IHHI',wire)!=(0x5630314d,4,104,0) or zlib.crc32(wire[:100])!=struct.unpack_from('<I',wire,100)[0]:raise ValueError('shared state wire contract changed')
    native=bytearray(wire);struct.pack_into('>IHHI',native,0,*struct.unpack_from('<IHHI',wire))
    for index in range(5):struct.pack_into('>H',native,12+8*index,struct.unpack_from('<H',wire,12+8*index)[0])
    struct.pack_into('>I',native,96,struct.unpack_from('<I',wire,96)[0]);struct.pack_into('>I',native,100,zlib.crc32(native[:100]))
    return normalized,wire,bytes(native)

def build_gr2_runtime(official:bytes,configuration:dict,out_dir:Path)->dict:
    profile=official_profile(official,'gr2')
    normalized,initial_wire,initial_native=configuration_state(configuration)
    clang=shutil.which('clang');linker=shutil.which('ld.lld')
    if not clang or not linker:raise RuntimeError('clang and ld.lld required for GR II BE32 build')
    from scripts.verify_gr3_5207_reference import verify
    from scripts.verify_gr3_harman_reference import verify as verify_harman
    from scripts.verify_gr3_curated_reference import verify as verify_curated
    from scripts.verify_gr3_newstocks_reference import verify as verify_newstocks
    for check in (verify,verify_harman,verify_curated,verify_newstocks):check(ROOT)
    out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    obj=out_dir/'model.o';elf=out_dir/'model.elf';script=out_dir/'model.ld'
    script.write_text('ENTRY(gr2_post_load)\nPHDRS { image PT_LOAD FLAGS(7); }\nSECTIONS { . = 0xA0798000; .text : { *(.text*) } :image .rodata : { *(.rodata*) } :image .data : { *(.data*) . = ALIGN(4); } :image .bss (NOLOAD) : { *(.bss*) *(COMMON) } :image /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }\n')
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_model.c'),'-o',str(obj)],check=True,capture_output=True)
    startup=out_dir/'startup.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_startup.S'),'-o',str(startup)],check=True,capture_output=True)
    planar=out_dir/'planar.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_planar.c'),'-o',str(planar)],check=True,capture_output=True)
    capture=out_dir/'capture.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_capture.c'),'-o',str(capture)],check=True,capture_output=True)
    storage=out_dir/'storage.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_storage.c'),'-o',str(storage)],check=True,capture_output=True)
    snapshot=out_dir/'snapshot.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_snapshot.c'),'-o',str(snapshot)],check=True,capture_output=True)
    services=out_dir/'services.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_services.c'),'-o',str(services)],check=True,capture_output=True)
    cache=out_dir/'cache.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_cache.S'),'-o',str(cache)],check=True,capture_output=True)
    files=out_dir/'files.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_files.c'),'-o',str(files)],check=True,capture_output=True)
    ui=out_dir/'ui.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_ui.c'),'-o',str(ui)],check=True,capture_output=True)
    sd=out_dir/'sd.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_sd.c'),'-o',str(sd)],check=True,capture_output=True)
    from scripts.gr2_text_contract import effect_name_contract,contract_header
    text_contract=effect_name_contract(official);(out_dir/'m10v_effect_names_contract.h').write_text(contract_header(text_contract))
    effect_names=out_dir/'effect_names.o'
    subprocess.run([clang,*FLAGS,'-I',str(out_dir),'-c',str(ROOT/'native/gr2/m10v_effect_names.c'),'-o',str(effect_names)],check=True,capture_output=True)
    configuration_object=out_dir/'configuration.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_configuration.c'),'-o',str(configuration_object)],check=True,capture_output=True)
    settings_backend=out_dir/'settings_backend.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_settings_backend.c'),'-o',str(settings_backend)],check=True,capture_output=True)
    settings_page=out_dir/'settings_page.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_settings_page.c'),'-o',str(settings_page)],check=True,capture_output=True)
    artwork=out_dir/'artwork.o'
    subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr2/m10v_artwork.c'),'-o',str(artwork)],check=True,capture_output=True)
    render_objects=[str(planar),str(capture),str(storage),str(snapshot),str(services),str(cache),str(files),str(ui),str(sd),str(effect_names),str(configuration_object),str(settings_backend),str(settings_page),str(artwork)]
    for name in ('m10v_library','halation_core','film_5207','film_harman','film_curated','film_newstocks','m10v_sd_library','m10v_settings','m10v_film_card'):
        target=out_dir/(name+'.o')
        initial_flags=['-DM10V_INITIAL_STATE_BYTES='+','.join(map(str,initial_native))] if name=='m10v_library' else []
        subprocess.run([clang,*FLAGS,*initial_flags,'-c',str(ROOT/f'native/gr3/{name}.c'),'-o',str(target)],check=True,capture_output=True)
        render_objects.append(str(target))
    subprocess.run([linker,'-m','armelfb','--no-undefined','-T',str(script),str(obj),str(startup),*render_objects,'-o',str(elf)],check=True,capture_output=True)
    report=audit_elf(elf.read_bytes())
    if official[0xA0044F4C-0xA0020200:0xA0044F50-0xA0020200]!=bytes.fromhex('e12fff1e'):raise ValueError('original SVC callback identity mismatch')
    displacement=report['symbols']['gr2_cache_gateway']-0xA0044F54
    if displacement%4 or not -(1<<25)<=displacement<(1<<25):raise ValueError('cache callback ARM branch range invalid')
    report['cache_gateway_patch_hex']=struct.pack('>I',0xea000000|((displacement>>2)&0xffffff)).hex()
    report['startup_patch_hex']=(bytes.fromhex('4b004718')+struct.pack('>I',report['symbols']['gr2_startup_chain'])).hex()
    from scripts.analyze_unity_runtime import parse_executable_load_map
    for row in parse_executable_load_map(official)[:15]:
        if row['address']<=0xA02ADC98 and 0xA02ADCA0<=row['address']+row['length']:
            source=row['source_file_offset']+0xA02ADC98-row['address'];break
    else:raise ValueError('original JPEG hook outside executable load ranges')
    if official[source:source+8]!=bytes.fromhex('a806f684fc0e980a'):raise ValueError('original JPEG hook instructions differ')
    report['jpeg_hook_patch_hex']=(bytes.fromhex('4b004718')+struct.pack('>I',report['symbols']['gr2_jpeg_chain'])).hex()
    report['jpeg_hook_source_offset']=source
    for row in parse_executable_load_map(official)[:15]:
        if row['address']<=0xA0394950 and 0xA0394958<=row['address']+row['length']:
            source=row['source_file_offset']+0xA0394950-row['address'];break
    else:raise ValueError('original UI hook outside executable load ranges')
    if official[source:source+8]!=bytes.fromhex('0006000d24002900'):raise ValueError('original UI hook instructions differ')
    report['ui_event_hook_patch_hex']=(bytes.fromhex('4b004718')+struct.pack('>I',report['symbols']['gr2_ui_event_chain'])).hex()
    report['ui_event_hook_source_offset']=source
    for row in parse_executable_load_map(official)[:15]:
        if row['address']<=0xA02AD48C and 0xA02AD494<=row['address']+row['length']:
            source=row['source_file_offset']+0xA02AD48C-row['address'];break
    else:raise ValueError('original producer hook outside executable load ranges')
    if official[source:source+8]!=bytes.fromhex('0004000db0ad2198'):raise ValueError('original producer hook instructions differ')
    report['producer_hook_patch_hex']=(bytes.fromhex('4b004718')+struct.pack('>I',report['symbols']['gr2_producer_chain'])).hex()
    report['producer_hook_source_offset']=source



    report.update(schema='m10v-gr2-runtime-foundation/v1',official_sha256=profile['sha'],can_package=False,
                  effect_name_contract=text_contract,configuration=normalized,initial_state_wire_hex=initial_wire.hex(),initial_state_native_hex=initial_native.hex(),
                  configuration_sha256=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                  runtime_sha256=hashlib.sha256(bytes.fromhex(report['runtime_hex'])).hexdigest(),
                  limits=['Shared scalar renderer and ABI bridges; capture ownership/cache/mode lifecycle and menu/storage integration remain researching.','Reserved C-heap window needs original literal adjustment; no firmware patch or download is emitted.','ARMv4T soft-float subset avoids assuming a newer CPU or floating-point unit.'])
    (out_dir/'runtime-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--component',required=True,type=Path);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--configuration',type=Path);args=parser.parse_args()
    report=build_gr2_runtime(args.component.read_bytes(),json.loads(args.configuration.read_text()) if args.configuration else {},args.out)
    print(json.dumps({key:report[key] for key in ('code_bytes','memory_bytes','endianness','be8','can_package')}))
if __name__=='__main__':main()

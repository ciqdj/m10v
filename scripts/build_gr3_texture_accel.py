"""Build an isolated exact full-color texture NEON module; emits no firmware or active hook."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FLAGS=['--target=armv7-none-eabi','-mcpu=cortex-a9','-marm','-mfpu=neon','-mfloat-abi=softfp',
       '-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables',
       '-fno-asynchronous-unwind-tables','-fno-vectorize','-fno-slp-vectorize','-Wall','-Wextra','-Werror']

def build(out_dir,base=0x54150000):
    if type(base) is not int or base&15 or not 0x540b6000<=base<=0x54f00000:raise ValueError('invalid isolated ARM base')
    clang=shutil.which('clang');linker=shutil.which('ld.lld')
    if not clang or not linker:raise RuntimeError('clang and ld.lld are required')
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='m10v-texture-') as folder:
        temp=Path(folder);obj=temp/'texture.o';elf=temp/'texture.elf';script=temp/'link.ld'
        subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr3/m10v_texture_accel.c'),'-o',str(obj)],check=True,capture_output=True)
        script.write_text(f'SECTIONS {{ . = {base}; .text : {{ *(.text*) }} .rodata : {{ *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }} }}')
        subprocess.run([linker,'-T',str(script),'--entry=m10v_texture_block8',str(obj),'-o',str(elf)],check=True,capture_output=True)
        b=elf.read_bytes()
        if b[:7]!=b'\x7fELF\x01\x01\x01' or struct.unpack_from('<HH',b,16)!=(2,40):raise ValueError('invalid ARM executable')
        shoff=struct.unpack_from('<I',b,32)[0];entsize,count,names_index=struct.unpack_from('<HHH',b,46)
        if entsize!=40 or shoff+40*count>len(b):raise ValueError('invalid ELF directory')
        rows=[struct.unpack_from('<10I',b,shoff+40*i) for i in range(count)]
        names_row=rows[names_index];names=b[names_row[4]:names_row[4]+names_row[5]]
        image=bytearray();symbols={}
        for row in rows:
            name=names[row[0]:].split(b'\0',1)[0].decode()
            if row[2]&2 and row[5]:
                if row[1]!=1 or row[2]&1 or name not in ('.text','.rodata') or not base<=row[3]<base+65536 or row[3]+row[5]>base+65536:raise ValueError('unexpected allocated section '+name)
                offset=row[3]-base
                if len(image)<offset+row[5]:image.extend(bytes(offset+row[5]-len(image)))
                image[offset:offset+row[5]]=b[row[4]:row[4]+row[5]]
            if row[1]==2:
                strings_row=rows[row[6]];strings=b[strings_row[4]:strings_row[4]+strings_row[5]]
                for at in range(row[4],row[4]+row[5],16):
                    n,value,size,info,other,section=struct.unpack_from('<IIIBBH',b,at)
                    symbol=strings[n:].split(b'\0',1)[0].decode()
                    if section==0 and symbol:raise ValueError('undefined symbol '+symbol)
                    if symbol.startswith('m10v_texture_') and info&15==2:symbols[symbol]=value
        if set(symbols)!={'m10v_texture_block8','m10v_texture_block8_cached','m10v_texture_effects_block8'}:raise ValueError('texture API mismatch')
        if not image:raise ValueError('empty image')
        (out/'m10v-texture-arm.o').write_bytes(obj.read_bytes())
        (out/'m10v-texture-arm.elf').write_bytes(b)
        (out/'m10v-texture-arm.bin').write_bytes(image)
    report={'schema':'m10v-texture-accel/v1','base':base,'symbols':symbols,'code_bytes':len(image),
       'sha256':hashlib.sha256(image).hexdigest(),'flags':FLAGS,'firmware_emitted':False,'camera_tested':False,
       'exact_full_isp':False,'neon_ownership':'caller establishes original task NEON context',
       'capabilities':{'full_color_texture_block8':True,'lut_entries':3375,'lut_channels':3,
                       'cpu_grain':False,'cpu_leak':False,'exact_rgb24_cache_bytes':65536,'precomputed_noise_required':False,'hardware_isp':False},
       'extra_image_buffers':0,'module_direct_allocation_calls':0,
       'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('native/gr3/m10v_texture_accel.c','native/gr3/m10v_texture_accel.h')}}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--base',type=lambda s:int(s,0),default=0x54150000)
    args=p.parse_args();print(json.dumps(build(args.out,args.base),indent=2))

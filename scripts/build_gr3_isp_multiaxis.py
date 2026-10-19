"""Compile a frame-owned full native multi-axis writer; no hooks or firmware emitted."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FLAGS=['--target=armv7-none-eabi','-mcpu=cortex-a9','-marm','-mfloat-abi=soft',
       '-O2','-ffreestanding','-fno-builtin','-fno-stack-protector',
       '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror']
API={'m10v_isp_multiaxis_apply'}
FIRMWARE_SHA256='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
def build(out_dir,base=0x54160000,rom=None):
    if rom is None:rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
    if hashlib.sha256(rom).hexdigest()!=FIRMWARE_SHA256:raise ValueError('unsupported RTOS hash')
    if type(base) is not int or base&4095 or not 0x540b6000<=base<=0x54f00000:
        raise ValueError('invalid isolated link address (not a camera RAM reservation)')
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    clang,linker=shutil.which('clang'),shutil.which('ld.lld')
    if not clang or not linker:raise RuntimeError('clang and ld.lld required')
    with tempfile.TemporaryDirectory(prefix='m10v-iip-') as folder:
        temp=Path(folder);obj=temp/'iip.o';elf=temp/'iip.elf';script=temp/'link.ld'
        subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr3/m10v_isp_multiaxis.c'),'-o',str(obj)],check=True,capture_output=True)
        script.write_text(f'SECTIONS {{ . = {base}; .text : {{ *(.text*) }} .rodata : {{ *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }} }}')
        subprocess.run([linker,'-T',str(script),'--entry=m10v_isp_multiaxis_apply',str(obj),'-o',str(elf)],check=True,capture_output=True)
        b=elf.read_bytes()
        if b[:7]!=b'\x7fELF\x01\x01\x01' or struct.unpack_from('<HH',b,16)!=(2,40):raise ValueError('invalid ARM ELF')
        shoff=struct.unpack_from('<I',b,32)[0];size,count,nidx=struct.unpack_from('<HHH',b,46)
        if size!=40 or shoff+size*count>len(b):raise ValueError('invalid ELF sections')
        rows=[struct.unpack_from('<10I',b,shoff+40*i) for i in range(count)]
        nr=rows[nidx];names=b[nr[4]:nr[4]+nr[5]];image=bytearray();symbols={}
        for row in rows:
            name=names[row[0]:].split(b'\0',1)[0].decode()
            if row[2]&2 and row[5]:
                if row[1]!=1 or row[2]&1 or name not in ('.text','.rodata') or not base<=row[3]<base+65536 or row[3]+row[5]>base+65536:raise ValueError('unexpected allocated section '+name)
                off=row[3]-base
                if len(image)<off+row[5]:image.extend(bytes(off+row[5]-len(image)))
                image[off:off+row[5]]=b[row[4]:row[4]+row[5]]
            if row[1]==2:
                sr=rows[row[6]];strings=b[sr[4]:sr[4]+sr[5]]
                for at in range(row[4],row[4]+row[5],16):
                    n,value,_,info,_,section=struct.unpack_from('<IIIBBH',b,at)
                    symbol=strings[n:].split(b'\0',1)[0].decode()
                    if section==0 and symbol:raise ValueError('undefined symbol '+symbol)
                    if symbol in API and info&15==2:symbols[symbol]=value
        if set(symbols)!=API or not image:raise ValueError('isolated API mismatch')
        (out/'m10v-isp-multiaxis-arm.o').write_bytes(obj.read_bytes())
        (out/'m10v-isp-multiaxis-arm.elf').write_bytes(b)
        (out/'m10v-isp-multiaxis-arm.bin').write_bytes(image)
    report={'base':base,'symbols':symbols,'bytes':len(image),'patches':[],
            'firmware_activated':False,'quality_equivalence_proven':False,
            'original_firmware_sha256':FIRMWARE_SHA256,
            'scope':'owned original multi-axis banks; no pixel fidelity claim'}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return bytes(image),report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(build(a.out)[1],indent=2))

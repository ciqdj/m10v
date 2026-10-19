"""Build isolated IIP register-image preparation; never emits camera firmware."""
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
API={'m10v_iip_lut_words','m10v_iip_gpc_patch','m10v_iip_spf_bank_patch','m10v_iip_original_copy_owned','m10v_iip_original_stage_owned','m10v_iip_spf_probe_owned'}
FIRMWARE_SHA256='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
def build(out_dir,base=0x54160000):
    if type(base) is not int or base&4095 or not 0x540b6000<=base<=0x54f00000:
        raise ValueError('invalid isolated link address (not a camera RAM reservation)')
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    clang,linker=shutil.which('clang'),shutil.which('ld.lld')
    if not clang or not linker:raise RuntimeError('clang and ld.lld required')
    with tempfile.TemporaryDirectory(prefix='m10v-iip-') as folder:
        temp=Path(folder);obj=temp/'iip.o';elf=temp/'iip.elf';script=temp/'link.ld'
        subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr3/m10v_iip_graph.c'),'-o',str(obj)],check=True,capture_output=True)
        script.write_text(f'SECTIONS {{ . = {base}; .text : {{ *(.text*) }} .rodata : {{ *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }} }}')
        subprocess.run([linker,'-T',str(script),'--entry=m10v_iip_lut_words',str(obj),'-o',str(elf)],check=True,capture_output=True)
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
        (out/'m10v-iip-graph-arm.o').write_bytes(obj.read_bytes())
        (out/'m10v-iip-graph-arm.elf').write_bytes(b)
        (out/'m10v-iip-graph-arm.bin').write_bytes(image)
    report={'schema':'m10v-iip-graph/v1','base':base,'code_bytes':len(image),'symbols':symbols,
            'sha256':hashlib.sha256(image).hexdigest(),'original_firmware_sha256':FIRMWARE_SHA256,
            'firmware_emitted':False,'camera_tested':False,'pixel_math_proven':False,
            'hardware_submit':'original copy/SPF probe adapters; original task ownership required','mmio':False,'module_direct_allocation_calls':0,'spf_probe_workspace_bytes':6144,
            'original_stage_entry':0x53680dbc,'original_stage_execution_r2':0,
            'original_stage_custom_nodes':False,'original_stage_optimizes_cpu_effects':False,
            'release_status_predicates':{'0x53778490':'!(status bit2)','0x53778474':'(status low2)==3'},
            'release_poll_exit_is_dma_idle_proof':False,
            'original_copy_allocates':True,'spf_probe_sd_io':False,'spf_probe_safe_to_install':False,
            'failure_quiescence_proven':False,'unsafe_on_failure':True,'hardware_activation_blocked':True,
            'probe_blocker':'original release has log-and-continue idle-poll timeout paths; no proved abort/reset contract',
            'scope':'original serializers plus caller-owned original copy and isolated SPF probe; no production effects hook',
            'unknown':['GPC binary points and round-code math','SPF tap geometry and edges','scheduler acquisition and buffer ownership'],
            'flags':FLAGS,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['native/gr3/m10v_iip_graph.c','native/gr3/m10v_iip_graph.h']}}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(build(a.out),indent=2))

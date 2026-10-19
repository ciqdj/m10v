"""Instruction-work comparison against the current cached grain lattice.

Runs linked ARM code in Unicorn; records work, not camera milliseconds.
"""
import json
import random
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from scripts.build_gr3_spatial_accel import ROOT,FLAGS
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_BLOCK
from unicorn import arm_const as A

def benchmark(out_dir):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);base=0x54150000
    with tempfile.TemporaryDirectory() as folder:
        temp=Path(folder);wrapper=temp/'compare.c';obj=temp/'compare.o';accel=temp/'accel.o';elf=temp/'compare.elf';link=temp/'link.ld'
        wrapper.write_text('''#include "film_5207.c"
#include "m10v_spatial_accel.h"
void m10v_scalar_noise_span(const uint32_t *xs,uint32_t y,uint32_t seed,uint32_t size,uint32_t *hs,int32_t *ns,uint32_t count){
 grain_lattice c={0xffffffffu,0xffffffffu,0,0,0,0};
 for(uint32_t i=0;i<count;++i){uint32_t h=random32(seed^xs[i]*0x9e3779b9u^y*0x85ebca6bu);hs[i]=h;ns[i]=grain_noise(xs[i],y,seed,size,h,&c)+((int)(h&255)-128)/3;}
}
void m10v_simd_noise_span(const uint32_t *xs,uint32_t y,uint32_t seed,uint32_t size,uint32_t *hs,int32_t *ns,uint32_t count){
 for(uint32_t i=0;i<count;i+=8)m10v_spatial_grain_noise8(xs+i,y,seed,size,hs+i,ns+i);
}
''')
        clang=shutil.which('clang');lld=shutil.which('ld.lld')
        for source,target in ((wrapper,obj),(ROOT/'native/gr3/m10v_spatial_accel.c',accel)):
            subprocess.run([clang,*FLAGS,'-ffunction-sections','-fdata-sections','-I',str(ROOT/'native/gr3'),'-c',str(source),'-o',str(target)],check=True,capture_output=True)
        link.write_text(f'SECTIONS {{ . = {base}; .text : {{ *(.text*) }} .rodata : {{ *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }} }}')
        subprocess.run([lld,'--gc-sections','--undefined=m10v_simd_noise_span','--entry=m10v_scalar_noise_span','-T',str(link),str(obj),str(accel),'-o',str(elf)],check=True,capture_output=True)
        blob=elf.read_bytes();shoff=struct.unpack_from('<I',blob,32)[0];_,count,_=struct.unpack_from('<HHH',blob,46)
        rows=[struct.unpack_from('<10I',blob,shoff+40*i) for i in range(count)];code=bytearray();symbols={}
        for row in rows:
            if row[2]&2 and row[5]:
                assert row[1]==1 and not row[2]&1
                offset=row[3]-base
                if len(code)<offset+row[5]:code.extend(bytes(offset+row[5]-len(code)))
                code[offset:offset+row[5]]=blob[row[4]:row[4]+row[5]]
            if row[1]==2:
                ss=rows[row[6]];strings=blob[ss[4]:ss[4]+ss[5]]
                for at in range(row[4],row[4]+row[5],16):
                    n,value,_,_,_,section=struct.unpack_from('<IIIBBH',blob,at)
                    name=strings[n:].split(b'\0',1)[0].decode()
                    if name in ('m10v_scalar_noise_span','m10v_simd_noise_span'):symbols[name]=value
        results=[]
        for scale in (1,2):
            for size in (0,1,2):
                outputs=[];work=[];n=6000;xs=[i*scale for i in range(n)]
                for symbol in ('m10v_scalar_noise_span','m10v_simd_noise_span'):
                    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(base,(len(code)+4095)&~4095);u.mem_write(base,bytes(code));u.mem_map(0x55000000,0x100000)
                    u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
                    u.mem_write(0x55010000,struct.pack('<'+'I'*n,*xs));sp=0x550fe000;stop=0x550ff000
                    u.mem_write(sp,struct.pack('<III',0x55020000,0x55030000,n))
                    for reg,value in ((A.UC_ARM_REG_R0,0x55010000),(A.UC_ARM_REG_R1,1025),(A.UC_ARM_REG_R2,0xffffffff),(A.UC_ARM_REG_R3,size),(A.UC_ARM_REG_SP,sp),(A.UC_ARM_REG_LR,stop)):u.reg_write(reg,value)
                    cost=[0]
                    u.hook_add(UC_HOOK_BLOCK,lambda uc,pc,length,data:cost.__setitem__(0,cost[0]+length//4))
                    u.emu_start(symbols[symbol],stop,count=10000000)
                    assert u.reg_read(A.UC_ARM_REG_PC)==stop
                    outputs.append(bytes(u.mem_read(0x55020000,n*4))+bytes(u.mem_read(0x55030000,n*4)));work.append(cost[0])
                assert outputs[0]==outputs[1],(scale,size)
                results.append(dict(coordinate_step=scale,size=size,pixels=n,scalar_instructions=work[0],neon_instructions=work[1],ratio=round(work[1]/work[0],4)))
        report={'scope':'linked ARM instruction work, noise primitive only; not fused texture, camera latency, or IIP pixels','rows':results}
        (out/'noise-work.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    print(json.dumps(benchmark(ROOT/'builds/gr3-isp-research/spatial/accel'),indent=2))

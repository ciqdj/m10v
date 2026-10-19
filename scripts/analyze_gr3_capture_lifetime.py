#!/usr/bin/env python3
"""Read-only GR III 2.10 lifetime evidence. Static disassembly is not device proof."""
import argparse, hashlib, json, struct
from pathlib import Path
import numpy as np
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
BASE = 0x53000000
SHA = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
DEFAULT = 'builds/gr3-extension-validation/official-rtos.bin'

def probe_original(b):
    """Execute tiny stock ARM paths; OS calls intercepted, no ISP or camera proof."""
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP
    regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
    ram=0x60000000;stop=ram+0xf0000
    def run(start,args,intercepts):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(BASE,0x1200000);u.mem_write(BASE,b)
        u.mem_map(0x55000000,0x4000000);u.mem_map(ram,0x100000)
        u.reg_write(UC_ARM_REG_SP,ram+0xe0000);u.reg_write(UC_ARM_REG_LR,stop)
        for reg,value in zip(regs,args):u.reg_write(reg,value)
        u.mem_write(ram,struct.pack('<I',0x53d0fc90));u.mem_write(ram+0x252,struct.pack('<H',2))
        u.mem_write(ram+0x60,struct.pack('<I',0x70000100));u.mem_write(ram+0x2f4,struct.pack('<I',0x70000000))
        events=[];finished=[]
        def hook(uc,addr,size,user):
            if addr==stop:finished.append(True);uc.emu_stop()
            elif addr in intercepts:
                argv=[uc.reg_read(r) for r in regs];events.append({'address':hex(addr),'args':list(map(hex,argv)),'stack0':hex(struct.unpack('<I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),4))[0])})
                result=intercepts[addr]
                uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(start,stop+4,count=10000)
        if not finished:raise AssertionError(f'Probe did not return: {start:x}')
        return u,events
    result={'evidence':'original ARM instructions with synthetic RAM and intercepted OS calls; not hardware validation','setter':[],'callback':[],'wait':[]}
    for ptr in [0,0x70000000]:
        u,events=run(0x5350d7e8,[ram,1,ptr],{})
        raw=struct.unpack('<I',u.mem_read(ram+0x60,4))[0];backing=struct.unpack('<I',u.mem_read(ram+0x2f4,4))[0]
        assert raw==(0x70000100 if ptr else 0) and backing==ptr
        result['setter'].append({'input':hex(ptr),'raw_source':hex(raw),'backing':hex(backing),'r0':hex(u.reg_read(regs[0]))})
    # Seed the result byte to expose unsupported-status preservation.
    for status in [0,1,2,3]:
        for opcode in [0x41000,0x42000,0x43000]:
            u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(BASE,0x1200000);u.mem_write(BASE,b);u.mem_map(ram,0x100000)
            u.mem_write(ram+0x10,b'\x7f');u.mem_write(ram+0x104,bytes([status]));u.reg_write(UC_ARM_REG_SP,ram+0xe0000);u.reg_write(UC_ARM_REG_LR,stop)
            for reg,value in zip(regs,[ram,opcode,ram+0x100]):u.reg_write(reg,value)
            signals=[];finished=[]
            def callback_hook(uc,addr,size,user):
                if addr==stop:finished.append(True);uc.emu_stop()
                elif addr==0x536a9d1c:
                    signals.append(uc.reg_read(UC_ARM_REG_R1));uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
            u.hook_add(UC_HOOK_CODE,callback_hook);u.emu_start(0x534ec9b8,stop+4,count=1000)
            assert finished and signals==[{0x41000:1,0x42000:2,0x43000:4}[opcode]]
            success=u.mem_read(ram+0x10,1)[0];assert success==(1 if status==0 else 0 if status in (1,2) else 0x7f)
            result['callback'].append({'opcode':hex(opcode),'status':status,'stored_success':success,'signal':signals[0],'r0':u.reg_read(regs[0])})
    for timeout in [0,25,0xffffffff]:
        for kernel in [0,0xffce0000]:
            u,events=run(0x536a9e8c,[ram,2,0,timeout],{0x536b9f1c:0,0x530512a8:kernel})
            calls=[e for e in events if e['address']=='0x530512a8'];assert len(calls)==1
            assert calls[0]['stack0']==hex(timeout)
            returned=u.reg_read(regs[0]);assert returned==(1 if kernel==0 else 0)
            result['wait'].append({'input_timeout':hex(timeout),'kernel_return':hex(kernel),'bool_return':returned,'kernel_call':calls[0]})
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument('--rtos',default=DEFAULT);p.add_argument('--output',default='builds/gr3-isp-research/lifetime');p.add_argument('--address',action='append',type=lambda x:int(x,0),default=[]);p.add_argument('--count',type=int,default=180);p.add_argument('--probe-original',action='store_true');a=p.parse_args()
    b=Path(a.rtos).read_bytes(); digest=hashlib.sha256(b).hexdigest()
    if digest!=SHA: raise SystemExit('Wrong RTOS SHA256: '+digest)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    words=np.frombuffer(b[:len(b)//4*4],dtype='<u4');idx=np.arange(len(words),dtype=np.int64)
    imm=(words&0xffffff).astype(np.int64);imm=np.where(imm&0x800000,imm-0x1000000,imm)
    targets=BASE+idx*4+8+imm*4;md=Cs(CS_ARCH_ARM,CS_MODE_ARM);md.skipdata=True
    addrs=a.address or [0x5350d7e8,0x535047d4,0x5351ad30,0x5351fc6c,0x536a9e8c,0x53518238,0x535216d0,0x53521d14,0x536a26f0,0x534eb8b4,0x534ecb3c,0x534ec9b8,0x5352013c,0x535218a4,0x5351ea9c,0x53505c8c]
    report={'sha256':digest,'evidence':'static ARM linear disassembly; no hardware execution','functions':{}}
    for addr in addrs:
        lines=[f'{i.address:#010x}: {i.mnemonic} {i.op_str}' for i in md.disasm(b[addr-BASE:addr-BASE+4*a.count],addr)]
        refs=[hex(BASE+4*int(i)) for i in np.flatnonzero(words==addr)]
        calls=[hex(BASE+4*int(i)) for i in np.flatnonzero(((words&0x0f000000)==0x0b000000)&(targets==addr))]
        report['functions'][hex(addr)]={'pointer_refs':refs,'direct_bl_callers':calls}
        (out/f'{addr:08x}.asm').write_text('\n'.join(lines)+'\n')
        print(hex(addr),'pointers',refs,'callers',calls)
    if a.probe_original:
        (out/'original-arm-probes.json').write_text(json.dumps(probe_original(b),indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()

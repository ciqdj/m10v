"""Execute compiled ARM bytes under an explicit software ABI; no camera patches."""
import argparse,hashlib,json,shutil,struct,subprocess,tempfile
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
try:
    from scripts.build_gr3_halation import ROOT,FLAGS,build
except ModuleNotFoundError:
    from build_gr3_halation import ROOT,FLAGS,build
BASE=0x60000000
SEAM=BASE+0x1000
STOP=BASE+0x1ff0
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12]

def build_call_seam():
    with tempfile.TemporaryDirectory() as t:
        obj=Path(t)/'seam.o'
        subprocess.run([shutil.which('clang') or 'clang',*FLAGS,'-c',str(ROOT/'native/gr3/halation_capture.S'),'-o',str(obj)],check=True,capture_output=True)
        elf=obj.read_bytes()
    if elf[:7]!=b'\x7fELF\x01\x01\x01':raise ValueError('invalid seam ELF')
    shoff=struct.unpack_from('<I',elf,32)[0];sz,count,names=struct.unpack_from('<HHH',elf,46)
    rows=[struct.unpack_from('<10I',elf,shoff+i*sz) for i in range(count)]
    st=elf[rows[names][4]:rows[names][4]+rows[names][5]]
    nm=lambda r:st[r[0]:].split(b'\0',1)[0].decode()
    ti=next(i for i,r in enumerate(rows) if nm(r)=='.text');text=rows[ti]
    code=bytearray(elf[text[4]:text[4]+text[5]]);patches=0
    for row in rows:
        if row[1]!=9 or row[7]!=ti:continue
        symbols=rows[row[6]];stringsrow=rows[symbols[6]];strings=elf[stringsrow[4]:stringsrow[4]+stringsrow[5]]
        for pos in range(row[4],row[4]+row[5],8):
            off,info=struct.unpack_from('<II',elf,pos);sym=info>>8;typ=info&255
            ns=struct.unpack_from('<I',elf,symbols[4]+sym*16)[0];name=strings[ns:].split(b'\0',1)[0]
            if typ!=28 or name!=b'm10v_halation' or off+4>len(code) or struct.unpack_from('<I',code,off)[0]!=0xebfffffe:raise ValueError('unexpected research seam relocation')
            delta=BASE-(SEAM+off+8)
            struct.pack_into('<I',code,off,0xeb000000|((delta>>2)&0xffffff));patches+=1
    if patches!=1:raise ValueError('research seam call is absent or ambiguous')
    return bytes(code)

def run_arm(code,seam,y,chroma,width,height,y_stride,chroma_stride,fmt,strength,scratch_bytes):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(BASE,8192);u.mem_write(BASE,code);u.mem_write(SEAM,seam)
    image=0x61000000;ya=0x62000000;ca=0x63000000;sa=0x64000000;stack=0x65000000;sp=stack+0xfff0
    for addr,n in [(image,4096),(ya,len(y)),(ca,len(chroma)),(sa,max(1,scratch_bytes)+64),(stack,65536)]:u.mem_map(addr,(n+4095)&~4095)
    u.mem_write(ya,y);u.mem_write(ca,chroma)
    u.mem_write(image,struct.pack('<9I',ya,ca,len(y)-64,len(chroma)-64,width,height,y_stride,chroma_stride,fmt))
    writes=0;stack_low=sp
    # Accept only visible image pixels, bounded scratch, and this call's stack.
    def write_guard(uc,access,address,size,value,data):
        nonlocal writes,stack_low
        if stack<=address and address+size<=sp:stack_low=min(stack_low,address);return
        if sa<=address and address+size<=sa+scratch_bytes:writes+=1;return
        for start,stride in ((ya,y_stride),(ca,chroma_stride)):
            if start<=address<start+stride*height:
                offset=address-start
                if offset%stride+size<=width and offset//stride<height:writes+=1;return
        raise AssertionError(f'write outside explicit contract: {address:#x}, {size}')
    u.hook_add(UC_HOOK_MEM_WRITE,write_guard)
    initial=[image,strength,sa,scratch_bytes]+[0x12000000+i for i in range(4,13)]
    flags=0xa80f0010
    def setup():
        u.reg_write(UC_ARM_REG_CPSR,flags)
        for reg,value in zip(REGS,initial):u.reg_write(reg,value)
        u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,STOP)
    setup();u.emu_start(BASE,STOP,count=20000000)
    if u.reg_read(UC_ARM_REG_PC)!=STOP:raise AssertionError('ARM instruction budget exceeded')
    status=u.reg_read(UC_ARM_REG_R0);saved=[u.reg_read(r) for r in REGS[4:12]]==initial[4:12]
    result_y=bytes(u.mem_read(ya,len(y)));result_c=bytes(u.mem_read(ca,len(chroma)))
    # Repeat from identical inputs through the preserving seam.
    u.mem_write(ya,y);u.mem_write(ca,chroma);setup();u.emu_start(SEAM,STOP,count=20000000)
    if u.reg_read(UC_ARM_REG_PC)!=STOP:raise AssertionError('ARM seam instruction budget exceeded')
    if result_y!=bytes(u.mem_read(ya,len(y))) or result_c!=bytes(u.mem_read(ca,len(chroma))):raise AssertionError('call seam changes output')
    return {'status':status,'y':result_y,'chroma':result_c,'calleeSaved':saved,
        'seamRegistersPreserved':[u.reg_read(r) for r in REGS]==initial,
        'flagsPreserved':u.reg_read(UC_ARM_REG_CPSR)&0xf80f0000==flags&0xf80f0000,
        'stackRestored':u.reg_read(UC_ARM_REG_SP)==sp,'maxStackBytes':sp-stack_low,'memoryWrites':writes}

def verify(out):
    manifest=build(out);code=(Path(out)/'halation-arm.bin').read_bytes();seam=build_call_seam();rows=[]
    for fmt in (1,2):
        for strength in (1,2):
            w,h=128,96;y=bytearray([24]*(w*h)+[173]*64);y[48*w+64]=255;c=bytes([128]*(w*h)+[197]*64)
            r=run_arm(code,seam,bytes(y),c,w,h,w,w,fmt,strength,6*w*h)
            rows.append({k:v for k,v in r.items() if k not in ('y','chroma')}|{'format':fmt,'strength':strength,'ySha256':hashlib.sha256(r['y']).hexdigest(),'chromaSha256':hashlib.sha256(r['chroma']).hexdigest()})
    if not all(r['status']==0 and all(r[k] for k in ('calleeSaved','seamRegistersPreserved','flagsPreserved','stackRestored')) for r in rows):raise AssertionError('ARM verification failed')
    report={'schema':'m10v-gr3-halation-arm-proof/v1','codeSha256':manifest['codeSha256'],'seamSha256':hashlib.sha256(seam).hexdigest(),'cases':rows,'limits':['Software CBCR/CRCB ABI, not camera chroma evidence','No RTOS allocation, cache hardware, ISP or JPEG encoder emulated','No injected camera adapter or firmware candidate produced']}
    (Path(out)/'halation-arm-proof.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'builds/gr3-800t-kernel');a=p.parse_args();print(json.dumps(verify(a.out),indent=2))

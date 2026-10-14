"""Build a standalone ARM kernel. Does not create or modify firmware."""
import argparse,hashlib,json,shutil,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FLAGS=['--target=armv7-none-eabi','-mcpu=cortex-a9','-marm','-mfloat-abi=soft','-Os','-fomit-frame-pointer','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-vectorize','-fno-slp-vectorize','-Wall','-Wextra','-Werror']
def extract_text(elf, entry='m10v_halation'):
    if elf[:7]!=b'\x7fELF\x01\x01\x01' or struct.unpack_from('<H',elf,18)[0]!=40:raise ValueError('expected little-endian ARM ELF32')
    shoff=struct.unpack_from('<I',elf,32)[0];size,count,names=struct.unpack_from('<HHH',elf,46)
    if size!=40 or shoff+size*count>len(elf) or names>=count:raise ValueError('invalid ELF sections')
    sections=[struct.unpack_from('<10I',elf,shoff+i*size) for i in range(count)]
    names_row=sections[names];strings=elf[names_row[4]:names_row[4]+names_row[5]]
    def name(row):return strings[row[0]:].split(b'\0',1)[0].decode('ascii')
    text_index=next(i for i,row in enumerate(sections) if name(row)=='.text');text=sections[text_index]
    for row in sections:
        if row[1] in (4,9) and row[7]==text_index and row[5]:raise ValueError('ARM text has unresolved relocations')
        if name(row).startswith(('.rodata','.data','.bss')) and row[5]:raise ValueError('standalone kernel has external data')
    symbols=[]
    for row in sections:
        if row[1]!=2:continue
        ns=sections[row[6]];st=elf[ns[4]:ns[4]+ns[5]]
        for off in range(row[4],row[4]+row[5],16):
            n,value,sz,info,other,idx=struct.unpack_from('<IIIBBH',elf,off)
            nm=st[n:].split(b'\0',1)[0].decode('ascii')
            if nm==entry:symbols.append((value,sz,idx))
            if idx==0 and nm:raise ValueError('ARM kernel has undefined symbol: '+nm)
    if len(symbols)!=1 or symbols[0][0]!=0 or symbols[0][2]!=text_index:raise ValueError('standalone entry point differs')
    code=elf[text[4]:text[4]+text[5]]
    if not code or len(code)>4096 or len(code)%4:raise ValueError('ARM kernel exceeds 4096 byte research budget')
    return code

def build(out_dir):
    clang=shutil.which('clang')
    if not clang:raise RuntimeError('clang unavailable')
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='m10v-halation-') as t:
        obj=Path(t)/'core.o'
        subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr3/halation_core.c'),'-o',str(obj)],check=True,capture_output=True)
        code=extract_text(obj.read_bytes())
    sha=lambda b:hashlib.sha256(b).hexdigest()
    manifest={'schema':'m10v-gr3-halation-kernel/v1','entryOffset':0,'codeBytes':len(code),'codeSha256':sha(code),'sources':{p:sha((ROOT/p).read_bytes()) for p in ('native/gr3/halation_core.h','native/gr3/halation_core.c')},'compiler':subprocess.check_output([clang,'--version'],text=True).splitlines()[0],'flags':FLAGS,'abi':'explicit-software-semiplanar-422','cameraLayoutProved':False,'firmwareArtifact':False,'scratchMaxBytes':589824}
    (out/'halation-arm.bin').write_bytes(code);(out/'halation-arm.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'builds/gr3-800t-kernel');args=parser.parse_args();print(json.dumps(build(args.out),indent=2))

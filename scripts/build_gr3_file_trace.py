"""Build checked synchronous file-trace hooks, with 16B caller-frame owner."""
import argparse,hashlib,importlib.util,json,shutil,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('save_trace_builder',ROOT/'scripts/build_gr3_save_trace.py');save=importlib.util.module_from_spec(spec);spec.loader.exec_module(save)
ASM='''
.syntax unified
.arm
.text
.global m10v_file_trace_prewrite
.type m10v_file_trace_prewrite,%function
m10v_file_trace_prewrite:
 push {r0-r12,lr}
 mrs r4,cpsr
 push {r4,r5}
 mov r0,fp
 bl m10v_file_trace_begin
 pop {r4,r5}
 msr cpsr_f,r4
 pop {r0-r12,lr}
 b stock_write_still
.global m10v_file_trace_bridge
.type m10v_file_trace_bridge,%function
m10v_file_trace_bridge:
 push {r4,lr}
 ldr r2,[fp,#-4]
 movw r3,#0x882c
 movt r3,#0x534e
 cmp r2,r3
 bne 1f
 ldr r3,[fp,#-12]
 ldr r2,[r3,#-80]
 ldr r3,[r3,#-56]
 bl m10v_save_trace_bridge
 pop {r4,pc}
1:
 pop {r4,lr}
 b stock_save_bridge
.global m10v_file_trace_postcleanup
.type m10v_file_trace_postcleanup,%function
m10v_file_trace_postcleanup:
 push {r0-r12,lr}
 mrs r4,cpsr
 push {r4,r5}
 mov r0,fp
 mov r1,r5
 bl m10v_file_trace_finish
 pop {r4,r5}
 msr cpsr_f,r4
 pop {r0-r12,lr}
 bx lr
'''
def build(out,base,trace_exports,flush,rtos=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 if base&3 or not 0x540b6000<=base<=0x54ff0000:raise ValueError('invalid code base')
 for address in [flush,trace_exports['m10v_save_trace_init'],trace_exports['m10v_save_trace_bridge']]:
  if address&3 or not 0x53000000<=address<0x55000000:raise ValueError('invalid function address')
 stock=Path(rtos or ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
 if hashlib.sha256(stock).hexdigest()!=save.SHA:raise ValueError('wrong locked RTOS')
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp);asm=temp/'file.S';asm.write_text(ASM);script=temp/'link.ld';script.write_text('SECTIONS { . = '+hex(base)+'; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }')
  objects=[]
  for source in [ROOT/'native/gr3/m10v_file_trace.c',asm]:
   obj=temp/(source.stem+'.o');subprocess.run(['clang',*save.FLAGS,'-c',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
   for name,row in save.sections(obj.read_bytes()):
    if row[2]&3==3 and row[5]:raise ValueError('writable section '+name)
  elfpath=out/'m10v_file_trace.elf';defs={**{name:trace_exports[name] for name in ['m10v_save_trace_init','m10v_save_trace_bridge','m10v_save_trace_append']},'m10v_lifecycle_file_flush':flush,'stock_write_still':0x534eb8b4,'stock_save_bridge':0x534ecb3c}
  subprocess.run([shutil.which('ld.lld') or 'ld.lld','-m','armelf','-T',str(script),*[f'--defsym={k}={v}' for k,v in defs.items()],*map(str,objects),'-o',str(elfpath)],check=True,capture_output=True)
 elf=elfpath.read_bytes();rows=save.sections(elf);exports={};blob=None
 for name,row in rows:
  if row[2]&2 and row[5]:
   if name!='.text' or row[2]&1 or row[3]!=base:raise ValueError('unexpected section')
   blob=elf[row[4]:row[4]+row[5]]
  if row[1]==2:
   strings_row=rows[row[6]][1];strings=elf[strings_row[4]:strings_row[4]+strings_row[5]]
   for at in range(row[4],row[4]+row[5],16):
    ni,value,length,info,other,index=struct.unpack_from('<IIIBBH',elf,at);symbol=strings[ni:].split(b'\0',1)[0].decode()
    if symbol and index==0:raise ValueError('undefined '+symbol)
    if symbol.startswith('m10v_file_trace_') and info&15==2:exports[symbol]=value
 if blob is None:raise ValueError('no text')
 def bl(at,target):
  off=target-at-8
  if off&3 or not -(1<<25)<=off<(1<<25):raise ValueError('BL range')
  return struct.pack('<I',0xeb000000|((off>>2)&0xffffff))
 patches=[]
 def patch(at,expected,replacement,role):
  if stock[at-0x53000000:at-0x53000000+4]!=expected:raise ValueError('stock mismatch '+hex(at))
  patches.append(dict(address=at,expected_hex=expected.hex(),replacement_hex=replacement.hex(),role=role))
 patch(0x534e87a4,bytes.fromhex('24d04de2'),bytes.fromhex('34d04de2'),'outer caller frame grows 16 bytes')
 for at,target,symbol in [(0x534e8828,0x534eb8b4,'m10v_file_trace_prewrite'),(0x534eba44,0x534ecb3c,'m10v_file_trace_bridge'),(0x534e8834,0x534eb7e4,'m10v_file_trace_postcleanup')]:patch(at,bl(at,target),bl(at,exports[symbol]),symbol)
 manifest=dict(schema=1,base=base,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),required_rtos_sha256=save.SHA,exports=exports,patches=patches,mutable_global_bytes=0,camera_tested=False,owner=dict(storage='optional heap allocation referenced only by original outer caller frame',outer=0x534e8794,inner=0x534eb8b4,original_frame_sub=0x24,extended_frame_sub=0x34,pointer_fp_offset=-0x50,outgoing_stack_offsets=[-0x5c,-0x58,-0x54],inner_saved_outer_fp_offset=-0xc,bytes=656,allocation_failure='stock save still executes; null trace bypasses proxy',free_boundary=0x534e8834),callback_filesystem_calls=0,foreign_caller_guard='inner saved LR fp-4 must equal534e882c; otherwise original two-argument bridge without reading caller owner',flush=flush,flush_contract='Synchronous sink after WriteStillFile inner cleanup; caller must establish task filesystem safety. No inferred RAW recipe identity.',task_identity='original WriteStillFile r1 descriptor from outerfp-38, not recipe',stock_cleanup_at_post_hook='534eb7e4 is bx lr; hook preserves all registers and NZCV')
 (out/'m10v_file_trace.bin').write_bytes(blob);(out/'patch-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return blob,manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--base',type=lambda x:int(x,0),required=True);p.add_argument('--trace-manifest',required=True);p.add_argument('--flush',type=lambda x:int(x,0),required=True);a=p.parse_args();blob,manifest=build(a.output,a.base,json.loads(Path(a.trace_manifest).read_text())['exports'],a.flush);print(json.dumps(manifest,indent=2))

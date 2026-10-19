"""Build isolated, SHA-locked UI169 deferred completion retry (no main builder)."""
import hashlib,importlib.util,json,shutil,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('save',ROOT/'scripts/build_gr3_save_trace.py');save=importlib.util.module_from_spec(spec);spec.loader.exec_module(save)
ASM='''
.syntax unified
.arm
.fpu neon
.text
.macro boundary name, displaced, source, helper, continuation
.global \\name
.type \\name,%function
\\name:
 \\displaced
 push {r0-r12,lr}
 mrs r7,cpsr
 vmrs r8,fpscr
 push {r7,r8}
 vpush {d0-d15}
 vpush {d16-d31}
 mov r0,\\source
 bl \\helper
 vpop {d16-d31}
 vpop {d0-d15}
 pop {r7,r8}
 vmsr fpscr,r8
 msr cpsr_f,r7
 pop {r0-r12,lr}
 b \\continuation
.endm
boundary m10v_view_hook_enter, "strb r3,[r0,#0x16c]", r0, m10v_view_deferred_on_enter, stock_enter_cont
boundary m10v_view_hook_capture, "strb r2,[r0,#0x2f]", r0, m10v_view_deferred_on_capture_start, stock_capture_cont
 .global m10v_view_hook_producer
.type m10v_view_hook_producer,%function
m10v_view_hook_producer:
 push {r0-r12,lr}
 mrs r7,cpsr
 vmrs r8,fpscr
 push {r7,r8}
 vpush {d0-d15}
 vpush {d16-d31}
 mov r0,r4
 bl m10v_view_deferred_on_producer
 vpop {d16-d31}
 vpop {d0-d15}
 pop {r7,r8}
 vmsr fpscr,r8
 msr cpsr_f,r7
 pop {r0-r12,lr}
 b stock_send
boundary m10v_view_hook_reply, "strb r3,[r4,#0x30]", r4, m10v_view_deferred_on_stop_reply, stock_reply_cont
'''
def build(out,base=0x54100000,rtos=None):
 if type(base)!=int or base&3 or not 0x540b6000<=base<=0x54fe0000:raise ValueError('invalid appendRX base')
 stock=Path(rtos or ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
 if hashlib.sha256(stock).hexdigest()!=save.SHA:raise ValueError('wrong locked RTOS')
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as d:
  d=Path(d);asm=d/'hook.S';asm.write_text(ASM);objects=[]
  for src in [ROOT/'native/gr3/m10v_view_deferred.c',asm]:
   obj=d/(src.stem+'.o');subprocess.run(['clang',*save.FLAGS,'-c',str(src),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
  link=d/'hook.ld';link.write_text('SECTIONS { . = '+hex(base)+'; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
  elfpath=out/'m10v_view_deferred.elf';subprocess.run([shutil.which('ld.lld') or 'ld.lld','-m','armelf','-T',str(link),'--defsym=stock_enter_cont=0x531cbdf4','--defsym=stock_capture_cont=0x5323abfc','--defsym=stock_reply_cont=0x53239bc4','--defsym=stock_send=0x532288b0',*map(str,objects),'-o',str(elfpath)],check=True,capture_output=True)
 elf=elfpath.read_bytes();rows=save.sections(elf);exports={};blob=None
 for name,r in rows:
  if r[2]&2 and r[5]:
   if r[2]&1 or name!='.text' or r[3]!=base or r[5]>0x2000:raise ValueError('unexpected allocation')
   blob=elf[r[4]:r[4]+r[5]]
  if r[1]==2:
   sr=rows[r[6]][1];strings=elf[sr[4]:sr[4]+sr[5]]
   for pos in range(r[4],r[4]+r[5],16):
    ni,val,length,info,other,index=struct.unpack_from('<IIIBBH',elf,pos);symbol=strings[ni:].split(b'\0',1)[0].decode()
    if symbol and not index:raise ValueError('undefined '+symbol)
    if symbol.startswith('m10v_view_') and info&15==2:exports[symbol]=val
 def bl(at,to):
  delta=to-at-8
  if delta&3 or not -(1<<25)<=delta<(1<<25):raise ValueError('branch range')
  return struct.pack('<I',0xeb000000|((delta>>2)&0xffffff))
 patches=[]
 def patch(at,old,new,role):
  if stock[at-0x53000000:at-0x53000000+len(old)]!=old:raise ValueError('original mismatch '+hex(at))
  patches.append(dict(address=at,expected_hex=old.hex(),replacement_hex=new.hex(),role=role))
 patch(0x531709fc,struct.pack('<I',0xe3a00f61),struct.pack('<I',0xe3000194),'QuickViewController allocation 184 to194')
 for at,expected,symbol in [(0x531cbdf0,0xe5c0316c,'m10v_view_hook_enter'),(0x5323abf8,0xe5c0202f,'m10v_view_hook_capture'),(0x53239bc0,0xe5c43030,'m10v_view_hook_reply')]:
  patch(at,struct.pack('<I',expected),struct.pack('<I',struct.unpack('<I',bl(at,exports[symbol]))[0]&~0x01000000),symbol)
 patch(0x53236768,bl(0x53236768,0x532288b0),bl(0x53236768,exports['m10v_view_hook_producer']),'native completion generation publication')
 patch(0x531cc1cc,bl(0x531cc1cc,0x531cbe78),bl(0x531cc1cc,exports['m10v_view_deferred_on_169']),'exact native UI169 handler call')
 manifest=dict(schema=1,base=base,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),required_rtos_sha256=save.SHA,exports=exports,patches=patches,mutable_global_bytes=0,filesystem_calls=0,camera_tested=False,storage=dict(owner='original QuickViewController factory allocation',original_bytes=0x184,extended_bytes=0x194,token_offset=0x184),contract='Defer only a real UI169 completion rejected for busy; retry only after original stop-response clears30; native capture-start and QuickView re-entry invalidate; no timer/event forgery, no busy clear.')
 (out/'m10v_view_deferred.bin').write_bytes(blob);(out/'patch-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return blob,manifest
if __name__=='__main__':
 blob,m=build('/tmp/m10v-view-deferred');print(json.dumps(m,indent=2))

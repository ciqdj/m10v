"""Observe the actual stock pool-release return without replacing its call."""
import hashlib,importlib.util,json,shutil,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('save',ROOT/'scripts/build_gr3_save_trace.py');save=importlib.util.module_from_spec(spec);spec.loader.exec_module(save)
ASM='''
.syntax unified
.arm
.text
.global m10v_pool_release_return
.type m10v_pool_release_return,%function
m10v_pool_release_return:
 push {r0-r12,lr}
 mrs r7,cpsr
 push {r7,r8}
 sub sp,sp,#8
 str r0,[sp]
 RAW_TOKEN_HOOK
 mov r0,r4
 mov r1,#184
 mov r2,r5
 mov r3,r6
 bl trace_mark
 add sp,sp,#8
 pop {r7,r8}
 msr cpsr_f,r7
 pop {r0-r12,lr}
 str r5,[sp,#8]
 b stock_continue
'''
def build(out,base,mark,rtos=None,raw_pool_return=None):
 for address in (base,mark,*([raw_pool_return] if raw_pool_return is not None else [])):
  if type(address)!=int or address&3 or not 0x540b6000<=address<0x54ff0000:raise ValueError('invalid appendRX address')
 stock=Path(rtos or ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
 if hashlib.sha256(stock).hexdigest()!=save.SHA:raise ValueError('wrong locked RTOS')
 at=0x53521e18;expected=bytes.fromhex('08508de5')
 if stock[at-0x53000000:at-0x53000000+4]!=expected:raise ValueError('wrong release continuation')
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as d:
  d=Path(d);source=d/'hook.S';source.write_text(ASM.replace('RAW_TOKEN_HOOK',('mov r3,r0\n mov r0,r4\n mov r1,r5\n mov r2,r6\n bl raw_pool_return' if raw_pool_return is not None else '')));obj=d/'hook.o';link=d/'hook.ld';link.write_text('SECTIONS { . = '+hex(base)+'; .text : { *(.text*) } /DISCARD/ : { *(.ARM.attributes) } }')
  subprocess.run(['clang',*save.FLAGS,'-c',str(source),'-o',str(obj)],check=True,capture_output=True)
  elf=out/'m10v_pool_release_trace.elf';subprocess.run([shutil.which('ld.lld') or 'ld.lld','-m','armelf','-T',str(link),'--defsym=trace_mark='+hex(mark),'--defsym=stock_continue=0x53521e1c',*(['--defsym=raw_pool_return='+hex(raw_pool_return)] if raw_pool_return is not None else []),str(obj),'-o',str(elf)],check=True,capture_output=True)
 data=elf.read_bytes();blob=None
 for name,row in save.sections(data):
  if row[2]&2 and row[5]:
   if name!='.text' or row[2]&1 or row[3]!=base:raise ValueError('unexpected allocated section '+name)
   blob=data[row[4]:row[4]+row[5]]
 if blob is None:raise ValueError('no code')
 offset=base-at-8
 if offset&3 or not -(1<<25)<=offset<(1<<25):raise ValueError('branch range')
 patch=dict(address=at,expected_hex=expected.hex(),replacement_hex=struct.pack('<I',0xea000000|((offset>>2)&0xffffff)).hex(),role='actual stock pool release return')
 manifest=dict(schema=1,base=base,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),required_rtos_sha256=save.SHA,exports={'m10v_pool_release_return':base},patches=[patch],mutable_global_bytes=0,raw_lifetime_helper=raw_pool_return,filesystem_calls=0,camera_tested=False,event_schema={'184':['recipe','buffer_id','backing','pool_dispatch_return']},stock_call_preserved=0x53521e14,stock_pool_dispatch=0x536a248c,limitations=['Pool dispatch returns 0 also for null/unrecognized pointers; this event alone does not prove successful free or memory reuse.','RAW transfer/clear and file status require separate correlation.','No guaranteed drain follows the last JPEG phase; retirement may discard this recipe-owned record before it reaches SD.'],requires='Existing recipe trace allocation and m10v_save_trace_recipe_mark; bounded append may drop if full.')
 (out/'m10v_pool_release_trace.bin').write_bytes(blob);(out/'patch-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return blob,manifest

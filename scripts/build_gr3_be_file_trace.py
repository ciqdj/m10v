"""Build actual BE blocking file boundary hooks with unchanged stock SP."""
import argparse,hashlib,importlib.util,json,shutil,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('save_trace_builder',ROOT/'scripts/build_gr3_save_trace.py');save=importlib.util.module_from_spec(spec);spec.loader.exec_module(save)
ASM='''
.syntax unified
.arm
.text
.global m10v_be_file_pre
.type m10v_be_file_pre,%function
m10v_be_file_pre:
 push {r0-r12,lr}
 mrs r4,cpsr
 push {r4,r5}
 mov r0,fp
 mov r1,r5
 bl m10v_be_file_begin
 pop {r4,r5}
 msr cpsr_f,r4
 pop {r0-r12,lr}
 b stock_file
.global m10v_be_file_post
.type m10v_be_file_post,%function
m10v_be_file_post:
 push {r0-r12,lr}
 mrs r4,cpsr
 push {r4,r5}
 mov r2,r0
 mov r0,fp
 mov r1,r5
 bl m10v_be_file_finish
 pop {r4,r5}
 msr cpsr_f,r4
 pop {r0-r12,lr}
 ldrb r3,[fp,#-0x3c]
 b stock_continue
'''
def build(out,base,trace_exports,flush,rtos=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 if base&3 or not 0x540b6000<=base<=0x54ff0000:raise ValueError('invalid code base')
 for address in [flush,trace_exports['m10v_save_trace_init'],trace_exports['m10v_save_trace_append']]:
  if address&3 or not 0x53000000<=address<0x55000000:raise ValueError('invalid function address')
 stock=Path(rtos or ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
 if hashlib.sha256(stock).hexdigest()!=save.SHA:raise ValueError('wrong locked RTOS')
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp);asm=temp/'file.S';asm.write_text(ASM);script=temp/'link.ld';script.write_text('SECTIONS { . = '+hex(base)+'; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }')
  objects=[]
  for source in [ROOT/'native/gr3/m10v_be_file_trace.c',asm]:
   obj=temp/(source.stem+'.o');subprocess.run(['clang',*save.FLAGS,'-c',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(obj)
   for name,row in save.sections(obj.read_bytes()):
    if row[2]&3==3 and row[5]:raise ValueError('writable section '+name)
  elfpath=out/'m10v_be_file_trace.elf';defs={**{name:trace_exports[name] for name in ['m10v_save_trace_init','m10v_save_trace_append']},'m10v_lifecycle_file_flush':flush,'stock_file':0x53697658,'stock_continue':0x5350b388}
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
    if symbol.startswith('m10v_be_file_') and info&15==2:exports[symbol]=value
 if blob is None:raise ValueError('no text')
 def bl(at,target):
  off=target-at-8
  if off&3 or not -(1<<25)<=off<(1<<25):raise ValueError('BL range')
  return struct.pack('<I',0xeb000000|((off>>2)&0xffffff))
 patches=[]
 def patch(at,expected,replacement,role):
  if stock[at-0x53000000:at-0x53000000+4]!=expected:raise ValueError('stock mismatch '+hex(at))
  patches.append(dict(address=at,expected_hex=expected.hex(),replacement_hex=replacement.hex(),role=role))
 patch(0x5350b380,bl(0x5350b380,0x53697658),bl(0x5350b380,exports['m10v_be_file_pre']),'actual BE file begin')
 at=0x5350b384;target=exports['m10v_be_file_post'];off=target-at-8
 if off&3 or not -(1<<25)<=off<(1<<25):raise ValueError('B range')
 patch(at,bytes.fromhex('3c305be5'),struct.pack('<I',0xea000000|((off>>2)&0xffffff)),'actual BE file return')
 manifest=dict(schema=1,base=base,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),required_rtos_sha256=save.SHA,exports=exports,patches=patches,mutable_global_bytes=0,camera_tested=False,owner=dict(storage='optional heap referenced by original caller outgoing slot fp-54',bytes=656,frame_growth=0,descriptor_fp_offset=-0x4c,pointer_fp_offset=-0x54),callback_filesystem_calls=0,flush=flush,flush_contract='Synchronous caller sink after original blocking operation returns; task-level filesystem safety remains required.',identity='Opaque original r1 context preserved in r5; never recipe or file number',event_schema={'200':['context_cookie','begin_usec','begin_sec','clock_status'],'201':['context_cookie','end_usec','end_sec','file_result_with_clock_status'],'202':['context_cookie','stage_status','frame_slot','file_result'],'203':['context_cookie','context_vptr','parameters_pointer_value','shooting_info_pointer_value']},stage_status={'0':'success','2':'open error','4':'metadata error','6':'close error'},stock_callee=0x53697658,stock_call_sp='unchanged',limitations=['No proven RAW recipe correlation','No physical media durability proof','Optional trace allocation failure leaves stock operation unchanged'])
 (out/'m10v_be_file_trace.bin').write_bytes(blob);(out/'patch-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return blob,manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--base',type=lambda x:int(x,0),required=True);p.add_argument('--trace-manifest',required=True);p.add_argument('--flush',type=lambda x:int(x,0),required=True);a=p.parse_args();blob,manifest=build(a.output,a.base,json.loads(Path(a.trace_manifest).read_text())['exports'],a.flush);print(json.dumps(manifest,indent=2))

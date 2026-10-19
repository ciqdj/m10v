"""Exact GR3 JPEG callsite tracing; preserve native stack arguments and waits."""
import struct
from scripts.build_gr3_menu_patches import assembly,branch

def build_hooks(base,callback):
 image=bytearray();patches=[]
 for address,event,expected,tail in (
  (0x535048ec,191,0xe51b5060,'ldr r5,[fp,#-0x60];b 0x535048f0'),
  (0x53504948,192,branch(0x53504948,0x536bbc30,True),'b 0x536bbc30')):
  entry=base+len(image)
  code=assembly('push {r0-r12,lr};mrs r0,cpsr;mov r1,sp;bic sp,sp,#7;sub sp,sp,#8;stm sp,{r0,r1};'
    'ldr r2,[r1];mov r0,r4;'+f'mov r1,#{event};bl {hex(callback)};'+
    'ldm sp,{r0,r1};mov sp,r1;msr cpsr_fs,r0;pop {r0-r12,lr};'+tail,entry)
  image+=code
  patches.append(dict(address=address,event=event,entry=entry,expected_hex=struct.pack('<I',expected).hex(),
    replacement_hex=struct.pack('<I',branch(address,entry,event==192)).hex(),kind='preserve-all-inline' if event==191 else 'preserve-all-call'))
 return bytes(image),dict(base=base,bytes=len(image),patches=patches,
  native_call_preserved=True,native_wait_preserved=True,stack_arguments_untouched=True)

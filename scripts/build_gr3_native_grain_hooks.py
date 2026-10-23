"""Borrow the original grain planning/execution stages at four exact callsites.

No independent DMA, allocation, SD or mutable globals. The two displaced
functions have verified three-register AAPCS arguments and no stack arguments.
"""
import hashlib,json,struct
from pathlib import Path
from scripts.build_gr3_menu_patches import assembly,branch
ROOT=Path(__file__).resolve().parents[1]
SHA='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
SITES={0x53513620:0xe1a00004,0x535033d8:0xebffff1b,0x53503aa0:0xebfffd69,0x53503ab4:0xeb05f4c0}
HELPERS=('m10v_isp_frame_recipe_grain_settings','m10v_isp_frame_recipe_grain_done')
# 56 GPR bytes, 8 flags/FPSCR bytes, 256 VFP bytes; original r0 at+264.
SAVE='push {r0-r12,lr};mrs r0,cpsr;vmrs r1,fpscr;push {r0,r1};vpush {d0-d15};vpush {d16-d31};'
RESTORE='vpop {d16-d31};vpop {d0-d15};pop {r0,r1};vmsr fpscr,r1;msr cpsr_f,r0;pop {r0-r12,lr};'

def build(out,base,exports,rtos=None,appended_slots=False):
    if type(base)is not int or base&3 or not 0x540b6000<=base<=0x54fe0000:raise ValueError('invalid isolated appendRX base')
    if any(type(exports.get(k))is not int or exports[k]&3 or not 0x53000000<=exports[k]<0x55000000 for k in HELPERS):raise ValueError('both recipe grain ARM helper exports required')
    rom=bytes(rtos) if rtos is not None else (ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
    for at,word in SITES.items():
        if at-0x53000000+4>len(rom) or struct.unpack_from('<I',rom,at-0x53000000)[0]!=word:raise ValueError('grain hook preimage differs at '+hex(at))
    if hashlib.sha256(rom).hexdigest()!=SHA:raise ValueError('requires exact original RTOS hash')
    code=b'';patches=[]
    def emit(site,text,link=True):
        nonlocal code
        entry=base+len(code);fragment=assembly(".fpu neon\n"+text,entry);code+=fragment
        patches.append(dict(address=site,entry=entry,expected_hex=struct.pack('<I',SITES[site]).hex(),replacement_hex=struct.pack('<I',branch(site,entry,link=link)).hex()))
    gate='sub r0,r0,#25;cmp r0,#4;bhi grain_gate_end;' if appended_slots else 'cmp r0,#12;beq grain_request;sub r0,r0,#18;cmp r0,#3;bhi grain_gate_end;'
    emit(0x53513620,SAVE+'ldrb r0,[r5,#0x77c];'+gate+'grain_request:;mov r0,#1;strb r0,[r4,#0x24];grain_gate_end:;'+RESTORE+'mov r0,r4;b 0x53513624',False)
    for site,phase in ((0x535033d8,0),(0x53503aa0,1)):
        # The fixed sixteen-byte wrapper frame keeps SP aligned. Original
        # register arguments are untouched; only callee-saved scratch is used.
        capture='mov r6,ip;' if phase==0 else 'mov r6,r4;'
        emit(site,'push {r4,r5,r6,lr};mov r5,r0;'+capture+'bl 0x5350304c;'+SAVE+'mov r0,r6;mov r1,r5;mov r2,#'+str(phase)+';bl '+hex(exports[HELPERS[0]])+';cmp r0,#1;ldreq r0,[sp,#264];orreq r0,r0,#1;streq r0,[sp,#264];'+RESTORE+'pop {r4,r5,r6,pc};')
    emit(0x53503ab4,'push {r4,r5,r6,lr};mov r5,r1;mov r6,r4;bl 0x53680dbc;'+SAVE+'mov r0,r6;mov r1,r5;ldr r2,[sp,#264];bl '+hex(exports[HELPERS[1]])+';'+RESTORE+'pop {r4,r5,r6,pc};')
    if len(code)>700:raise ValueError('grain hooks exceed700-byte budget')
    manifest=dict(schema='gr3-native-grain-hooks/v1',base=base,bytes=len(code),patches=patches,exports={k:exports[k] for k in HELPERS},required_rtos_sha256=SHA,mutable_global_bytes=0,filesystem_calls=0,allocator_calls=0,independent_dma=False,cpu_noise_processing=False,software_fallback=False,camera_tested=False,
      appended_slots=appended_slots,original_abi={'settings':0x5350304c,'execution':0x53680dbc,'arguments':'verified r0,r1,r2 only; no stack arguments','wrapper_frame_bytes':16,'helper_save_bytes':320,'vfp':'all d0-d31 and FPSCR restored to original postcall state','result':'original r0; settings may OR1 only when helper returns1','post_gate':'all GPR/flags/VFP preserved except displaced mov r0,r4 and legal request+24=1','zero_grain':'postgate only enables traversal, original plan sizing remains0'})
    out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'native-grain-hooks.bin').write_bytes(code);(out/'native-grain-hooks.json').write_text(json.dumps(manifest,indent=2)+'\n');return code,manifest

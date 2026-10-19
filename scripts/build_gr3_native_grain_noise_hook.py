"""Borrow the stock Granulation RNG call and its checked execution owner chain."""
import hashlib,json,struct
from pathlib import Path
from scripts.build_gr3_menu_patches import assembly,branch
ROOT=Path(__file__).resolve().parents[1]
SHA='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
SITE=0x5367ae14
HELPER='m10v_isp_frame_recipe_grain_noise'
SAVE='push {r0-r12,lr};mrs r0,cpsr;vmrs r1,fpscr;push {r0,r1};vpush {d0-d15};vpush {d16-d31};'
RESTORE='vpop {d16-d31};vpop {d0-d15};pop {r0,r1};vmsr fpscr,r1;msr cpsr_f,r0;pop {r0-r12,lr};'
def build(out,base,exports,expected_stage_return,rtos=None):
    if type(base)is not int or base&3 or not 0x540b6000<=base<=0x54fe0000:raise ValueError('invalid appendRX base')
    helper=exports.get(HELPER)
    if type(helper)is not int or helper&3 or not 0x53000000<=helper<0x55000000:raise ValueError('recipe noise helper ARM export required')
    if type(expected_stage_return)is not int or expected_stage_return&3 or not 0x53000000<=expected_stage_return<0x55000000:raise ValueError('verified dispatcher return PC required')
    rom=bytes(rtos) if rtos is not None else (ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
    if hashlib.sha256(rom).hexdigest()!=SHA:raise ValueError('requires exact original RTOS hash')
    word=struct.unpack_from('<I',rom,SITE-0x53000000)[0]
    if word!=branch(SITE,0x5368a92c,link=True):raise ValueError('original RNG BL differs')
    text='.fpu neon\npush {r4,r5,r6,lr};mov r4,r0;mov r5,r1;mov r6,fp;bl 0x5368a92c;'+SAVE
    # Native Granulation fp was established by the original function; inspect
    # only its known local/saved-frame fields before following any pointer.
    text+='ldr r0,[r6,#-4];movw r1,#0x1050;movt r1,#0x5368;cmp r0,r1;bne noise_end;'
    text+='ldr r0,[r6,#-12];tst r0,#3;bne noise_end;cmp r0,r6;bls noise_end;cmp r0,#0x80000000;bhs noise_end;'
    # Original dispatcher push44 + locals52 places its fp exactly96 bytes
    # above Granulation fp. Bind this exact frame layout before dereferencing.
    text+='sub r1,r0,r6;cmp r1,#0x60;bne noise_end;'
    text+='ldr r1,[r0,#-4];movw r2,#'+str(expected_stage_return&65535)+';movt r2,#'+str(expected_stage_return>>16)+';cmp r1,r2;bne noise_end;'
    text+='ldr r0,[r0,#-40];mov r1,r4;mov r2,r5;ldr r3,[r6,#-0x64c];sub sp,sp,#8;'
    text+='ldr ip,[r6,#-0x644];str ip,[sp];ldr ip,[r6,#-0x650];str ip,[sp,#4];bl '+hex(helper)+';add sp,sp,#8;'
    text+='noise_end:;'+RESTORE+'pop {r4,r5,r6,lr};bx lr;'
    code=assembly(text,base)
    if len(code)>350:raise ValueError('noise wrapper exceeds350-byte budget')
    patch=dict(address=SITE,entry=base,expected_hex=struct.pack('<I',word).hex(),replacement_hex=struct.pack('<I',branch(SITE,base,link=True)).hex())
    report=dict(schema='gr3-native-grain-noise-hook/v1',base=base,bytes=len(code),patches=[patch],exports={HELPER:helper},required_rtos_sha256=SHA,expected_stage_return=expected_stage_return,
        granulation_return=0x53681050,dispatcher_frame_delta=0x60,owner_source='dispatcher saved r4 at fp-0x28; recipe helper validates Digital C ownership',
        original_rng=0x5368a92c,cache_clean_after_hook=0x5367ae24,
        frame_offsets={'Granulation_saved_fp':-12,'Granulation_saved_lr':-4,'width':-0x64c,'height':-0x644,'stride':-0x650,'dispatcher_saved_r4':-40},
        helper_abi='r0=C,r1=noise,r2=bytes,r3=width,stack0=height,stack4=stride',
        original_rng_abi='two register arguments; original RNG executes first',
        wrapper_stack_bytes=344,mutable_global_bytes=0,allocator_calls=0,independent_dma=False,camera_tested=False)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'native-grain-noise-hook.bin').write_bytes(code)
    (out/'native-grain-noise-hook.json').write_text(json.dumps(report,indent=2)+'\n')
    return code,report

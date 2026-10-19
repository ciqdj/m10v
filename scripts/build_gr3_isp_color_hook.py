"""Build an actual Still Make gamma call-site hook with immutable slot ingress.

This is opt-in build-time slot selection, not dynamic SD-library selection.
Only explicit matrix/curve/post targets are accepted; 3D LUT fits are rejected.
"""
import hashlib,json,os,shutil,struct,subprocess,tempfile
from pathlib import Path
from scripts.build_gr3_m10v_library import ROOT,FLAGS,link_object
from scripts.build_gr3_menu_patches import assembly,branch
SHA='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
SITE=0x536ddbe8
EXPECTED=0xeb002d04

def validate_slots(slots):
    if not isinstance(slots,list) or len(slots)!=5:raise ValueError('exactly five explicit slot targets required')
    result=[]
    for slot in slots:
        if slot is None:result.append(None);continue
        if slot.get('kind')!='matrix-curves-post':raise ValueError('arbitrary 3D LUT or fitted targets are unsupported')
        vals=[]
        for name,n,lo,hi in [('matrix_q13',9,-32768,32767),('post_q9',9,-32768,32767),('curves',768,0,16383)]:
            v=slot.get(name)
            if not isinstance(v,list) or len(v)!=n or any(type(x)!=int or not lo<=x<=hi for x in v):raise ValueError('invalid '+name)
            vals.append(v)
        if any(vals[2][c*256+i]<vals[2][c*256+i-1] for c in range(3) for i in range(1,256)):raise ValueError('nonmonotone curves')
        result.append(vals)
    return result

def build(out,slots,rom,base=0x54170000):
    rom=bytes(rom)
    if hashlib.sha256(rom).hexdigest()!=SHA:raise ValueError('requires exact official GR III 2.10 RTOS')
    if struct.unpack_from('<I',rom,SITE-0x53000000)[0]!=EXPECTED:raise ValueError('gamma BL differs')
    if type(base)!=int or base&3 or not 0x540b6000<=base<=0x54fe0000:raise ValueError('invalid appendRX base')
    parsed=validate_slots(slots)
    compiler=os.environ.get('M10V_LLVM_CLANG') or '/opt/homebrew/opt/llvm/bin/clang'
    if not Path(compiler).is_file():compiler=shutil.which('clang')
    with tempfile.TemporaryDirectory() as d:
        d=Path(d)
        config='static const uint8_t m10v_isp_slot_enabled[5]={'+','.join('1' if s else '0' for s in parsed)+'};\n'
        config+='static const m10v_isp_frame_target m10v_isp_slot_targets[5]={\n'
        for s in parsed:
            if s is None:config+='{{0},{0},{{0}}},\n';continue
            m,p,c=s
            config+='{'+','.join('{'+','.join(map(str,v))+'}' for v in (m,p)) + ',{'+','.join('{'+','.join(map(str,c[i:i+256]))+'}' for i in range(0,768,256))+'}},\n'
        config+='};\n';(d/'m10v_isp_slot_config.h').write_text(config)
        # Single translation unit allows the bounded relocator to verify every
        # section and resolve writer calls without a permissive ELF linker.
        (d/'module.c').write_text('#include "'+str(ROOT/'native/gr3/m10v_isp_frame_color.c')+'"\n#include "'+str(ROOT/'native/gr3/m10v_isp_color_hook.c')+'"\n')
        obj=d/'module.o'
        subprocess.run([compiler,*FLAGS,'-I'+str(d),'-c',str(d/'module.c'),'-o',str(obj)],capture_output=True,check=True)
        code,symbols=link_object(obj.read_bytes(),base,prefix='m10v_isp_frame_',additional_exports=('m10v_isp_frame_color_hook_gamma',))
    entry=base+len(code)
    # Original gamma uses stack bytes in its cache: run it first at exactly
    # the stock SP. Then save all observable original registers around apply.
    # This is an AAPCS BL boundary; NZCV is caller-clobbered.
    code+=assembly('bl 0x536e9000;push {r0-r11,ip,lr};ldr r0,[r5,#0x17c];mov r1,r4;mov r2,r6;mov r3,r5;bl '+hex(symbols['m10v_isp_frame_color_hook_gamma'])+';pop {r0-r11,ip,lr};movw lr,#0xdbec;movt lr,#0x536d;b 0x536ddbec',entry)
    patch={'address':SITE,'expected':EXPECTED,'entry':entry,'word':branch(SITE,entry,link=True)}
    manifest=dict(schema=1,base=base,bytes=len(code),symbols=symbols,patches=[patch],required_rtos_sha256=SHA,mutable_global_bytes=0,filesystem_calls=0,allocator_calls=0,selection='immutable ROM slots selected by this frame original stage1 ShootingInfo tone',enabled_slots=[i for i,s in enumerate(parsed) if s],camera_tested=False,quality_equivalence_proven=False,dynamic_sd_selection=False,scope='matrix-curves-post only; no arbitrary 3D LUT or spatial effects',original_abi={'callsite':SITE,'callee':0x536e9000,'r0':'Gamma','r1':'stack context','r2':'info+0x120','apply_r0':'r5+0x17c Gamma','apply_r1':'r4 context','apply_r2':'r6 info','apply_r3':'r5 ImageTuning','return':'original r0','preserves':'original gamma r0-r12, lr and sp; NZCV caller-clobbered'})
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'isp-color-hook.bin').write_bytes(code);(out/'isp-color-hook.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return code,manifest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True);p.add_argument('--slots',required=True,help='JSON array: five explicit matrix-curves-post targets or null')
    p.add_argument('--rtos',required=True);p.add_argument('--base',type=lambda s:int(s,0),default=0x54170000)
    a=p.parse_args();code,m=build(a.out,json.loads(Path(a.slots).read_text()),Path(a.rtos).read_bytes(),a.base)
    print(json.dumps({'bytes':len(code),'patches':m['patches'],'dynamic_sd_selection':False,'quality_equivalence_proven':False},indent=2))

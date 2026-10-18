"""Independent GR4 center-style level slider; all mutable sites verified."""
import json,hashlib,shutil,struct,subprocess,tempfile
from pathlib import Path
from scripts.build_gr3_m10v_library import FLAGS,link_object
from scripts.build_gr3_menu_patches import assembly
ROOT=Path(__file__).resolve().parents[1]
BASE=0x53000000
CALLBACK_POINTER=0x53d95260
FRAME_VTABLE=0x53e98890
RTOS_SHA='a9a9a51530c35819df47dee1cce9f4f560a17eeed1da258950167d282884fce1'
PROFILE=json.loads((ROOT/'native/gr4/level-abi.json').read_text())
def compile_level(base,rtos=None):
 original=(ROOT/'data/research/gr4/RTOS.bin').read_bytes() if rtos is None else rtos
 if rtos is None and hashlib.sha256(original).hexdigest()!=RTOS_SHA:raise ValueError('GR4 level requires official1.11 RTOS')
 table_bytes=original[FRAME_VTABLE-BASE-8:FRAME_VTABLE-BASE+22*4]
 if hashlib.sha256(table_bytes).hexdigest()!=PROFILE['frame_vtable_sha256']:raise ValueError('GR4 FrameView vtable preimage differs')
 with tempfile.TemporaryDirectory(prefix='m10v-gr4-level-') as folder:
  obj=Path(folder)/'level.o'
  subprocess.run([shutil.which('clang'),*FLAGS,'-c',str(ROOT/'native/gr4/m10v_level.c'),'-o',str(obj)],check=True,capture_output=True)
  provisional,symbols=link_object(obj.read_bytes(),base,{'m10v_level_frame_vtable':base},'m10v_level_')
  vt_at=(base+len(provisional)+15)&~15
  table=bytearray(table_bytes);struct.pack_into('<I',table,8+19*4,symbols['m10v_level_draw'])
  getter=vt_at+len(table);vt=vt_at+8;stub=assembly(f'movw r0,#{vt&65535};movt r0,#{vt>>16};bx lr',getter)
  code,symbols=link_object(obj.read_bytes(),base,{'m10v_level_frame_vtable':getter},'m10v_level_');blob=code+bytes(vt_at-base-len(code))+table+stub
 return blob,{'schema':'m10v-gr4-level-slider/v1','base':base,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'native/gr4/m10v_level.c').read_bytes()).hexdigest(),'symbols':symbols,'private_vtable':vt,'original_vtable':FRAME_VTABLE,'draw_slot':19,'contracts':PROFILE['contracts'],'abi_preimages':PROFILE['preimages'],'frame_vtable_sha256':PROFILE['frame_vtable_sha256'],'hook':{'address':CALLBACK_POINTER,'expected':0x5318d8f0,'replacement':symbols['m10v_level_callback']},'camera_tested':False}
def apply_level(patch):
 for row in PROFILE['preimages']:
  a=row['address']-BASE;expected=bytes.fromhex(row['expected'])
  if bytes(patch.image[a:a+len(expected)])!=expected:raise ValueError('GR4 level preimage differs: '+row['contract'])
 if patch.word(CALLBACK_POINTER)!=0x5318d8f0:raise ValueError('GR4 level callback preimage differs')
 # The verified candidate already contains every original dependency. Production
 # builds must not depend on an untracked, locally extracted research RTOS.
 base=(BASE+len(patch.image)+15)&~15;blob,report=compile_level(base,rtos=patch.image);actual=patch.append(blob,16)
 if actual!=base:raise ValueError('GR4 level append address contract differs')
 patch.set_word(CALLBACK_POINTER,report['symbols']['m10v_level_callback'],'M10V center-style level slider callback');return report

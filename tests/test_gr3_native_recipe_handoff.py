"""Installed StillMake must apply native color and authorize exactly one shot."""
import tempfile,unittest,struct,zlib
from unicorn import UC_HOOK_CODE
from unicorn import arm_const as A
from tests import test_gr3_isp_recipe_color as prior
library_fragment,state,StockISP,BASE,ROOT=prior.library_fragment,prior.state,prior.StockISP,prior.BASE,prior.ROOT
from scripts.build_gr3_isp_recipe_color import build
class NativeRecipeHandoffTests(unittest.TestCase):
 def fixture(self,tone=12,stage=0):
  e,r,o,i,c,si=prior.RecipeColorTests.fixture(self,tone,stage)
  # Execute the actual stock case5 metadata writes. The first field is
  # at R+96c: stock writes source+1a8 to R+99c (C+30), not R+9a0.
  e.w32(r+0x44c8,si);e.w32(r+0x5c,e.alloc(64))
  e.u.reg_write(A.UC_ARM_REG_R0,r);e.u.reg_write(A.UC_ARM_REG_R4,r)
  e.u.emu_start(0x5350eb10,0x5350eb38,count=100)
  own=r+0x96c
  self.assertEqual(int.from_bytes(e.u.mem_read(own+0x30,4),'little'),r+0x1a8)
  self.assertEqual(int.from_bytes(e.u.mem_read(own+0x34,4),'little'),si)
  return e,r,o,i,own,si
 snapshot=prior.RecipeColorTests.snapshot
 callback=prior.RecipeColorTests.callback
 status=prior.RecipeColorTests.status
 @classmethod
 def setUpClass(cls):
  cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
  with tempfile.TemporaryDirectory() as d:
   cls.libbase,cls.libcode,cls.libsymbols=library_fragment(d)
   owner={'storage':{'color_offset':0x4a08,'color_bytes':1716,'extended_recipe_bytes':0x50f0},'patches':[{'address':0x53523e0c}]}
   cls.code,cls.manifest=build(d,cls.rom,cls.libsymbols,owner,observer=False,native_color=True,native_grain=True)
  candidate=bytearray(cls.rom)
  for at,code in ((cls.libbase,cls.libcode),(cls.manifest['base'],cls.code)):
   end=at-BASE+len(code)
   if end>len(candidate):candidate.extend(bytes(end-len(candidate)))
   candidate[at-BASE:end]=code
  for p in cls.manifest['patches']:candidate[p['address']-BASE:p['address']-BASE+4]=bytes.fromhex(p['replacement_hex'])
  cls.candidate=bytes(candidate)
 # Native profiles intentionally have different frame banks from old CPU LUTs.
 def test_phoenix_ei120_reaches_installed_still_native_profile(self):
  e,r,o,i,c,si=self.fixture();data=bytearray(state((67,)*5));data[61]=1
  struct.pack_into('<I',data,100,zlib.crc32(data[:100]))
  self.assertEqual(self.snapshot(e,r,data)[0],1)
  observed=[];prepare=self.manifest['exports']['m10v_isp_native_look_prepare']
  e.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:observed.append((u.reg_read(A.UC_ARM_REG_R1),u.reg_read(A.UC_ARM_REG_R2))) if a==prepare else None)
  self.callback(e,o,i,c)
  self.assertEqual(self.status(e,r),2)
  self.assertEqual(observed,[(67,1)])
 def test_unsupported_3d_lut_and_wrong_si_leave_frame_stock(self):
  e,r,o,i,c,si=self.fixture();self.snapshot(e,r,state((67,)*5));self.callback(e,o,i,c);self.assertEqual(self.status(e,r),2)
 def test_installed_native_apply_has_exact_per_shot_completion_identity(self):
  for film in (33,35,66,67,68):
   for tone in (12,18,19,20,21):
    with self.subTest(film=film,tone=tone):
     e,r,o,i,c,si=self.fixture(tone);self.snapshot(e,r,state((film,)*5));self.callback(e,o,i,c);self.assertEqual(self.status(e,r),2)
     completed=self.manifest['exports']['m10v_isp_frame_recipe_completed'];data=e.alloc(104);e.u.mem_write(data,state((film,)*5))
     e.call(completed,r,si,tone,data);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
     e.call(completed,r,si+4,tone,data);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),0)
     e.u.mem_write(data,state((film,)*5,sequence=9));e.call(completed,r,si,tone,data);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),0)
 def test_grain_completion_requires_matching_plan_execution_and_native_success(self):
  import struct,zlib
  e,r,o,i,c,si=self.fixture();data=bytearray(state((67,)*5));data[14]=2;data[56]=1;struct.pack_into('<I',data,100,zlib.crc32(data[:100]));self.snapshot(e,r,data);self.callback(e,o,i,c)
  self.assertIn('m10v_isp_frame_recipe_grain_settings',self.manifest['exports'])
  settings=self.manifest['exports']['m10v_isp_frame_recipe_grain_settings'];done=self.manifest['exports']['m10v_isp_frame_recipe_grain_done'];complete=self.manifest['exports']['m10v_isp_frame_recipe_completed']
  params=e.alloc(0x40);values=e.alloc(12);e.w32(params+0x10,values);digital=r+0x4320;e.u.mem_write(digital,bytes(e.u.mem_read(c,0x40)));c=digital;e.w32(c,0x53d0fc60);source=e.alloc(104);e.u.mem_write(source,bytes(data))
  e.call(settings,c,params,1);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),0)
  e.call(settings,c,params,0);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1);self.assertEqual(struct.unpack('<h',e.u.mem_read(values+4,2))[0],2)
  e.call(done,c,params,1);e.call(complete,r,si,12,source);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
  e.call(settings,c,params,1);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
  e.call(done,c,params,0);e.call(complete,r,si,12,source);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
  e.call(settings,c,params,1);noise=e.alloc(256);e.u.mem_write(noise,bytes(range(256)));e.u.mem_write(0x5effff00,struct.pack('<II',16,16));e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_noise'],c,noise,256,16);e.call(done,c,params,1);e.call(complete,r,si,12,source);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),3)

 def test_foreign_destination_cannot_publish_native_completion_for_source_recipe(self):
  e,r,o,i,c,si=self.fixture();self.snapshot(e,r,state((67,)*5));foreign=e.alloc(0x100);e.u.mem_write(foreign,bytes(e.u.mem_read(c,0x100)));before=bytes(e.u.mem_read(i,0x9000));self.callback(e,o,i,foreign)
  self.assertEqual(self.status(e,r),1);self.assertEqual(bytes(e.u.mem_read(i,0x9000)),before)

 def test_native_grain_completion_does_not_require_color_begin_success(self):
  import struct,zlib
  e,r,o,i,c,si=self.fixture();data=bytearray(state((67,)*5));data[14]=2;data[56]=0;struct.pack_into('<I',data,100,zlib.crc32(data[:100]));self.snapshot(e,r,data)
  digital=r+0x4320;e.u.mem_write(digital,bytes(e.u.mem_read(c,0x40)));e.w32(digital,0x53d0fc60)
  params=e.alloc(0x40);values=e.alloc(12);e.w32(params+0x10,values);noise=e.alloc(256);source=e.alloc(104);e.u.mem_write(source,bytes(data))
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_settings'],digital,params,0)
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_settings'],digital,params,1)
  e.u.mem_write(0x5effff00,struct.pack('<II',16,16));e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_noise'],digital,noise,256,16)
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_done'],digital,params,1)
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_completed'],r,si,12,source);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),2)

 def test_successful_native_grain_is_not_reapplied_when_size_hook_was_unavailable(self):
  import struct,zlib
  e,r,o,i,c,si=self.fixture();data=bytearray(state((67,)*5));data[14]=2;data[56]=1;struct.pack_into('<I',data,100,zlib.crc32(data[:100]));self.snapshot(e,r,data)
  digital=r+0x4320;e.u.mem_write(digital,bytes(e.u.mem_read(c,0x40)));e.w32(digital,0x53d0fc60)
  params=e.alloc(0x40);values=e.alloc(12);e.w32(params+0x10,values);source=e.alloc(104);e.u.mem_write(source,bytes(data))
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_settings'],digital,params,0)
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_settings'],digital,params,1)
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_grain_done'],digital,params,1)
  e.call(self.manifest['exports']['m10v_isp_frame_recipe_completed'],r,si,12,source);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),2)
  self.assertEqual(e.u.mem_read(r+0x4a08+40+7*4,4),bytes(4))

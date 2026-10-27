"""Execute actual IIIx candidate marker hooks, including stock enum6 for71mm."""
import json
import os
from pathlib import Path
import struct
import unittest
from unicorn import UC_HOOK_CODE,arm_const as A
from tests.test_gr3_isp_base import StockISP
class Gr3xFinalZoom(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  folder=os.environ.get('M10V_GR3X_CANDIDATE')
  if not folder:raise unittest.SkipTest('Set M10V_GR3X_CANDIDATE to actual candidate directory')
  cls.folder=Path(folder);cls.m=json.loads((cls.folder/'M10V-runtime-manifest.json').read_text());cls.rom=(cls.folder/'final-rtos.bin').read_bytes()
  assert cls.m['camera_model']=='gr3x'
  for patch in cls.m['zoom']['patches']:assert struct.unpack_from('<I',cls.rom,patch['address']-0x53000000)[0]==patch['replacement']
 def test_actual_writer_reader_roundtrip_default_and_custom_lens_values(self):
  for mm,bits,marker in [(40,0x3f800000,[0,0,0]),(50,0x3fa00000,[0,5,0]),(71,0x3fe49249,[0,6,0]),(60,0x3fc00000,[0,160,1])]:
   with self.subTest(mm=mm):
    e=StockISP(self.rom);ctx=e.alloc(64);props=e.alloc(0x800);ifd=e.alloc(64);state=e.alloc(0x800)
    e.w32(ctx+0x1c,props);e.w32(props+0x7b8,bits);e.w32(ifd+8,3)
    def boundary(u,at,n,data):
     if at not in (0x535d02b4,0x535d04bc):return
     obj=u.reg_read(A.UC_ARM_REG_R0);index=u.reg_read(A.UC_ARM_REG_R1)
     if at==0x535d02b4:u.mem_write(obj+16+index,bytes([u.reg_read(A.UC_ARM_REG_R2)&255]))
     else:u.reg_write(A.UC_ARM_REG_R0,u.mem_read(obj+16+index,1)[0])
     u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
    e.u.hook_add(UC_HOOK_CODE,boundary)
    e.call(0x53604b18,ctx,ifd);self.assertEqual(list(e.u.mem_read(ifd+16,3)),marker)
    e.call(0x535beffc,ctx,ifd,state);self.assertEqual(struct.unpack('<I',e.u.mem_read(state+0x7b8,4))[0],bits)
    e.call(self.m['symbols']['m10v_zoom_capture_caption'],bits)
    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1063 if mm==60 else 0xffffffff)

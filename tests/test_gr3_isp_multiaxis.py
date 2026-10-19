"""CPU ABI/packing equivalence only; hardware color fidelity is not emulated."""
import random,struct,tempfile,unittest
from pathlib import Path
from scripts.build_gr3_isp_multiaxis import build
from tests.test_gr3_isp_base import StockISP,ROOT,BASE
MASKS=bytes([255,15]*16+[15]*20+[255,15,0,0]*540+[255,3,0,0]*360+[63,0]+[255,15]*8+[63,0]+[255,7]*4+[255,1]*4+[255,15]*3+[255,1]*9)
class MultiAxisTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
  with tempfile.TemporaryDirectory() as d:cls.code,cls.manifest=build(d)
 def em(self):
  b=bytearray(self.rom);off=self.manifest['base']-BASE;b.extend(bytes(max(0,off+len(self.code)-len(b))));b[off:off+len(self.code)]=self.code
  return StockISP(bytes(b))
 def test_owned_writer_matches_original_for_full_banks(self):
  rng=random.Random(478)
  for trial in range(4):
   e=self.em();t=e.alloc(len(MASKS));frame=e.alloc(0x9000);ref=e.alloc(0x9000);obj=e.alloc(24)
   raw=bytes(rng.getrandbits(8)&m for m in MASKS);seed=rng.randbytes(0x9000)
   e.u.mem_write(t,raw);e.u.mem_write(frame,seed);e.u.mem_write(ref,seed)
   for i,o in enumerate((0,32,52,2212,3652,3694)):e.w32(obj+i*4,t+o)
   e.call(0x536df55c,obj,ref+0x120)
   e.call(self.manifest['symbols']['m10v_isp_multiaxis_apply'],frame,0x9000,t)
   self.assertEqual(bytes(e.u.mem_read(frame,0x9000)),bytes(e.u.mem_read(ref,0x9000)))
   self.assertEqual(bytes(e.u.mem_read(t,len(raw))),raw)
 def test_invalid_bits_and_overlap_leave_frame_unchanged(self):
  e=self.em();t=e.alloc(len(MASKS));f=e.alloc(0x9000);seed=bytes([0xa5])*0x9000;e.u.mem_write(f,seed)
  for offset,value in ((1,16),(32,16),(54,1),(2214,1),(3652,64),(3695,2)):
   e.u.mem_write(t,bytes(len(MASKS)));e.u.mem_write(t+offset,bytes([value]));e.call(self.manifest['symbols']['m10v_isp_multiaxis_apply'],f,0x9000,t)
   self.assertEqual(bytes(e.u.mem_read(f,0x9000)),seed)
  e.call(self.manifest['symbols']['m10v_isp_multiaxis_apply'],f,0x9000,f)
  self.assertEqual(bytes(e.u.mem_read(f,0x9000)),seed)

 def test_builder_rejects_foreign_firmware(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'RTOS hash'):build(d,rom=b'foreign')

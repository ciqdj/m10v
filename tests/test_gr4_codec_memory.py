"""Large firmware checksum must not allocate another whole-image word array."""
import struct
import sys
import tracemalloc
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'vendor/gr4'))
from gr4_editor.codec.container import sum32,repair_last_word

class Gr4CodecMemoryTests(unittest.TestCase):
 def test_checksum_has_bounded_workspace_and_preserves_unsigned_sum(self):
  data=struct.pack('<4I',0xffffffff,2,0x80000000,7)*(512*1024)
  tracemalloc.start()
  try:
   self.assertEqual(sum32(data),((0xffffffff+2+0x80000000+7)*(512*1024))&0xffffffff)
   self.assertLess(tracemalloc.get_traced_memory()[1],256*1024)
  finally:tracemalloc.stop()
 def test_repair_preserves_prefix_and_rejects_unaligned_input(self):
  original=struct.pack('<4I',0xffffffff,2,0x80000000,7)
  repaired=repair_last_word(original)
  self.assertEqual(repaired[:-4],original[:-4]);self.assertEqual(sum32(repaired),0)
  with self.assertRaises(ValueError):sum32(b'123')

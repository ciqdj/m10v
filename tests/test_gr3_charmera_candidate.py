"""Final BIN execution, not hardware/LCD/ISP pixel emulation."""
import json,os,struct,subprocess,unittest,zlib
from pathlib import Path
from tests.test_gr3_isp_base import StockISP
from tests.test_gr3_isp_recipe_color import state

@unittest.skipUnless(os.environ.get('M10V_CHARMERA_CANDIDATE'),'Charmera final artifact required')
class CharmeraCandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=Path(os.environ['M10V_CHARMERA_CANDIDATE']).resolve()
  cls.manifest=json.loads((cls.folder/'evidence/manifest.json').read_text())
  script="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
  cls.rom=subprocess.check_output(['node','--input-type=module','-e',script,str(cls.folder/'fw/fwdc239b.bin')])
  cls.entry=cls.manifest['capture_lifecycle']['snapshot']['patches'][3]['entry']
 def test_final_appended_live_callback_consumes_all_four_colors_in_each_of_five_slots(self):
  for slot,tone in enumerate((25,26,27,28,29)):
   e=StockISP(self.rom);e.w32(0x55063910,1);e.w32(0x55063988,0x550d0000)
   e.w32(0x550d193c,0x3856504d);e.w32(0x550d1940,2)
   data=bytearray(state((289,)*5));e.u.mem_write(0x550d1944,bytes(data))
   e.make(tone,1,True,actual_live=True);frame=0x60001400;obj=0x60000000
   si=struct.unpack('<I',e.u.mem_read(frame+0x82d0,4))[0];shooting=bytes(e.u.mem_read(si,0x80000));outputs=[]
   for color in range(4):
    data[63+slot*8]=color;struct.pack_into('<I',data,100,zlib.crc32(data[:100]));e.u.mem_write(0x550d1944,bytes(data))
    e.call(self.entry,obj,frame);outputs.append(bytes(e.u.mem_read(frame,0x9000)))
    e.call(self.entry,obj,frame);self.assertEqual(bytes(e.u.mem_read(frame,0x9000)),outputs[-1])
    self.assertEqual(bytes(e.u.mem_read(si,0x80000)),shooting)
   self.assertEqual(len(set(outputs)),4,slot)
   self.assertFalse(e.assertions)

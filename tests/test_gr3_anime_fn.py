import json,os,struct,subprocess,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class AnimeFnTests(unittest.TestCase):
 def test_short_enum_has_pinned_glyphs_within_original_value_rail(self):
  from scripts.generate_m10v_anime_ui import artwork,verify
  meta=verify();images=artwork()
  self.assertEqual(meta['caption'],'漫画进阶')
  self.assertEqual(meta['names'],['关闭','线稿','色块','手绘'])
  self.assertEqual([im.size for im in images],[(40,16)]*4+[(400,10)])
  for im in images[:4]:
   bbox=im.getbbox();self.assertIsNotNone(bbox)
   self.assertGreaterEqual(bbox[0],2);self.assertLessEqual(bbox[2],38)
  self.assertEqual((ROOT/'native/gr3/m10v_anime_ui.rgba').read_bytes(),b''.join(im.tobytes() for im in images))

class AnimeFnArmTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  folder=Path(os.environ.get('M10V_CURRENT_PIPELINE_CANDIDATE',ROOT/'builds/gr3-anime-e6-20261027/default'))
  if not (folder/'M10V-runtime-manifest.json').exists():raise unittest.SkipTest('requires exported candidate')
  cls.manifest=json.loads((folder/'M10V-runtime-manifest.json').read_text())
  js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
  cls.rom=subprocess.check_output(['node','--input-type=module','-e',js,str(folder/'fwdc239b.bin')],cwd=ROOT)
 def test_real_fn_table_short_caption_bitmap_states_bounds_and_atomic_callback(self):
  from tests.test_gr3_isp_base import StockISP
  from unicorn import UC_HOOK_CODE
  from unicorn import arm_const as A
  m=self.manifest
  self.assertEqual(m['resources']['texts'][1148-786],'漫画进阶')
  self.assertEqual(m['detail']['variant_ids']['anime'],[21,30])
  for film in (306,307,308):
   for mode in range(4):
    with self.subTest(film=film,mode=mode):
     e=StockISP(self.rom);ui=e.alloc(0x1a0);row=e.alloc(0x700);slider=e.alloc(0x100)
     e.u.mem_write(ui+0x198,bytes([25,0,0,0,0,0]));e.w32(ui+0x194,e.alloc(4));e.w32(ui+0x164,slider);e.w32(ui+0x160,e.alloc(0x100))
     e.w32(row+0xf0,row+0x200);e.w32(row+0xf4,row+0x400)
     state=bytearray.fromhex(m['initial_state_hex']);struct.pack_into('<H',state,12,film);state[103]=mode;struct.pack_into('<I',state,180,zlib.crc32(state[:180]))
     events=[];fail=[False]
     def service(u,at,n,_):
      args=[u.reg_read(getattr(A,'UC_ARM_REG_R'+str(i))) for i in range(4)];result=0
      if at==m['symbols']['m10v_camera_library_load']:u.mem_write(args[0],bytes(state))
      elif at==m['symbols']['m10v_camera_library_effects']:
       events.append(('save',args[1],args[2],args[3]));result=0xfffffffe if fail[0] else 0
      elif at==0x53394758:result=row
      elif at==0x5339e274:events.append(('row',args[1],args[2]))
      elif at==0x533ab548:events.append(('bounds',*struct.unpack('<4I',u.mem_read(args[1],16))))
      elif at==0x5339ee0c:events.append(('restore',args[1]))
      elif at==0x53396f80:events.append(('caption',args[1]))
      else:return
      u.reg_write(A.UC_ARM_REG_R0,result);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
     e.u.hook_add(UC_HOOK_CODE,service)
     control=m['symbols']['m10v_detail_control']
     e.call(control,1,ui,12);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),mode)
     e.call(control,3,ui,12<<16);self.assertIn(('row',858+film-306,864+mode),events)
     e.call(control,8,ui,30<<16);self.assertEqual([v for v in events if v[0]=='bounds'],[('bounds',50,10,40,40)]*2)
     before=bytes(state);fail[0]=True;e.call(control,2,ui,(12<<8)|((mode+1)%4))
     self.assertIn(('restore',mode),events);self.assertEqual(bytes(state),before)
     self.assertIn(('save',0,7,(mode+1)%4),events)

if __name__=='__main__':unittest.main()

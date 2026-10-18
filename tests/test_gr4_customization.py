"""GR IV native/custom recipes: real writer, independent resources, actual ARM getters."""
import base64,json,struct,subprocess,sys,unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from scripts.build_gr4_custom_firmware import (compile_custom,catalog,recipe_icon,validate_selection,FIELDS,DEFAULT_ENTRIES,ROOT,load_image,read_filters,canonical_base,_metadata)
class Gr4CustomizationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=load_image(ROOT/'bin/fwdc248b-gr4-officical.bin')
  def recipe(slot):return {'slotId':slot,'cameraName':'TEST '+slot[-1].upper(),'parameters':{key:i-4 for i,key in enumerate(FIELDS)},'iconMode':'original','source':'manual'}
  cls.selection={'variant':'street','features':['recipes','presets'],'recipes':[recipe(s) for s in ['builtin-0b','builtin-16','builtin-11','builtin-15','custom1','custom2']],'stockPresets':[{'slot':12,'name':'VIVID TEST','iconPixelsBase64':base64.b64encode(bytes([123,45,67,255])*1600).decode()}]}
  positive=cls.selection['recipes'][2];positive.update(iconMode='preset',source='community_reference',id='cookbook_kodamax')
  cls.selection['recipes'][4].update(iconMode='custom',customIcon={'schema':'grlife-camera-icon/v1','width':40,'height':40,'format':'rgba8','pixelsBase64':base64.b64encode(bytes([91,82,73,255])*1600).decode()})
  cls.rtos,cls.icons,cls.report=compile_custom(cls.source,deepcopy(cls.selection))
 def test_actual_twenty_native_capabilities_have_full_icons(self):
  caps=catalog(self.source);self.assertEqual(len(caps),20);self.assertEqual({x['slot'] for x in caps},set(range(11,31)))
  for x in caps:self.assertEqual(len(base64.b64decode(x['iconPixelsBase64'])),6400);self.assertTrue(x['canRename']);self.assertTrue(x['canIcon'])
 def test_six_recipes_and_independent_native_resource_readback(self):
  self.assertTrue(self.report['ready']);self.assertTrue(self.report['reset_required']);self.assertEqual(len(self.report['custom_styles']),2);self.assertEqual(canonical_base(self.rtos),self.source.rtos)
  rows=read_filters(SimpleNamespace(rtos=self.rtos,icon_bytes=self.icons,editable=True));by={r['identity']['style_id']:r for r in rows}
  self.assertEqual(by[11]['name'],'TEST B');self.assertEqual(by[25]['name'],'Standard')
  self.assertEqual(bytes.fromhex(by[17]['resources']['icon']['hex']),recipe_icon(self.selection['recipes'][2]));custom=next(r for r in rows if r['id']=='m10v-custom1');self.assertEqual(bytes.fromhex(custom['resources']['icon']['hex']),bytes([91,82,73,255])*1600)
  self.assertEqual(by[12]['name'],'VIVID TEST');self.assertEqual(bytes.fromhex(by[12]['resources']['icon']['hex']),bytes([123,45,67,255])*1600)
 def test_all_four_builtin_recipe_defaults_execute_in_unicorn(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x2000000);u.mem_write(0x53000000,self.rtos);u.mem_map(0x55000000,0x100000)
  for style in [11,24,17,23]:
   for value,entry in enumerate(DEFAULT_ENTRIES):
    u.reg_write(UC_ARM_REG_R0,0x55001000);u.reg_write(UC_ARM_REG_R1,style);u.reg_write(UC_ARM_REG_SP,0x550ff000);u.reg_write(UC_ARM_REG_LR,0x550fff00)
    u.emu_start(entry,0x550fff00,count=1000);self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x550fff00);self.assertEqual(u.reg_read(UC_ARM_REG_R0),value)
 def test_all_recipe_icon_modes_use_real_pixels(self):
  self.assertIsNone(recipe_icon({'iconMode':'original'}))
  raw=bytes([10,20,30,255])*1600;icon={'schema':'grlife-camera-icon/v1','width':40,'height':40,'format':'rgba8','pixelsBase64':base64.b64encode(raw).decode()}
  self.assertEqual(recipe_icon({'iconMode':'custom','customIcon':icon}),raw)
  community={'slotId':'builtin-11','iconMode':'preset','source':'community_reference','id':'cookbook_kodamax'}
  pixels=recipe_icon(community);self.assertEqual(len(pixels),6400);self.assertTrue(any(pixels));self.assertNotEqual(pixels,raw)
  with self.assertRaises(ValueError):recipe_icon({**community,'slotId':'builtin-16'})
 def test_validation_rejects_bad_ranges_aliasing_and_recipe_preset_collision(self):
  for mutate in [lambda x:x['recipes'][0]['parameters'].update(saturation=5),lambda x:x['stockPresets'].append({'slot':11,'name':'collision'}),lambda x:x.update(features=['film'])]:
   selection=deepcopy(self.selection);mutate(selection)
   with self.assertRaises(ValueError):validate_selection(selection)
 def test_cli_will_not_overwrite_input_or_config(self):
  source=ROOT/'bin/fwdc248b-gr4-officical.bin';before=source.stat().st_size
  p=subprocess.run([sys.executable,str(ROOT/'scripts/build_gr4_custom_firmware.py'),'--input',str(source),'--report',str(source),'--catalog'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('paths must be distinct',p.stderr);self.assertEqual(source.stat().st_size,before)

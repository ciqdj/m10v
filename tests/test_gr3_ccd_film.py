"""CCD native defaults, artifact-free fast path and colour-fit quality bounds."""
import ctypes as C
import json
import unittest
import subprocess
import numpy as np
import colour
from scripts.build_gr3_curated_reference import render
from tests import test_gr3_m10v_library as host

class CcdFilmTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  host.NativeFilmLibraryTests.setUpClass()
  cls.addClassCleanup(host.NativeFilmLibraryTests.doClassCleanups)
  cls.lib=host.NativeFilmLibraryTests.lib
 def test_ccd_defaults_and_both_resets_preserve_clean_digital_texture(self):
  lib=self.lib;s=host.State();lib.m10v_library_init(C.byref(s));ok=host.STORE(lambda _,v:0)
  self.assertEqual(lib.m10v_library_select(C.byref(s),0,72,ok,None),0)
  expected=bytes(s.slots[0]);effects=bytes(s.effects[0])
  self.assertEqual([s.slots[0].grain,s.slots[0].soft,s.slots[0].halo_gain],[0,0,0])
  self.assertEqual(effects,bytes([0,0,0,4,0,0,0,0]))
  lib.m10v_library_reset.argtypes=[C.POINTER(host.State),C.c_uint32,host.STORE,C.c_void_p]
  lib.m10v_library_effects.argtypes=[C.POINTER(host.State),C.c_uint32,C.c_uint32,C.c_uint32,host.STORE,C.c_void_p]
  for reset in (False,True):
   self.assertEqual(lib.m10v_library_texture(C.byref(s),0,3,0,ok,None),0)
   if reset:self.assertEqual(lib.m10v_library_reset(C.byref(s),0,ok,None),0)
   else:self.assertEqual(lib.m10v_library_effects(C.byref(s),0,5,0,ok,None),0)
   self.assertEqual(bytes(s.slots[0]),expected);self.assertEqual(bytes(s.effects[0]),effects)
 def test_native_color_completed_leaves_padded_pixels_and_buffers_untouched_without_scratch(self):
  lib=self.lib;s=host.State();lib.m10v_library_init(C.byref(s));ok=host.STORE(lambda _,v:0)
  self.assertEqual(lib.m10v_library_select(C.byref(s),0,72,ok,None),0)
  y=(C.c_uint8*96)(*range(96));uv=(C.c_uint8*96)(*reversed(range(96)))
  image=host.Image(y,uv,96,96,10,8,12);before=(bytes(y),bytes(uv))
  lib.m10v_library_render_native.argtypes=[C.POINTER(host.Image),C.POINTER(host.State),C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32]
  self.assertEqual(lib.m10v_library_render_native(C.byref(image),C.byref(s),0,None,42,None,0,1),0)
  self.assertEqual((bytes(y),bytes(uv)),before)
 def test_ccd_interpolation_and_isp_holdout_stay_below_visible_fit_budget(self):
  ref=json.loads((host.ROOT/'native/gr3/curated-reference.json').read_text())
  stock=next(s for s in ref['stocks'] if s['id']==72)
  self.assertLess(stock['interpolation']['delta_e00_p95'],.5)
  score=next(q['holdout'] for q in ref['native_profiles_full'] if q['film_id']==72)
  self.assertLessEqual(score['de00_median'],1.);self.assertLessEqual(score['de00_p95'],2.)

class CcdPaletteTests(unittest.TestCase):
 def test_cyan_rotates_blueward_and_red_rotates_orange_while_skin_is_restrained(self):
  # A saturation-only implementation cannot rotate these independent hue anchors.
  lab=colour.Oklch_to_Oklab(np.array([[.65,.12,195],[.60,.15,25],[.70,.10,55]]))
  rgb=colour.XYZ_to_sRGB(colour.Oklab_to_XYZ(lab))
  out=colour.Oklab_to_Oklch(colour.XYZ_to_Oklab(colour.sRGB_to_XYZ(render(72,rgb))))
  self.assertGreater(out[0,2]-195,4)
  self.assertGreater(out[1,2]-25,2)
  self.assertLess(out[2,1]/.10,1.06)
 def test_neutral_ramp_and_extreme_colours_remain_bounded_and_smooth(self):
  ramp=np.repeat(np.linspace(0,1,4097)[:,None],3,axis=1)
  result=render(72,ramp)
  self.assertLess(np.max(np.ptp(result,axis=1)),1e-9)
  self.assertTrue(np.all(np.diff(result[:,0])>=0))
  np.testing.assert_allclose(result[[0,-1]],[[0,0,0],[1,1,1]],atol=1e-9)
  rgb=np.random.default_rng(72).uniform(0,1,(4096,3));out=render(72,rgb)
  self.assertTrue(np.isfinite(out).all());self.assertGreaterEqual(out.min(),0);self.assertLessEqual(out.max(),1)
  nearby=render(72,np.clip(rgb+1e-5,0,1))
  self.assertLess(np.max(np.abs(nearby-out)),.002)

 def test_browser_ccd_lut_preserves_source_alpha_and_source_buffer(self):
  script="""
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {previewCuratedPixels} from './web/gr3/film-preview.mjs';
const lut=JSON.parse(fs.readFileSync('./web/gr3/curated-luts.json','utf8'));
const source=new Uint8ClampedArray([42,130,170,0,170,70,50,19,170,135,110,255]);
const before=source.slice(),out=previewCuratedPixels(source,lut,72);
assert.deepEqual(Array.from(out).filter((_,i)=>i%4===3),[0,19,255]);
assert.deepEqual(source,before);
assert.notDeepEqual(out,source);
"""
  subprocess.run(['node','--input-type=module','-e',script],cwd=host.ROOT,check=True,capture_output=True)

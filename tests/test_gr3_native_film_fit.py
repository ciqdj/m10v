import unittest
import numpy as np
from scripts.fit_gr3_native_film_targets import groups,identity_parameters,render,pack_multiaxis,fit_gate
class NativeFitTests(unittest.TestCase):
 def test_identity_roundtrip_in_native_gamma_domain(self):
  base=np.linspace(0,1,256)**.45;x=np.random.default_rng(3).random((128,3))
  self.assertLess(np.max(np.abs(render(identity_parameters(),x,base)-x)),2e-14)
 def test_active_geometry_has_twelve_regions(self):
  ycc=np.column_stack([np.full(360,.5),.1*np.cos(np.radians(np.arange(360))),.1*np.sin(np.radians(np.arange(360)))])
  conversion=np.array([[77,150,29],[-43,-85,128],[128,-107,-21]])/256
  self.assertEqual(set(groups(ycc@np.linalg.inv(conversion).T)),set(range(12)))
 def test_packed_full_levels_repeat_without_coefficient_loss(self):
  q=np.tile(np.eye(3,dtype=int)*1024,(12,1,1));q[2,0]=[1028,-4,0]
  b=pack_multiaxis(q);self.assertEqual(len(b),3712)
  import struct
  m=np.array(struct.unpack_from('<540I',b,52)).reshape(12,5,3,3)
  self.assertTrue(np.all(m==np.repeat((q&4095)[:,None],5,axis=1)))
 def test_gate_refuses_poor_fit_or_unvalidated_pixel_model(self):
  self.assertFalse(fit_gate({'de00_p95':5.74,'de00_max':9,'de00_median':1},True)['eligible'])
  self.assertFalse(fit_gate({'de00_p95':.2,'de00_max':1,'de00_median':.1},False)['eligible'])
 def test_joint_fit_reduces_error_for_actual_nonlinear_native_chain(self):
  from scripts.fit_gr3_native_film_targets import fit
  x=np.random.default_rng(9).random((192,3));base=np.linspace(0,1,256)**.45;p=identity_parameters();p[0]=.96;p[1]=.04;p[18:51]=np.linspace(0,1,33)**1.1
  wanted=render(p,x,base);before=np.mean((wanted-x)**2);fitted,_=fit(x,wanted,base,120)
  self.assertLess(np.mean((render(fitted,x,base)-wanted)**2),before*.03)
 def test_quantization_models_actual_native_matrix_composition(self):
  from scripts.fit_gr3_native_film_targets import quantize,STD_CCA,STD_CSP
  p=identity_parameters();p[0]=.94;p[1]=.06;p[10]=.97;p[11]=.03;q=quantize(p)
  self.assertTrue(np.array_equal(q['native_cca_signed12'],(np.array(q['matrix_q13'])@STD_CCA+4096)//8192))
  self.assertTrue(np.array_equal(q['native_csp_signed9'],(STD_CSP.astype(int)@np.array(q['post_q9'])+256)//512))

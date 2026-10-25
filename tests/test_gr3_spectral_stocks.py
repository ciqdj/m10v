"""Acceptance against the complete, same-stock community spectral pipeline."""
import unittest
import numpy as np
from scripts.build_gr3_newstocks_reference import render

class SpectralStocksTests(unittest.TestCase):
 def test_2460_uses_full_negative_and_paper_pipeline_instead_of_curve_blend(self):
  # Same-stock spectral model with corrected official AS-2652 RGB curves,
  # Portra Endura, sRGB D65, zero exposure, no masking or white clipping.
  x=np.array([[0.,0.,0.],[.18,.18,.18],[.5,.5,.5],[1.,1.,1.],[.8,.2,.1]])
  expected=np.array([[.08164930,.04873436,.06374502],[.11499239,.08090947,.07343847],[.51267785,.53160745,.53668815],[.86375201,.88132018,.87855440],[.65239471,.17302793,.09757983]])
  np.testing.assert_allclose(render(77,x),expected,atol=2e-6,rtol=0)

if __name__=='__main__':unittest.main()

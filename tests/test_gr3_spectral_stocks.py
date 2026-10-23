"""Acceptance against the complete, same-stock community spectral pipeline."""
import unittest
import numpy as np
from scripts.build_gr3_newstocks_reference import render

class SpectralStocksTests(unittest.TestCase):
 def test_2460_uses_full_negative_and_paper_pipeline_instead_of_curve_blend(self):
  # Independently evaluated with Jan Lohse's full Kodak Aerocolor IV model,
  # Portra Endura, sRGB D65, zero exposure, no masking or white clipping.
  x=np.array([[0.,0.,0.],[.18,.18,.18],[.5,.5,.5],[1.,1.,1.],[.8,.2,.1]])
  expected=np.array([[.08334333,.05110290,.06499022],[.11532976,.08245831,.07725782],[.51814260,.52769095,.53107650],[.86275400,.88336885,.88789300],[.65376360,.17637855,.12429541]])
  np.testing.assert_allclose(render(77,x),expected,atol=2e-6,rtol=0)

if __name__=='__main__':unittest.main()

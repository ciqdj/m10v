"""Independent anchors read from Kodak AS-2652, page6, medium contrast."""
import unittest,numpy as np
from unittest.mock import patch
from scripts.build_gr3_spectral_reference import models
class OfficialAerocolorTests(unittest.TestCase):
 def test_blue_layer_is_not_a_copy_of_green_and_matches_official_chart(self):
  # Capture the raw FilmData supplied to the real spectral constructor; its
  # processed density curves later use a different layer-activation basis.
  with patch('spectral_film_lut.film_spectral.FilmSpectral',side_effect=lambda data:data):
   n,_=models.__wrapped__(77)
  # Official PDF endpoint at logH about0.86: R2.175, G2.440, B2.580.
  v=np.array([np.interp(.86,*np.array(sorted(c.items())).T) for c in n.sensiometric_curve])
  np.testing.assert_allclose(v,[2.175,2.440,2.580],atol=.02)
 def test_medium_contrast_exposure_reference_is_explicit_not_maximum_contrast(self):
  n,_=models(77);self.assertEqual(n.iso,100)
if __name__=='__main__':unittest.main()

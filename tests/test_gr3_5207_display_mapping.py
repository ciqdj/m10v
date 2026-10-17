"""Independent display-domain quality limits, separate from model interpolation.

Limits describe a restrained everyday look; they do not establish measured
Kodak 5207 reproduction or GR3 sensor/ISP calibration.
"""
import unittest
import tempfile
import json
from pathlib import Path
import numpy as np
from scripts.build_gr3_5207_reference import Reference5207, sample_tetrahedral, generate
import colour


class Display5207QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=Reference5207()
        axis=np.linspace(0,1,15)
        grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1).reshape(-1,3)
        cls.table=np.rint(cls.model.render(grid)*255).reshape(15,15,15,3)/255

    def outputs(self,rgb):
        return (self.model.render(rgb),sample_tetrahedral(self.table,np.asarray(rgb)))

    def test_neutral_ramp_retains_exposure_and_stays_neutral(self):
        x=np.linspace(0,1,257);gray=np.repeat(x[:,None],3,axis=1)
        for output in self.outputs(gray):
            self.assertLessEqual(float(np.ptp(output,axis=1).max()),1/255)
            self.assertLessEqual(float(np.abs(output-gray).max()),.03)
            self.assertTrue((np.diff(output,axis=0)>=-1e-7).all())
            self.assertLessEqual(float(output[0].max()),1/255)

    def test_highlight_steps_retain_detail_with_soft_positive_slope(self):
        gray=np.repeat(np.array([.85,.9,.95,1.])[:,None],3,axis=1)
        for output in self.outputs(gray):
            steps=np.diff(output[:,0])
            self.assertGreater(float(steps.min()),.03)
            self.assertLess(float(steps.max()),.055)
            self.assertGreater(float(output[-1,0]),.96)

    def test_increasing_own_channel_does_not_reverse_its_output(self):
        rgb=np.random.default_rng(987).uniform(.02,.98,(8192,3))
        for channel in range(3):
            increased=rgb.copy();increased[:,channel]+=.01
            for before,after in zip(self.outputs(rgb),self.outputs(increased)):
                self.assertGreaterEqual(float((after[:,channel]-before[:,channel]).min()),-1/255)

    def test_blue_and_cyan_sky_keep_hue_and_chroma(self):
        rgb=np.array([[.15,.5,.9],[.36,.48,.63],[0,1,1],[0,0,1]])
        for output in self.outputs(rgb):
            self.assertTrue((output[:,2]>output[:,0]+.12).all())
            self.assertLess(float(output[2,0]),.10)
            self.assertTrue(((output.max(1)-output.min(1))>.20).all())
            self.assertLess(float(np.max(np.abs(output-rgb))),.06)

    def test_skin_hue_shift_is_small_without_magenta_bias(self):
        rgb=np.array([[.76,.57,.49],[.45,.32,.26],[.65,.43,.35],[.9,.72,.63]])
        before=colour.XYZ_to_Lab(colour.sRGB_to_XYZ(rgb));hue0=np.arctan2(before[:,2],before[:,1])
        for output in self.outputs(rgb):
            lab=colour.XYZ_to_Lab(colour.sRGB_to_XYZ(output));hue=np.arctan2(lab[:,2],lab[:,1])
            distance=np.abs(np.arctan2(np.sin(hue-hue0),np.cos(hue-hue0)))
            self.assertLess(float(np.rad2deg(distance).max()),8)
            chroma_ratio=np.linalg.norm(lab[:,1:],axis=1)/np.linalg.norm(before[:,1:],axis=1)
            self.assertTrue(((chroma_ratio>=.85)&(chroma_ratio<=1.15)).all())
            self.assertTrue((output[:,0]>output[:,1]).all())
            self.assertTrue((output[:,1]>output[:,2]).all())

    def test_generation_declares_display_domain_and_uncalibrated_assumptions(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest=generate(Path(directory))
            self.assertEqual(manifest['schema'],'m10v-5207-reference/v2')
            self.assertEqual(manifest['model'],'bounded-display-srgb-v1')
            for key in ('camera_calibrated','film_calibrated','spectral_calibrated','official_lut','scene_radiance_recovered'):
                self.assertIs(manifest[key],False)
            self.assertIsNone(manifest['inversion_gamma'])
            self.assertIn('assumed',manifest['parameters']['status'])
            self.assertIn('encoded display sRGB',manifest['input'])
            self.assertIn('encoded display sRGB',manifest['output'])
            saved=json.loads((Path(directory)/'native/gr3/5207-reference.json').read_text())
            self.assertEqual(saved,manifest)
            self.assertEqual(manifest['table_bytes'],10125)

    def test_invalid_rgb_is_rejected_and_outside_domain_is_bounded(self):
        for rgb in ([[np.nan,0,0]],[[0,np.inf,0]],[.1,.2]):
            with self.assertRaises(ValueError):self.model.render(rgb)
        result=self.model.render([[-1,.5,2],[1,1,1]])
        self.assertTrue(np.isfinite(result).all())
        self.assertTrue(((result>=0)&(result<=1)).all())


if __name__=='__main__':unittest.main()

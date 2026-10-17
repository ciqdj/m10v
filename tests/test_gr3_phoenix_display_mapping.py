"""Independent restrained Phoenix display-quality limits and frozen RED tables."""
import hashlib
import unittest
import numpy as np
from scripts.build_gr3_harman_reference import ReferenceHarman, sample_tetrahedral
import colour

RED_SHA256={125:'9f1202227870d22c721ae007968291470cfef0c7c8fba50764f4b0c88f62b817',64:'8857832e8b8ad2469c4a60aa7c01346ad66c0e8c46856320d189848fab65d9fd',250:'3c1c7d7257148205a727ee662744d6709685a9145279f2002d0c485209607c1c'}


class PhoenixDisplayMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=ReferenceHarman('phoenix-ii')
        axis=np.linspace(0,1,15)
        cls.grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1).reshape(-1,3)
        cls.table=np.rint(cls.model.render(cls.grid)*255).reshape(15,15,15,3)/255

    def outputs(self,rgb):
        rgb=np.asarray(rgb)
        return self.model.render(rgb),sample_tetrahedral(self.table,rgb)

    @staticmethod
    def lab(rgb):return colour.XYZ_to_Lab(colour.sRGB_to_XYZ(rgb))

    def test_neutrals_keep_exposure_and_remain_neutral(self):
        x=np.linspace(0,1,257);rgb=np.repeat(x[:,None],3,axis=1)
        for out in self.outputs(rgb):
            self.assertLess(float(np.max(np.abs(out-rgb))),.025)
            self.assertLessEqual(float(np.ptp(out,axis=1).max()),1/255)
            self.assertTrue((np.diff(out,axis=0)>=0).all())

    def test_soft_highlights_keep_all_steps_without_early_clip(self):
        rgb=np.repeat(np.array([.85,.9,.95,1.])[:,None],3,axis=1)
        for out in self.outputs(rgb):
            self.assertGreater(float(np.diff(out[:,0]).min()),.035)
            self.assertLess(float(np.diff(out[:,0]).max()),.055)
            self.assertGreater(float(out[-1,0]),.97)

    def test_natural_blue_cyan_gain_modest_selective_chroma(self):
        rgb=np.array([[.2,.45,.75],[.3,.65,.7],[.15,.5,.8],[.28,.55,.64]])
        base=self.lab(rgb);h0=np.arctan2(base[:,2],base[:,1]);c0=np.linalg.norm(base[:,1:],axis=1)
        for out in self.outputs(rgb):
            lab=self.lab(out);h=np.arctan2(lab[:,2],lab[:,1]);c=np.linalg.norm(lab[:,1:],axis=1)
            self.assertTrue(((c/c0>1.01)&(c/c0<1.15)).all(),c/c0)
            shift=np.abs(np.rad2deg(np.arctan2(np.sin(h-h0),np.cos(h-h0))))
            self.assertLess(float(shift.max()),6)
            self.assertTrue((out[:,2]>out[:,0]).all())

    def test_skin_stays_warm_without_a_global_blue_cast(self):
        rgb=np.array([[.76,.57,.49],[.45,.32,.26],[.65,.43,.35],[.9,.72,.63]])
        before=self.lab(rgb);h0=np.arctan2(before[:,2],before[:,1])
        for out in self.outputs(rgb):
            after=self.lab(out);h=np.arctan2(after[:,2],after[:,1]);shift=np.abs(np.rad2deg(np.arctan2(np.sin(h-h0),np.cos(h-h0))))
            self.assertLess(float(shift.max()),6)
            self.assertLess(float(np.max(np.abs(out-rgb))),.035)
            self.assertTrue((out[:,0]>out[:,1]).all())
            self.assertTrue((out[:,1]>out[:,2]).all())

    def test_own_channel_response_is_monotone(self):
        rgb=np.random.default_rng(6702).uniform(.01,.98,(8192,3))
        for channel in range(3):
            changed=rgb.copy();changed[:,channel]+=.01
            for a,b in zip(self.outputs(rgb),self.outputs(changed)):
                self.assertGreaterEqual(float((b[:,channel]-a[:,channel]).min()),-1/255)

    def test_all_three_red_payloads_remain_byte_identical(self):
        for ei,digest in RED_SHA256.items():
            values=np.rint(ReferenceHarman('red',ei).render(self.grid)*255).astype(np.uint8)
            self.assertEqual(hashlib.sha256(values.tobytes()).hexdigest(),digest)


if __name__=='__main__':unittest.main()

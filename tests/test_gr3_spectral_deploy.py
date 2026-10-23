"""Server verification is stdlib-only; fitting dependencies are offline tools."""
import subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SpectralDeployTests(unittest.TestCase):
 def test_spectral_verification_does_not_import_scientific_fitting_stack(self):
  script='''import sys,importlib.abc
class NoFit(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'numpy','scipy','colour','torch','numba'}:raise AssertionError('server verifier imported '+fullname)
sys.meta_path.insert(0,NoFit())
from scripts.verify_gr3_spectral_reference import verify
assert len(verify('.'))==2
'''
  p=subprocess.run(['.venv/bin/python','-c',script],cwd=ROOT,capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()

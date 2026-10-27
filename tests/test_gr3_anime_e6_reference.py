"""Contracts for offline references and default native ISP profiles."""
import copy
import json
import tempfile
import shutil
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def flatten(rows):
 for row in rows:yield from row

class AnimeE6ReferenceTests(unittest.TestCase):
 def test_reference_contract(self):
  from scripts.verify_gr3_anime_e6_reference import verify
  self.assertEqual(len(verify(ROOT)),6)
 def test_ids_and_claims(self):
  ref=json.loads((ROOT/'native/gr3/anime-e6-reference.json').read_text())
  self.assertEqual([s['id'] for s in ref['stocks']],list(range(306,312)))
  self.assertFalse(ref['camera_validated'])
  self.assertEqual(ref['default_camera_renderer'],'quantized native ISP; no CPU color LUT')
  self.assertEqual(ref['stocks'][3]['source_kind'],'exact-name community LUT')
  self.assertNotEqual(ref['stocks'][4]['model_parameters'],ref['stocks'][5]['model_parameters'])
 def test_finite_distinct_profiles(self):
  from scripts.verify_gr3_anime_e6_reference import verify_profile
  ref=json.loads((ROOT/'native/gr3/anime-e6-reference.json').read_text())
  for q in ref['native_profiles_full']: verify_profile(q)
  self.assertEqual(len({json.dumps(q['curves']) for q in ref['native_profiles_full']}),6)
 def test_reject_overflow_and_false_claim(self):
  from scripts.verify_gr3_anime_e6_reference import verify_profile
  q=copy.deepcopy(json.loads((ROOT/'native/gr3/anime-e6-reference.json').read_text())['native_profiles_full'][0])
  q['hue_q10'][0][0][0]=2048
  with self.assertRaises(ValueError):verify_profile(q)
 def test_reject_mutated_artifacts(self):
  from scripts.verify_gr3_anime_e6_reference import verify
  ref=json.loads((ROOT/'native/gr3/anime-e6-reference.json').read_text())
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   paths=set(ref['files'])|{'native/gr3/anime-e6-reference.json','native/gr3/m10v_anime_e6_native_profiles.h'}
   for path in paths:
    target=root/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/path,target)
   path=root/'web/gr3/anime-e6-luts.json';original=path.read_text();data=json.loads(original)
   data['stocks'][0]['native_values'][0]^=1;path.write_text(json.dumps(data))
   with self.assertRaises(ValueError):verify(root)
   path.write_text(original)
   path=root/'native/gr3/anime-e6-reference.json';data=json.loads(path.read_text());data['camera_validated']=True;path.write_text(json.dumps(data))
   with self.assertRaises(ValueError):verify(root)
 def test_lossless_packed_curve_roundtrip(self):
  from scripts.fit_gr3_anime_e6_native import packed_frames
  from scripts.build_gr3_isp_native_look import decode_curve_deltas
  ref=json.loads((ROOT/'native/gr3/anime-e6-reference.json').read_text())
  frames,stream=packed_frames(ref)
  self.assertLess(len(stream)+len(frames)*48,6*1572)
  for frame,q in zip(frames,ref['native_profiles_full']):
   self.assertEqual(frame['matrix'],list(flatten(q['matrix_q13'])))
   self.assertEqual(frame['post'],list(flatten(q['post_q9'])))
   for i,original in enumerate(q['curves']):
    curve=[frame['first'][i]]
    for delta in decode_curve_deltas(stream[frame['offset'][i]:]):curve.append(curve[-1]+delta)
    self.assertEqual(curve,original)
  ref['native_profiles_full'][0]['curves'][0][1]=ref['native_profiles_full'][0]['curves'][0][0]+256
  with self.assertRaises(ValueError):packed_frames(ref)
 def test_builder_is_reproducible(self):
  from scripts.build_gr3_anime_e6_reference import tables
  expected=json.loads((ROOT/'web/gr3/anime-e6-luts.json').read_text())
  self.assertEqual(tables(ROOT),[{k:v for k,v in stock.items() if k not in ('native_values','default_preview')} for stock in expected['stocks']])

if __name__=='__main__':unittest.main()

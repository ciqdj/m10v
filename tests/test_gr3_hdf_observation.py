"""Decode per-frame HDF evidence without confusing color or file completion."""
import unittest
from scripts.read_gr3_debug_log import lifecycle_profiles
class HdfObservationTests(unittest.TestCase):
 def test_hdf_success_and_rejection_flags_are_per_frame(self):
  records=[]
  for r,flags in [(0x5c001000,15),(0x5c002000,33),(0x5c003000,128)]:
   for event,args in [(198,[r,0x48444601,(flags<<8)|3,0x5c080000]),(193,[r,100,0,0]),(194,[r,110,0,0])]:
    records.append({'event':event,'arguments':args,'build_id':'hdf-test'})
  rows=lifecycle_profiles(records);self.assertEqual(len(rows),3)
  self.assertTrue(rows[0]['hdf']['processing_returned_success'])
  self.assertFalse(rows[1]['hdf']['processing_returned_success'])
  self.assertTrue(rows[1]['hdf']['si_rejected'])
  self.assertTrue(rows[2]['hdf']['load_failed'])
  self.assertTrue(all(r['file_save_proven'] is False for r in rows))

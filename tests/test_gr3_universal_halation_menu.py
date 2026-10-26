import unittest
from scripts.build_gr3_native_detail import build_detail
class UniversalHalationMenuTests(unittest.TestCase):
    def test_all_film_variants_get_explicit_mode_with_bounded_stock_slider(self):
        _,m=build_detail(0x54100000,{'m10v_detail_table':0x540b6000,'m10v_detail_control':0x540b6200},native_grain=True,sd_library=True,appended_slots=True,universal_halation=True)
        for ids in m['variant_ids'].values():
            for required in (18,19,20,22):self.assertIn(required,ids)
        self.assertIn('Halation Mode',m['fields']);self.assertEqual(m['halation_modes'],['off','spill','streak'])
        self.assertEqual(m['mode_caption'],1137)
if __name__=='__main__':unittest.main()

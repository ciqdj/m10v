"""Native stock caption tables must keep stable label pointers across UI updates."""
import unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2EffectNameTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build

    def test_all_original_language_tables_use_owned_film_names_and_restore_without_touching_other_labels(self):
        from scripts import analyze_gr2_native_contract as native
        runtime=self.build();self.assertIn('gr2_effect_names_refresh',runtime['symbols'])
        report=native.probe_effect_names(component('gr2','b01firm8'),native_runtime=runtime)
        self.assertEqual(report['languages'],21);self.assertEqual(report['aliases'],7)
        self.assertEqual(report['initial_names'],['Ektar 100','Gold 200','Gold 200','Pro 400H','Portra 400','800T','800T'])
        self.assertTrue(report['low_memory_rejected']);self.assertTrue(report['all_languages_match']);self.assertTrue(report['stable_pointers'])
        self.assertTrue(report['unrelated_labels_preserved']);self.assertTrue(report['foreign_change_rejected'])
        self.assertTrue(report['all_original_tables_restored']);self.assertTrue(report['pool_restored'])
        self.assertEqual(report['updated_first_name'],'800T')
        self.assertFalse(report['hardware_tested'])

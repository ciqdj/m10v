"""HDF graph preparation and immutable per-image curve ownership, without DMA."""
import unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2HdfGraphTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    def test_owned_graph_preparation_selects_eleven_bands_and_rejects_hdr_and_stale_snapshot(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        runtime=self.build();self.assertIn('gr2_hdf_graph_prepare',runtime['symbols'])
        result=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,workspace_owner=True,hdf_graph=True)
        graph=result['hdf_graph'];base=graph['data']
        self.assertEqual(graph['frozen'],1);self.assertEqual(graph['prepared'],1)
        self.assertEqual(graph['curves'],[base+0xe040+i*8192 for i in range(11)]+[base+0x6000])
        self.assertEqual(graph['stock'],0);self.assertEqual(graph['stock_pointer'],base+0x6000)
        self.assertEqual(graph['again'],1);self.assertEqual(graph['stale'],base+0x6000)
        self.assertEqual(graph['header_faults'],[base+0x6000]*7)
        self.assertEqual(graph['invalid_prepare'],0);self.assertEqual(graph['off_freeze'],1)
        self.assertEqual(graph['off_prepare'],0);self.assertEqual(graph['off_magic'],0)
        self.assertTrue(graph['request_preserved']);self.assertTrue(result['stack_preserved'])

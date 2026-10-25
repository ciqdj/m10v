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

    def test_native_hooks_run_original_full_graph_with_owned_band_curves_and_restore_user_strength(self):
        from scripts.analyze_gr2_native_contract import probe_clarity_control_graph
        runtime=self.build();self.assertIn('gr2_hdf_core',runtime['symbols'])
        for strength in (1,5,9):
            result=probe_clarity_control_graph(component('gr2','b01firm8'),strength,0xcc01340,native_runtime=runtime,hdf_strength=3)
            self.assertTrue(result['context_preserved']);self.assertTrue(result['resources_balanced'])
            self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])
            self.assertTrue(result['request_preserved']);self.assertTrue(result['arena_guards_preserved'])
            self.assertEqual([row['effective_pointer'] for row in result['band_curves']],
                             [0x2706fa00+0xe040+(level-1)*8192 for level in range(11,0,-1)])
            self.assertEqual(result['native_header_magic'],0)
            self.assertTrue(all(row['replay_abi_preserved'] for row in result['band_curves']))

    def test_default_off_and_hdr_keep_original_uploads_and_control_stages(self):
        from scripts.analyze_gr2_native_contract import probe_clarity_control_graph
        runtime=self.build();code=component('gr2','b01firm8')
        for strength,hdr in ((1,False),(5,False),(9,False),(3,True)):
            original=probe_clarity_control_graph(code,strength,0xcc01340,hdr=hdr)
            hooked=probe_clarity_control_graph(code,strength,0xcc01340,hdr=hdr,native_runtime=runtime,hdf_strength=3 if hdr else 0)
            self.assertEqual([(x['mode'],x['read_bytes'],x['source_sha256']) for x in hooked['curve_uploads']],
                             [(x['mode'],x['read_bytes'],x['source_sha256']) for x in original['curve_uploads']])
            for field in ('stages','resource_acquisitions','resource_releases','event_waits','mmio_write_count'):
                self.assertEqual(hooked[field],original[field])
            self.assertTrue(hooked['context_preserved']);self.assertTrue(hooked['hdf_curve_region_preserved'])
            self.assertTrue(all(row['replay_abi_preserved'] for row in hooked['band_curves']))
            self.assertEqual(hooked['native_header_magic'],0)

    def test_all_three_grades_reach_original_lut_driver_with_exact_gains_and_unchanged_postband_tables(self):
        from scripts.analyze_gr2_native_contract import probe_clarity_control_graph
        from scripts.build_gr3_digital_hdf import ROWS
        import hashlib,struct
        runtime=self.build();code=component('gr2','b01firm8')
        def node(i):
            i=min(i,255);return 8*i+4*i//255
        identity=[(node(i//8)*(8-i%8)+node(i//8+1)*(i%8))//8 for i in range(2048)]
        for strength,gains in enumerate(ROWS,1):
            result=probe_clarity_control_graph(code,5,0xcc01340,native_runtime=runtime,hdf_strength=strength)
            expected=[]
            for level in range(11,0,-1):
                curve=[0]*4096
                for i,value in enumerate(identity):
                    value=value*gains[level-1]//1024;curve[2048+i]=value
                    if i:curve[2048-i]=4096-value
                curve[0]=curve[1];expected.append(hashlib.sha256(struct.pack('>4096H',*curve)).hexdigest())
            self.assertEqual([entry['source_sha256'] for entry in result['curve_uploads'][:11]],expected)
            self.assertEqual([entry['source_sha256'] for entry in result['curve_uploads'][-2:]],
                             ['588eb9934761a8508729c1ab59c25a89fb74138ef8d4964482ac73e23bb8a529',
                              '85a821a3d487430c79a42f944b67db8b12a76a8a4f96c66c1c3c8f725bfb3444'])

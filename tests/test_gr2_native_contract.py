"""Native ABI evidence must execute original wrappers, with hardware boundaries explicit."""
import importlib.util
import unittest
from tests.test_unity_update import ROOT,component

class Gr2NativeContractTests(unittest.TestCase):
    def implementation(self):
        source=ROOT/'scripts/analyze_gr2_native_contract.py'
        self.assertTrue(source.exists(),'GR II native ABI analyzer is missing')
        spec=importlib.util.spec_from_file_location('gr2_native_contract',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def test_original_rtc_wrapper_expands_compact_driver_time_to_six_big_endian_halfwords(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for fields in ((2026,10,20,18,30,45),(2000,1,1,0,0,0),(2127,12,31,23,59,59)):
            with self.subTest(fields=fields):
                report=module.probe_rtc_get_time(code,fields)
                self.assertEqual(report['fields'],list(fields))
                self.assertEqual(report['output_hex'],''.join(f'{v:04x}' for v in fields))
                self.assertTrue(report['guards_unchanged'])
                self.assertTrue(report['callee_saved_preserved'])
                self.assertEqual(report['returned'],fields[-1])
                self.assertEqual(report['driver_calls'],1)

    def test_native_contract_rejects_unverified_or_other_model_code(self):
        module=self.implementation()
        with self.assertRaisesRegex(ValueError,'identity'):module.probe_rtc_get_time(bytes(4096),(2026,10,20,1,2,3))
        if (ROOT/'bin/rg1_v051.frm').exists():
            with self.assertRaisesRegex(ValueError,'identity'):module.probe_rtc_get_time(component('gr1','b01firm8'),(2026,10,20,1,2,3))

    def test_original_sd_io_wrappers_preserve_distinct_read_and_write_backend_contracts(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for operation in ('read','write'):
            with self.subTest(operation=operation):
                report=module.probe_sd_io(code,operation,b'M10V\x00config\xff')
                self.assertEqual(report['returned'],12)
                self.assertEqual(report['transferred_hex'],b'M10V\x00config\xff'.hex())
                self.assertTrue(report['guards_unchanged'])
                self.assertEqual(report['backend_items'],12 if operation=='read' else 1)
                self.assertEqual(report['backend_item_bytes'],1 if operation=='read' else 12)

    def test_original_sd_open_translates_bit_flags_to_backend_modes(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for flags,mode in ((0,'r'),(1,'w'),(9,'a'),(2,'r+'),(10,'a+'),(0x102,'w+')):
            with self.subTest(flags=flags):
                report=module.probe_sd_open_mode(code,flags)
                self.assertEqual(report['mode'],mode)
                self.assertEqual(report['path'],'H:/M10V.BIN')
                self.assertFalse(report['opened'])

    def test_read_wrapper_returns_short_count_at_eof_without_touching_tail(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_sd_io(component('gr2','b01firm8'),'read',b'12345678',read_count=3)
        self.assertEqual(report['returned'],3)
        self.assertEqual(report['buffer_hex'],b'123'.hex()+'a5'*5)
        self.assertTrue(report['guards_unchanged'])

    def test_original_region_init_reserves_system_pool_before_later_aligned_regions(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_memory_regions(component('gr2','b01firm8'),[1,17,1024])
        self.assertEqual(report['region_base'],0xa0900000)
        self.assertEqual(report['pool_bytes'],0x200000)
        self.assertEqual(report['pool_data'],0xa0900010)
        self.assertEqual(report['allocated'],[0xa0b00020,0xa0b00030,0xa0b00050])
        self.assertTrue(report['guards_unchanged'])
        self.assertEqual(report['pool_create_calls'],1)
        self.assertFalse(report['private_gap_proved'])

    def test_c_heap_boundaries_execute_original_arm_thumb_startup_without_interception(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for reserved_end in (None,0xa0800000):
            with self.subTest(reserved_end=reserved_end):
                report=module.probe_c_heap_startup(code,reserved_end=reserved_end)
                self.assertEqual(report['heap_base'],reserved_end or 0xa0798000)
                self.assertEqual(report['heap_limit'],0xa0900000)
                self.assertTrue(report['stack_preserved'])
                self.assertTrue(report['reserved_guard_preserved'])
                self.assertEqual(report['helpers_intercepted'],[])
                self.assertTrue(report['heap_initialized'])

    def test_original_jpeg_wrapper_and_encoder_config_use_planar_422_with_separate_pitches(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for width,height in ((4928,3264),(1280,848),(638,426)):
            with self.subTest(size=(width,height)):
                report=module.probe_jpeg_input(code,width,height)
                pitch=(width+15)&~15;chroma=((width//2)+15)&~15
                self.assertEqual(report['width'],width);self.assertEqual(report['height'],height)
                self.assertEqual(report['y_stride'],pitch);self.assertEqual(report['chroma_stride'],chroma)
                self.assertEqual(report['y'],0x60000000)
                self.assertEqual(report['u'],0x60000000+pitch*height)
                self.assertEqual(report['v'],0x60000000+(pitch+chroma)*height)
                self.assertEqual(report['jpeg'],0x64000000)
                self.assertEqual(report['subsampling'],1)
                self.assertEqual(report['input_format'],0x422)
                self.assertFalse(report['hardware_encoder_executed'])

    def test_jpeg_format_and_plane_overrides_come_from_original_descriptor_fields(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for kind,format_word,enum,chroma_bytes in ((2,0x422,1,320*480),(3,0x420,2,320*240),(4,0x444,0,640*480)):
            with self.subTest(kind=kind):
                report=module.probe_jpeg_input(code,640,480,format_kind=kind)
                self.assertEqual(report['input_format'],format_word)
                self.assertEqual(report['subsampling'],enum)
                self.assertEqual(report['v']-report['u'],chroma_bytes)
        report=module.probe_jpeg_input(code,640,480,overrides=(0x61000000,0x62000000,672,352))
        self.assertEqual((report['u'],report['v'],report['y_stride'],report['chroma_stride']),(0x61000000,0x62000000,672,352))

    def test_original_capture_owner_selects_distinct_image_kind_handles_and_dimensions(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for kind,offset,dimensions in ((1,0x1f4,(4928,3264)),(2,0x1fc,(1280,848)),(3,0x200,(160,120))):
            with self.subTest(kind=kind):
                report=module.probe_capture_owner(code,kind)
                self.assertEqual(report['source_handle_offset'],offset)
                self.assertEqual((report['width'],report['height']),dimensions)
                self.assertEqual(report['source'],report['source_handle_data'])
                self.assertGreaterEqual(report['source_handle_bytes'],report['minimum_planar_bytes'])
                self.assertEqual(report['output'],report['output_handle_data'])
                self.assertEqual(report['original_handle_getters'],2)

    def test_original_rtos_pool_allocates_releases_and_reports_exhaustion_without_asserting(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_rtos_pool(component('gr2','b01firm8'))
        self.assertEqual(report['pool_id'],1)
        self.assertEqual(report['allocate_returned'],0)
        self.assertEqual(report['free_returned'],0)
        self.assertEqual(report['exhausted_returned'],0xffffffce)
        self.assertEqual(report['reallocated_pointer'],report['allocated_pointer'])
        self.assertEqual(report['helpers_intercepted'],[])

    def test_official_named_raw_for_dng_field_is_the_capture_property_offset_1e4(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        present=module.probe_raw_for_dng(code,present=True)
        self.assertEqual(present['handle_offset'],0x1e4)
        self.assertFalse(present['asserted'])
        self.assertTrue(present['reached_continuation'])
        absent=module.probe_raw_for_dng(code,present=False)
        self.assertTrue(absent['asserted'])
        self.assertIn('hRawForDng',absent['assertion_text'])

    def test_original_memory_policy_programs_only_region_five_as_cacheable(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        for mode in (0,1,3,4):
            with self.subTest(mode=mode):
                report=module.probe_memory_policy(component('gr2','b01firm8'),boot_mode=mode)
                self.assertEqual(report['instruction_cache_mask'],0x20)
                self.assertEqual(report['data_cache_mask'],0x20)
                self.assertEqual(report['write_buffer_mask'],0)
                self.assertEqual(report['regions'][5],0xa0000039)
                self.assertEqual(report['control']&0x1005,0x1005)
                self.assertFalse(report['hardware_cache_emulated'])

    def test_original_file_lifecycle_closes_backend_and_invalidates_metadata_before_free(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_sd_file_lifecycle(component('gr2','b01firm8'))
        self.assertEqual(report['write_returned'],104)
        self.assertEqual(report['read_returned'],104)
        self.assertTrue(report['payload_matches'])
        self.assertEqual(report['backend_close_calls'],2)
        self.assertEqual(report['metadata_free_calls'],2)
        self.assertTrue(report['magic_cleared_before_free'])

    def test_original_effect_menu_roundtrips_every_display_choice_through_property_43(self):
        module=self.implementation()
        code=component('gr2','b01firm8')
        report=module.probe_effect_menu(code)
        self.assertEqual(report['item_id'],102)
        self.assertEqual(report['property_id'],43)
        self.assertEqual(len(report['choices']),18)
        self.assertEqual(sorted(row['display_index'] for row in report['choices']),list(range(18)))
        self.assertTrue(all(row['roundtrip'] for row in report['choices']))
        self.assertEqual(report['invalid_definition'],0)
        self.assertFalse(report['hardware_tested'])

    def test_capture_callers_keep_source_until_encoder_returns_then_release_it(self):
        module=self.implementation();code=component('gr2','b01firm8')
        for kind in (1,3):
            with self.subTest(kind=kind):
                report=module.probe_capture_owner(code,kind,complete=True)
                self.assertEqual(report['lifetime_events'],['encoder_enter','encoder_return','source_release'])
                self.assertTrue(report['source_cleared_after_encode'])
                self.assertTrue(report['stack_preserved'])

    def test_original_task_context_constructor_starts_tasks_in_user_mode(self):
        module=self.implementation();report=module.probe_task_context(component('gr2','b01firm8'))
        self.assertEqual(report['initial_task_cpsr'],0x10)
        self.assertEqual(report['scheduler_cpsr'],0xd2)
        self.assertTrue(report['guards_unchanged'])
        self.assertEqual(report['helpers_intercepted'],[])

    def test_original_localized_text_lookup_returns_big_endian_utf16_and_bounded_fallback(self):
        module=self.implementation();code=component('gr2','b01firm8')
        for language,expected in ((0,'白黒'),(1,'Black & White'),(4,'黑白'),(5,'黑白')):
            with self.subTest(language=language):
                report=module.probe_ui_text(code,106,language)
                self.assertEqual(report['text'],expected)
                self.assertEqual(report['wire_hex'],(expected+'\0').encode('utf-16-be').hex())
                self.assertEqual(report['helpers_intercepted'],[])
        self.assertEqual(module.probe_ui_text(code,0,1)['pointer'],module.probe_ui_text(code,0x350,1)['pointer'])
        with self.assertRaises(ValueError):module.probe_ui_text(code,106,21)

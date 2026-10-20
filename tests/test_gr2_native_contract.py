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

    def test_original_file_mode_parser_does_not_accept_assumed_exclusive_stdio_modes(self):
        module=self.implementation();self.assertTrue(hasattr(module,'probe_file_mode_flags'))
        result=module.probe_file_mode_flags(component('gr2','b01firm8'))
        self.assertEqual(result['flags'],{'r':2,'rb':2,'r+':10,'w':1,'wb':1,'w+':9,'a':4,'a+':12,'wx':0,'wbx':0,'x':0})
        self.assertEqual(result['helpers_intercepted'],[])

    def test_original_mutex_enforces_owner_nonrecursive_and_nonblocking_handoff(self):
        module=self.implementation();self.assertTrue(hasattr(module,'probe_rtos_mutex'))
        result=module.probe_rtos_mutex(component('gr2','b01firm8'))
        self.assertEqual(result['create_returned'],1)
        self.assertEqual(result['returns'],[0,-28,-50,-28,0,0,0])
        self.assertEqual(result['owners'],[1,1,1,1,0,2,0])
        self.assertTrue(result['stack_preserved']);self.assertEqual(result['helpers_intercepted'],[])

    def test_original_iq_engine_builds_hardware_configuration_and_returns_its_computed_matrix(self):
        module=self.implementation()
        result=module.probe_producer_iq(component('gr2','b01firm8'),component('gr2','b01firm6'),deep=True)
        self.assertEqual(result['hardware_mode'],6)
        self.assertEqual(result['hardware_raw_address'],0x68000000)
        self.assertEqual(result['hardware_yuv_address'],0x60000000)
        self.assertTrue(result['computed_response_nonzero']);self.assertTrue(result['response_copied'])
        self.assertTrue(result['stack_preserved']);self.assertGreater(result['mutex_boundaries'],0)
        self.assertEqual(result['helpers_intercepted'],['mutex lock/unlock','ISP hardware pipeline'])

    def test_original_iq_library_initialization_and_producer_request_run_with_official_resources(self):
        module=self.implementation();self.assertTrue(hasattr(module,'probe_producer_iq'))
        result=module.probe_producer_iq(component('gr2','b01firm8'),component('gr2','b01firm6'))
        self.assertEqual(result['iq_bytes'],194848);self.assertEqual(result['common_bytes'],60)
        self.assertEqual(result['constructor_return'],0);self.assertEqual(result['load_return'],0)
        self.assertEqual(result['library_ready'],1)
        self.assertEqual(result['raw_address'],0x68000000);self.assertEqual(result['yuv_address'],0x60000000)
        self.assertEqual(result['frame_address'],0x51000008)
        self.assertEqual(result['producer_return'],(4<<16)|32)
        self.assertTrue(result['response_copied']);self.assertTrue(result['source_resources_unchanged'])
        self.assertTrue(result['arena_guards_unchanged']);self.assertTrue(result['stack_preserved'])
        self.assertEqual(result['helpers_intercepted'],['ISP engine completion'])
        changed=bytearray(component('gr2','b01firm6'));changed[1000]^=1
        with self.assertRaises(ValueError):module.probe_producer_iq(component('gr2','b01firm8'),bytes(changed))

    def test_original_isp_color_recipe_reads_frame_408_in_its_own_numeric_space(self):
        module=self.implementation();expected=[0,1,14,2,3,4,5,6,7,8,9,10,11,12,13,0,16,0,15,17,18]
        self.assertTrue(hasattr(module,'probe_isp_color_recipe'))
        for tone,recipe in enumerate(expected):
            with self.subTest(frame_color_mode=tone):
                report=module.probe_isp_color_recipe(component('gr2','b01firm8'),tone)
                self.assertEqual(report['recipe'],recipe)
                self.assertEqual(report['monochrome'],int(tone in (5,7)))
                self.assertTrue(report['context_unchanged'])
                self.assertTrue(report['output_guards_unchanged'])
                self.assertTrue(report['stack_preserved'])
                self.assertEqual(report['helpers_intercepted'],[])

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

    def test_original_isp_completion_wait_uses_event_13_and_clears_observed_bits(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_isp_completion_wait(component('gr2','b01firm8'))
        self.assertEqual(report['event_id'],13)
        self.assertEqual(report['requested_bits'],0x11)
        self.assertEqual(report['wait_mode'],1)
        self.assertEqual(report['clear_mask'],0xffffffee)
        self.assertEqual(report['observed_bits'],0x11)
        self.assertEqual(report['returned'],0)
        self.assertTrue(report['stack_preserved'])

    def test_original_effect_widget_navigation_runs_all_graphics_contexts_and_property_setters(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_effect_view_init(component('gr2','b01firm8'),activate=True,settle_animation=True,navigate=True)
        self.assertEqual(report['navigation'],[{'event':0x60002004,'index':2,'effect':6},{'event':0x60002004,'index':3,'effect':7},{'event':0x60002003,'index':2,'effect':6}])
        self.assertEqual(report['graphics_contexts'],6)
        self.assertGreater(report['display_writes'],0)
        self.assertTrue(report['guards_unchanged'])
        self.assertTrue(report['stack_preserved'])
        self.assertEqual(report['helpers_intercepted'],['palette backend upload/apply'])

    def test_original_effect_list_draws_official_font_resources_before_and_after_navigation(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8');disk=component('gr2','b01firm6')
        report=module.probe_effect_view_draw(code,disk)
        self.assertEqual(report['font_resources'],['A:/font/RT_Latin.pac','A:/font/LE_Latin.bin','A:/font/RT_Moni.pac','A:/font/LE_JP.bin'])
        self.assertEqual(report['navigation_effects'],[6,7,6])
        self.assertEqual(report['draw_returns'],[1,1])
        self.assertGreater(report['font_engine_calls'],0)
        self.assertGreater(report['display_nonzero_bytes'],10000)
        self.assertTrue(report['guards_unchanged'])
        self.assertTrue(report['stack_preserved'])
        self.assertFalse(report['hardware_tested'])
        with self.assertRaises(ValueError):module.probe_effect_view_draw(code,disk[:-1]+bytes([disk[-1]^1]))

    def test_original_osd_color_converter_proves_rgb_and_alpha_nibble_order(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_osd_colors(component('gr2','b01firm8'))
        self.assertEqual(len(report['colors']),256)
        def q(value):return (min(255,max(0,value//1000))+8)//17
        for row in report['colors']:
            packed=row['palette'];y=(packed>>16)&255;u=((packed>>8)&255)-128;v=(packed&255)-128
            expected=q(1164*y+1596*v)<<12|q(1164*y-391*u-813*v)<<8|q(1164*y+2018*u)<<4|row['alpha']
            self.assertEqual(row['rgb4444'],expected)
        self.assertEqual(report['colors'][1]['rgb4444'],0xffff)
        self.assertEqual(report['colors'][4]['rgb4444'],0x000f)
        self.assertEqual(report['helpers_intercepted'],[])

    def test_original_root_transition_and_draw_dispatch_own_the_stock_effect_page(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_effect_view_draw(component('gr2','b01firm8'),component('gr2','b01firm6'),attach=True)
        self.assertTrue(report['active_root_matches'])
        self.assertEqual(report['page_events'][:2],[0x60000000,0x60000001])
        self.assertIn(0x60000003,report['page_events'])
        self.assertEqual(report['navigation_effects'],[6,7,6])
        self.assertEqual(report['draw_returns'],[0,0])
        self.assertTrue(report['guards_unchanged'])
        self.assertTrue(report['stack_preserved'])
        self.assertTrue(report['low_module_loaded'])

    def test_original_image_object_fixed_pools_own_construct_clone_and_retirement(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        for extra in (0,128,128+12288):
            with self.subTest(inline_extension=extra):
                report=module.probe_image_object_pools(component('gr2','b01firm8'),extra=extra)
                self.assertEqual(report['pool_counts'],[60,91])
                self.assertEqual(report['pool_block_bytes'],[0xfb14+extra,0x7f00])
                self.assertTrue(report['constructor_zeroed'])
                self.assertEqual(report['header_magic'],'IMG ')
                self.assertEqual(report['counter_after_construct'],1)
                self.assertTrue(report['clone_matches'])
                self.assertTrue(report['inline_extension_cloned'])
                self.assertTrue(report['freed_magic_invalid'])
                self.assertEqual(report['counter_after_retirement'],0)
                self.assertTrue(report['retired_slot_cleared'])
                self.assertEqual(report['exhausted_return'],0xffffffce)
                self.assertEqual(report['unique_blocks'],60)
                self.assertTrue(report['all_blocks_released'])
                self.assertTrue(report['stack_preserved'])
                self.assertEqual(report['helpers_intercepted'],['mutex create/lock/unlock'])

    def test_original_main_yuv_handoff_sets_valid_length_before_encode(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_main_yuv_handoff(component('gr2','b01firm8'))
        self.assertEqual(report['source_offset'],0x1f0)
        self.assertEqual(report['destination_offset'],0x1f4)
        self.assertTrue(report['source_cleared'])
        self.assertTrue(report['same_handle'])
        self.assertEqual(report['used_before'],0)
        self.assertEqual(report['used_after'],4928*3264*2)
        self.assertEqual(report['queried_buffer_kinds'],[0x17])
        self.assertTrue(report['stack_preserved'])

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

    def test_effect_screen_key_actions_preserve_payload_and_distinct_guarded_routes(self):
        module=self.implementation();report=module.probe_effect_key_routes(component('gr2','b01firm8'))
        routes=report['routes'];self.assertEqual(len(routes),17)
        for source,target in ((0x60001006,0x60002003),(0x60001007,0x60002004),(0x6000100a,0x60002005)):
            route=next(row for row in routes if row['source_event']==source)
            self.assertEqual(route['queued_event'],target)
        left=[row for row in routes if row['source_event']==0x60001008]
        self.assertEqual(len(left),2);self.assertTrue(all(row['predicate'] for row in left))
        self.assertEqual({row['queued_event'] for row in left},{0x60002002,0x6000200f})
        self.assertEqual(next(row['accepted_focus'] for row in left if row['queued_event']==0x60002002),[0,6])
        self.assertEqual(next(row['accepted_focus'] for row in left if row['queued_event']==0x6000200f),[1])
        self.assertTrue(all(row['payload']==[0x12345678,0x23456789] for row in routes))
        self.assertTrue(all(row['returned']==1 for row in routes))
        self.assertEqual(next(row['source_name'] for row in routes if row['source_event']==0x60001017),'APP_EVENT_SYS_JOG_LEFT')

    def test_original_effect_screen_constructor_initializes_embedded_views_without_helpers(self):
        module=self.implementation();report=module.probe_effect_view_init(component('gr2','b01firm8'))
        self.assertEqual(report['returned'],1)
        self.assertEqual(report['widget_offsets'],[0x44,0x84,0x42c,0x4a0,0x294,0x304,0x344])
        self.assertEqual(report['focus'],0)
        self.assertTrue(report['guards_unchanged']);self.assertTrue(report['stack_preserved'])
        self.assertLessEqual(report['highest_written_offset'],0x600)
        self.assertEqual(report['external_writes'],[])
        self.assertEqual(report['helpers_intercepted'],[])

    def test_original_effect_screen_init_uses_property_bank_and_defers_animation_without_rendering(self):
        module=self.implementation();report=module.probe_effect_view_init(component('gr2','b01firm8'),activate=True)
        self.assertEqual(report['returned'],0)
        self.assertEqual(report['list_count'],18);self.assertEqual(report['list_cursor'],1)
        self.assertEqual(report['effect_property'],5)
        self.assertEqual(report['animation_state'],2)
        self.assertGreater(report['pending_draw_mask'],0)
        self.assertTrue(report['guards_unchanged']);self.assertTrue(report['stack_preserved'])
        self.assertEqual(report['helpers_intercepted'],[])

    def test_original_osd_context_and_animation_use_distinct_physical_and_logical_geometry(self):
        module=self.implementation();report=module.probe_effect_view_init(component('gr2','b01firm8'),activate=True,settle_animation=True)
        self.assertEqual(report['physical_size'],[720,480]);self.assertEqual(report['logical_size'],[640,480])
        self.assertEqual(report['animation_state'],0)
        self.assertEqual(report['palette_backend_calls'],3)
        self.assertEqual(report['effect_property'],5)
        self.assertTrue(report['guards_unchanged']);self.assertTrue(report['stack_preserved'])
        self.assertFalse(report['hardware_tested'])

    def test_original_ui_preview_preserves_first_value_and_cancel_or_commit_frees_all_storage(self):
        module=self.implementation();code=component('gr2','b01firm8')
        for commit in (False,True):
            with self.subTest(commit=commit):
                report=module.probe_ui_undo(code,commit=commit)
                self.assertEqual(report['preview_values'],[6,7]);self.assertEqual(report['saved_original_values'],[5,5])
                self.assertEqual(report['final_effect'],7 if commit else 5)
                self.assertEqual(report['stack_depth_after'],0);self.assertEqual(report['active_after'],0)
                self.assertEqual(report['pool_bytes_after'],report['pool_bytes_before'])
                self.assertEqual(report['helpers_intercepted'],[])

    def test_original_seek_sign_extends_offset_and_passes_origin_on_stack(self):
        module=self.implementation();code=component('gr2','b01firm8')
        for offset,origin in ((0,0),(4096,0),(0x7fffffff,0),(-1,1),(-4096,2)):
            with self.subTest(offset=offset,origin=origin):
                report=module.probe_sd_seek(code,offset,origin)
                self.assertEqual(report['offset_high'],0xffffffff if offset<0 else 0)
                self.assertEqual(report['offset_low'],offset&0xffffffff)
                self.assertEqual(report['origin'],origin);self.assertEqual(report['returned'],0)
                self.assertTrue(report['stack_preserved'])
        self.assertEqual(module.probe_sd_seek(code,4096,0,fail=True)['returned'],0xffffffff)

    def test_original_tell_copies_big_endian_64_bit_position_only_after_success(self):
        module=self.implementation();code=component('gr2','b01firm8')
        for position in (0,104,0x100000001):
            with self.subTest(position=position):
                report=module.probe_sd_tell(code,position)
                self.assertEqual(report['position_hex'],position.to_bytes(8,'big').hex())
                self.assertEqual(report['returned'],0);self.assertTrue(report['guards_unchanged'])
        error=module.probe_sd_tell(code,104,fail=True)
        self.assertEqual(error['returned'],0xffffffff);self.assertEqual(error['position_hex'],'a5'*8)

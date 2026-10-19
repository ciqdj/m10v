import unittest
from scripts.read_gr3_debug_log import lifecycle_profiles,file_profiles,be_file_profiles

def row(event,recipe,ticks,result=0):
 return {'event':event,'arguments':[recipe,ticks&0xffffffff,ticks>>32,result],
         'build_id':'abc12345','channel':'io','sequence':ticks}

class LifecycleDecoderTests(unittest.TestCase):
 def test_actual_be_file_service_is_separate_from_recipe_and_card_durability(self):
  records=[row(200,456,100),row(201,456,240,1),row(202,456,0)]
  records[-1]['arguments']=[456,0,2,1]
  p=be_file_profiles(records)[0]
  self.assertEqual(p['service_ticks'],140)
  self.assertEqual(p['stage'],'success');self.assertEqual(p['frame_slot'],2)
  self.assertEqual(p['context_cookie'],'0x1c8')
  self.assertFalse(p['recipe_association_proven']);self.assertFalse(p['durable_file_proven'])
  records[-1]['arguments'][1]=6
  self.assertEqual(be_file_profiles(records)[0]['stage'],'close-error')
 def test_isp_observer_is_reported_without_claiming_hardware_effects(self):
  records=[row(198,123,0)]
  records[0]['arguments']=[123,0x49535001,(7<<16)|19,380]
  records.extend([row(193,123,100),row(194,123,300),row(192,123,500,1)])
  p=lifecycle_profiles(records)[0]
  self.assertEqual(p['isp'],{'status':7,'mode':'observer','stock_tone':19,'sequence':380,'effects_offloaded':False})
  self.assertEqual(p['render_begin_ticks'],100)
  self.assertEqual(p['jpeg_wait_return_ticks'],500)
 def test_unknown_isp_status_and_wrong_tag_do_not_claim_offload(self):
  records=[row(198,123,0),row(193,123,100)]
  records[0]['arguments']=[123,0x49535001,(99<<16)|18,380]
  self.assertEqual(lifecycle_profiles(records)[0]['isp']['mode'],'unknown')
  self.assertIsNone(lifecycle_profiles(records)[0]['isp']['effects_offloaded'])
  records[0]['arguments'][1]=0
  self.assertNotIn('isp',lifecycle_profiles(records)[0])
 def test_wait_return_is_distinct_from_render_and_never_proves_file_save(self):
  records=[row(193,123,100),row(194,123,200),row(190,123,220),row(191,123,230),row(192,123,450,1)]
  p=lifecycle_profiles(records)[0]
  self.assertEqual(p['recipe'],'0x7b');self.assertEqual(p['render_ticks'],100)
  self.assertEqual(p['jpeg_submit_ticks'],10);self.assertEqual(p['jpeg_wait_ticks'],220)
  self.assertTrue(p['jpeg_event_received']);self.assertFalse(p['file_save_proven'])
 def test_same_owner_reuse_missing_completion_and_failed_clock_remain_distinct(self):
  records=[row(193,123,100),row(190,123,200),row(191,123,210),row(193,123,500),row(194,123,510,0xfffffffd),row(192,123,530,1)]
  records[-1]['arguments'][2]=0x80000000
  a,b=lifecycle_profiles(records)
  self.assertIsNone(a['jpeg_wait_ticks']);self.assertFalse(a['jpeg_event_received'])
  self.assertEqual(b['render_result'],-3);self.assertIsNone(b['jpeg_wait_ticks']);self.assertFalse(b['clock_valid'])
 def test_file_callback_payload_and_return_byte_are_reported_without_claiming_durability(self):
  records=[row(195,123,100),{'event':181,'arguments':[456,0x42000,0,123],'build_id':'abc12345','channel':'io','sequence':2},row(196,123,300,1)]
  p=file_profiles(records)[0]
  self.assertEqual(p['service_ticks'],200);self.assertEqual(p['service_result'],1)
  self.assertEqual(p['callbacks'][0]['payload_status'],0);self.assertFalse(p['durable_file_proven'])

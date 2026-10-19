import struct
import unittest
import zlib
from scripts.read_gr3_debug_log import decode_logs

def page(events):
    data=bytearray(4096);header=[0x4744564d,1,42,len(events),len(events),len(events),2]+[0]*9
    for i,event in enumerate(events):
        record=[0x474c564d,1,i+1,*event,42,2]+[0]*6
        raw=bytearray(struct.pack('<16I',*record));struct.pack_into('<I',raw,60,zlib.crc32(raw[:60]));data[64+64*i:128+64*i]=raw
    struct.pack_into('<16I',data,0,*header);struct.pack_into('<I',data,60,zlib.crc32(data[:60]));return data

class ProfileDecoderTests(unittest.TestCase):
    def test_stage_durations_and_reused_recipe_addresses_stay_per_shot(self):
        events=[]
        for film in (33,66,67):
            for stage in range(1,13):
                ticks=0xffffff00+stage*100+film*10000
                events.append((150,0x550709b8,stage,ticks&0xffffffff,ticks>>32))
                if stage==3:events.append((132,0x550709b8,film,1,0))
        result=decode_logs([page(events)])
        self.assertEqual([r['film'] for r in result['capture_profiles']],[33,66,67])
        for row in result['capture_profiles']:
            self.assertTrue(row['complete']);self.assertEqual(row['total_ticks'],1100);self.assertEqual(row['total_seconds'],1.1)
            self.assertEqual(row['units'],'milliseconds')
            self.assertEqual([r['ticks'] for r in row['intervals']],[100]*11)

    def test_failed_counter_and_truncated_first_shot_are_not_valid_durations(self):
        result=decode_logs([page([(150,1,8,42,0),(150,1,12,50,0),
            (150,1,1,100,0),(150,1,0x80000002,0,0),(150,1,12,90,0)])])
        rows=result['capture_profiles']
        self.assertFalse(rows[0]['complete']);self.assertIsNone(rows[0]['total_ticks'])
        self.assertFalse(rows[1]['complete']);self.assertIsNone(rows[1]['total_ticks'])

    def test_overlapping_pages_recover_old_prefix_and_deduplicate(self):
        def window(first,last):
            events=[(150,1,i,100*i,0) for i in range(first,last+1)]
            data=page(events)
            for j,sequence in enumerate(range(first,last+1)):
                at=64+j*64;struct.pack_into('<I',data,at+8,sequence)
                struct.pack_into('<I',data,at+60,zlib.crc32(data[at:at+60]))
            struct.pack_into('<I',data,20,last)
            struct.pack_into('<I',data,60,zlib.crc32(data[:60]));return data
        for pages in ([window(1,8),window(5,12)],[window(5,12),window(1,8)]):
            result=decode_logs(pages)
            self.assertEqual([r['sequence'] for r in result['records']],list(range(1,13)))
            self.assertTrue(result['capture_profiles'][0]['complete'])

    def test_backend_and_released_raw_are_scoped_to_current_capture(self):
        result=decode_logs([page([(150,0x550709b8,1,100,0),
            (126,0x550709b8,2,0,0),(134,0x550709b8,12000,9500,7),
            (150,0x550709b8,12,200,0)])])
        row=result['capture_profiles'][0]
        self.assertEqual(row['raw_lifetime']['status'],2)
        self.assertEqual(row['texture_backend']['batch_pixels'],12000)
        self.assertTrue(row['texture_backend']['cache_selected'])
        self.assertFalse(row['texture_backend']['batch_rejected'])

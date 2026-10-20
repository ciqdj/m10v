"""Shared settings interactions execute on GR II BE32 with explicit backend callbacks."""
import struct
import unittest
import zlib
from tests import test_gr2_runtime_build as runtime_tests

class Gr2SettingsTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    machine=runtime_tests.Gr2RuntimeBuildTests.machine
    call=runtime_tests.Gr2RuntimeBuildTests.call

    def test_native_owned_settings_overlay_draws_and_keeps_confirmation_and_close_lifetimes(self):
        from scripts.analyze_gr2_native_contract import probe_effect_view_draw
        from tests.test_unity_update import component
        runtime=self.build();self.assertIn('gr2_settings_open',runtime['symbols']);self.assertIn('gr2_settings_raw_event',runtime['symbols'])
        report=probe_effect_view_draw(component('gr2','b01firm8'),component('gr2','b01firm6'),native_runtime=runtime,attach=True,settings_overlay=True,language=4,settings_raw_hook=True)
        self.assertIn('A:/font/RT_CN_S.pac',report['font_resources']);self.assertIn('A:/font/LE_CN_S.bin',report['font_resources'])
        self.assertGreater(report['settings_opened'],0);self.assertEqual(report['settings_duplicate'],0)
        self.assertEqual(report['settings_initial'][:2],[1,0]);self.assertEqual(report['settings_after_right'][:2],[1,1])
        self.assertEqual(report['settings_after_catalog'][:5],[2,1,1,0,33])
        self.assertEqual(report['settings_after_install'][:2],[1,1])
        self.assertEqual(report['settings_writes'],[['install',1,66],['stamp',1,0,0,0]])
        self.assertGreater(report['settings_changed_bytes'],100000)
        self.assertTrue(report['settings_camera_root_preserved']);self.assertTrue(report['settings_pool_restored'])
        self.assertEqual(report['settings_closed'],[0,0]);self.assertEqual(report['settings_underlying_effect'],6)
        self.assertTrue(report['settings_raw_scope_restored']);self.assertEqual(report['settings_raw_double_deliveries'],0)

    def test_five_slots_catalog_identity_and_all_stamp_fields_keep_confirm_cancel_semantics(self):
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();self.assertTrue('m10v_settings_open' in report['symbols']);u=self.machine(report)
        self.call(u,report['symbols']['m10v_library_init'],[0x50001000]);saved=bytearray(u.mem_read(0x50001000,104))
        ids=[33,*range(66,79),*range(34,66)];behavior={'fail':False};writes=[]
        functions=[0x5001d000+i*4 for i in range(5)];context=0x5000c000;ops=0x50000000;page=0x50002000
        u.mem_write(ops,struct.pack('>6I',context,*functions))
        def backend(uc,address,size,unused):
            self.assertEqual(uc.reg_read(r.UC_ARM_REG_R0),context)
            a,b,c=[uc.reg_read(reg) for reg in (r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3)];result=0
            if address==functions[0]:uc.mem_write(a,bytes(saved))
            elif address==functions[1]:result=ids[a] if a<len(ids) else 0
            elif behavior['fail']:result=0xffffffff
            else:
                if address==functions[2]:
                    self.assertEqual(ids[a],b);self.assertLess(c,5);struct.pack_into('>H',saved,12+c*8,b);writes.append(('install',c,b))
                elif address==functions[3]:
                    color=struct.unpack('>I',uc.mem_read(uc.reg_read(r.UC_ARM_REG_SP),4))[0]
                    saved[52:56]=bytes((a,b,c,color));writes.append(('stamp',a,b,c,color))
                else:struct.pack_into('>I',saved,96,a);writes.append(('name',a))
                struct.pack_into('>I',saved,100,zlib.crc32(saved[:100]))
            uc.reg_write(r.UC_ARM_REG_R0,result);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,backend,begin=functions[0],end=functions[-1])
        def fields():return struct.unpack('>7I',u.mem_read(page+104,28))
        def key(k):self.call(u,report['symbols']['m10v_settings_key'],[page,ops,k])
        def open_page(screen):return self.call(u,report['symbols']['m10v_settings_open'],[page,ops,screen])
        self.assertEqual(open_page(1),0)
        for _ in range(4):key(1)
        key(4);self.assertEqual(fields()[:4],(2,4,4,0));self.assertEqual(writes,[])
        key(3);self.assertEqual(fields()[3],5);key(2);self.assertEqual(fields()[3],0)
        key(1);self.assertEqual(fields()[4],66)
        ids[1]=67;key(4);self.assertEqual(fields()[6],2);self.assertEqual(writes,[])
        ids[1]=66;key(0);key(1);behavior['fail']=True;key(4);self.assertEqual(fields()[0],2);self.assertEqual(fields()[6],3)
        behavior['fail']=False;key(4);self.assertEqual(fields()[:2],(1,4));self.assertEqual(writes,[('install',4,66)])
        key(4);key(5);self.assertEqual(len(writes),1);key(5);self.assertEqual(fields()[0],0)
        self.assertEqual(open_page(3),0);effects=bytes(saved[56:96])
        for field in range(4):
            for value in range(1,3 if field==0 else 4):
                key(4);self.assertEqual(fields()[0],4);key(1);key(4)
                self.assertEqual(saved[52+field],value);self.assertEqual(fields()[0],3)
            key(3)
        self.assertEqual(bytes(saved[56:96]),effects);before=len(writes)
        key(4);key(1);key(5);self.assertEqual(len(writes),before);self.assertEqual(struct.unpack_from('>I',saved,96)[0],0)
        key(4);key(1);behavior['fail']=True;key(4);self.assertEqual(fields()[0],4);self.assertEqual(fields()[6],3)
        behavior['fail']=False;key(4);self.assertEqual(fields()[0],3);self.assertEqual(struct.unpack_from('>I',saved,96)[0],1)
        self.assertEqual(open_page(99),0xffffffff);self.assertEqual(fields()[0],0)

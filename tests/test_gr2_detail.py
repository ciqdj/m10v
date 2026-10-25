"""GR II film controls execute as BE32 code against an observed journal backend."""
import struct
import unittest
from tests import test_gr2_runtime_build as runtime_tests

class Gr2DetailTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    machine=runtime_tests.Gr2RuntimeBuildTests.machine
    call=runtime_tests.Gr2RuntimeBuildTests.call

    def fixture(self):
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();self.assertIn('gr2_detail_open',report['symbols'])
        u=self.machine(report);s=report['symbols'];state=0x50001000;view=0x50002000;ops=0x50000000
        self.call(u,s['m10v_library_init'],[state]);disk=bytearray(u.mem_read(state,104));writes=[];mode={'fail':False,'unreadable':False}
        u.mem_write(ops,struct.pack('>3I',0x1234,0x5001d000,0x5001d004))
        def backend(uc,address,size,unused):
            self.assertEqual(uc.reg_read(r.UC_ARM_REG_R0),0x1234)
            ptr=uc.reg_read(r.UC_ARM_REG_R1);result=0
            if address==0x5001d000:
                if mode['unreadable']:result=0xffffffff
                else:uc.mem_write(ptr,bytes(disk))
            else:
                writes.append(bytes(uc.mem_read(ptr,104)))
                if not mode['fail'] or mode.get('commit_on_failure'):disk[:]=writes[-1]
                if mode['fail']:result=0xffffffff
            uc.reg_write(r.UC_ARM_REG_R0,result);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,backend,begin=0x5001d000,end=0x5001d004)
        def call(name,*args):return self.call(u,s[name],list(args))
        return u,view,ops,disk,writes,mode,call

    def test_every_selectable_film_has_exact_gr3_visible_fields_and_limits(self):
        u,v,ops,disk,writes,mode,call=self.fixture()
        for film in [33,*range(34,79),79,288]:
            call('m10v_library_init',0x50001000)
            # Independently encode a valid selected film and CRC.
            import zlib
            struct.pack_into('>H',disk,12,film);disk[62:64]=bytes((1 if film>78 else 0,0))
            disk[61]=0;struct.pack_into('>I',disk,100,zlib.crc32(disk[:100]))
            self.assertEqual(call('gr2_detail_open',v,ops,0),1)
            expected=([0,1,2] if film in (33,67) else [])+[3,5,6,7,8,9]+([10] if film in (67,68) else [])+[11]
            self.assertEqual([call('gr2_detail_field',v,i) for i in range(len(expected))],expected)
            self.assertEqual(call('gr2_detail_field',v,len(expected)),0xffffffff)
            self.assertEqual(call('gr2_detail_limit',v,4),0xffffffff)
            self.assertEqual(call('gr2_detail_limit',v,10),1 if film==67 else 2 if film==68 else 0xffffffff)
        self.assertEqual(writes,[])

    def test_immediate_save_failure_restores_actual_state_and_reset_preserves_custom_bank(self):
        u,v,ops,disk,writes,mode,call=self.fixture()
        self.assertEqual(call('gr2_detail_open',v,ops,4),1)
        self.assertEqual(call('gr2_detail_set',v,ops,(3<<8)|3),1)
        self.assertEqual(disk[46],3);self.assertEqual(call('gr2_detail_value',v,3),3)
        mode['fail']=True
        self.assertEqual(call('gr2_detail_set',v,ops,(3<<8)|1),0)
        self.assertEqual(call('gr2_detail_value',v,3),3)
        self.assertEqual(struct.unpack('>I',u.mem_read(v+112,4))[0],1)
        mode['unreadable']=True
        self.assertEqual(call('gr2_detail_set',v,ops,(3<<8)|2),0)
        self.assertEqual(call('gr2_detail_value',v,3),0xffffffff)
        count=len(writes)
        self.assertEqual(call('gr2_detail_set',v,ops,(3<<8)|2),0);self.assertEqual(len(writes),count)
        mode.update(fail=False,unreadable=False)
        import zlib
        struct.pack_into('>H',disk,44,288);disk[94]=2;disk[46]=3;disk[47]=3
        struct.pack_into('>I',disk,100,zlib.crc32(disk[:100]))
        self.assertEqual(call('gr2_detail_open',v,ops,4),1)
        self.assertEqual(call('gr2_detail_set',v,ops,(11<<8)),1)
        self.assertEqual(struct.unpack_from('>H',disk,44)[0],288);self.assertEqual(disk[94],2)
        self.assertEqual(disk[46:48],bytes((1,0)))

    def test_hidden_fields_bad_slot_and_out_of_range_values_never_write(self):
        u,v,ops,disk,writes,mode,call=self.fixture()
        self.assertEqual(call('gr2_detail_open',v,ops,5),0)
        self.assertEqual(call('gr2_detail_open',v,ops,0),1)
        for field,value in ((0,1),(4,1),(10,1),(3,4),(5,3),(6,9),(7,6),(8,9),(9,2),(11,1),(12,0)):
            self.assertEqual(call('gr2_detail_set',v,ops,(field<<8)|value),0)
        self.assertEqual(writes,[])

    def test_original_effect_root_opens_owned_detail_and_raw_keys_do_not_reach_stock_twice(self):
        from scripts.analyze_gr2_native_contract import probe_effect_view_draw
        from tests.test_unity_update import component
        result=probe_effect_view_draw(component('gr2','b01firm8'),component('gr2','b01firm6'),native_runtime=self.build(),attach=True,language=4,detail_overlay=True)
        self.assertTrue(result['detail_opened'])
        self.assertEqual(result['detail_stock_routes'],[0x6000400b])
        self.assertEqual(result['detail_route_slots'],[4])
        self.assertTrue(result['detail_root_preserved']);self.assertTrue(result['detail_pool_restored'])
        self.assertEqual(result['detail_raw_deliveries'],0)
        self.assertEqual(result['detail_fields'],[0,1,2,3,5,6,7,8,9,11])
        self.assertEqual(result['detail_grain'],1);self.assertEqual(result['detail_failed_value'],1)
        self.assertEqual(result['detail_reset_grain'],0)
        self.assertEqual(result['detail_writes'],3)
        self.assertGreater(result['detail_changed_bytes'],100000)
        self.assertTrue(result['detail_closed'])

    def test_detail_route_only_replaces_enabled_five_carriers_on_exact_stock_effect_root(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from tests.test_unity_update import component
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();u=runtime_machine(component('gr2','b01firm8'));u.mem_write(report['base'],bytes.fromhex(report['runtime_hex']))
        symbols=report['symbols'];root=0x50008000;opened=[];tone=[8];reads=[]
        template=bytes(u.mem_read(0xa0411a18,64));u.mem_write(root,template)
        def boundary(uc,address,size,unused):
            value=0
            if address==0xa03989c8:value=root
            elif address==0xa00e0e80:
                reads.append(uc.reg_read(r.UC_ARM_REG_R0));value=tone[0]
            else:opened.append([uc.reg_read(r.UC_ARM_REG_R0),uc.reg_read(r.UC_ARM_REG_R1)])
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        for address in (0xa03989c8,0xa00e0e80,symbols['gr2_settings_detail_open']):u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        def route():return self.call(u,symbols['gr2_settings_menu_route'],[0x6000400b])
        self.assertEqual(route(),0);self.assertEqual(opened,[])
        self.assertEqual(self.call(u,symbols['gr2_menu_films_enable'],[1]),1)
        for i,carrier in enumerate((9,10,11,18,8)):
            tone[0]=carrier;self.assertEqual(route(),1);self.assertEqual(opened[-1],[i,0])
        self.assertEqual(reads,[43]*5);count=len(opened)
        for native in set(range(21))-{9,10,11,18,8}:
            tone[0]=native;self.assertEqual(route(),0)
        self.assertEqual(len(opened),count)
        tone[0]=8;count_reads=len(reads)
        for offset,replacement in ((0,0xa03ad0c6),(4,0x17),(0x30,0x65),(0x38,0x04000000)):
            u.mem_write(root,template);u.mem_write(root+offset,struct.pack('>I',replacement));self.assertEqual(route(),0)
        self.assertEqual(len(reads),count_reads);self.assertEqual(len(opened),count)

    def test_all_visible_parameter_values_match_independent_journal_bytes(self):
        import zlib
        u,v,ops,disk,writes,mode,call=self.fixture()
        for film in (33,67,68,69,79):
            struct.pack_into('>H',disk,28,film);disk[31]=3;disk[35]=3
            disk[77]=0;disk[78]=1 if film>78 else 0
            struct.pack_into('>I',disk,100,zlib.crc32(disk[:100]))
            self.assertEqual(call('gr2_detail_open',v,ops,2),1)
            fields=([0,1,2] if film in (33,67) else [])+[3,5,6,7,8,9]+([10] if film in (67,68) else [])
            for field in fields:
                limit={0:8,1:8,2:8,3:3,5:2,6:8,7:5,8:8,9:1,10:1 if film==67 else 2}[field]
                for value in range(limit+1):
                    expected=bytearray(disk)
                    offset=32+field if field<3 else 30 if field==3 else 72+field-5
                    expected[offset]=value
                    if film==33 and field<=3:expected[35]=2
                    struct.pack_into('>I',expected,8,struct.unpack_from('>I',expected,8)[0]+1)
                    struct.pack_into('>I',expected,100,zlib.crc32(expected[:100]))
                    self.assertEqual(call('gr2_detail_set',v,ops,field<<8|value),1,(film,field,value))
                    self.assertEqual(disk,expected,(film,field,value))
                    self.assertEqual(call('gr2_detail_value',v,field),value)

    def test_failed_close_reconciles_committed_value_and_replaced_film_never_gets_stale_write(self):
        import zlib
        u,v,ops,disk,writes,mode,call=self.fixture()
        self.assertEqual(call('gr2_detail_open',v,ops,0),1)
        mode.update(fail=True,commit_on_failure=True)
        self.assertEqual(call('gr2_detail_set',v,ops,3<<8|2),0)
        self.assertEqual(call('gr2_detail_value',v,3),2)
        self.assertEqual(struct.unpack('>I',u.mem_read(v+112,4))[0],1)
        count=len(writes);struct.pack_into('>H',disk,12,68)
        struct.pack_into('>I',disk,100,zlib.crc32(disk[:100]))
        self.assertEqual(call('gr2_detail_set',v,ops,3<<8|1),0)
        self.assertEqual(len(writes),count)
        self.assertEqual(call('gr2_detail_value',v,3),0xffffffff)

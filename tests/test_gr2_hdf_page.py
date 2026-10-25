"""Independent HDF overlay interactions and UI-owner resource lifetime."""
import struct,unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2HdfPageTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    def fixture(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();self.assertIn('gr2_hdf_page_open',runtime['symbols'])
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_map(0x51000000,0x10000)
        symbols=runtime['symbols'];events=[];captions=[]
        state=dict(value=1,saved=1,reload=1,read=1,update=1,persist=1,allocate=1,attach=1,film=0,overlay=0)
        names=['gr2_allocate','gr2_release','gr2_overlay_attach','gr2_overlay_detach','gr2_text_draw_full','gr2_fill_rect',
               'gr2_hdf_reload','gr2_hdf_update','gr2_hdf_configuration_read','gr2_settings_active']
        addresses={symbols[name]:name for name in names}
        def boundary(machine,address,size,unused):
            name=addresses[address];a,b,c=[machine.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2)]
            value=1
            if name=='gr2_allocate':value=0x51000000 if state['allocate'] else 0;events.append(['allocate',a])
            elif name=='gr2_release':events.append(['release',a])
            elif name=='gr2_overlay_attach':
                value=state['attach'];events.append(['attach',a]);state['overlay']=a if value else 0
            elif name=='gr2_overlay_detach':
                self.assertEqual(a,state['overlay']);state['overlay']=0;events.append(['detach',a])
                destructor=struct.unpack('>I',machine.mem_read(a+16,4))[0]
                machine.reg_write(r.UC_ARM_REG_R1,0);machine.reg_write(r.UC_ARM_REG_PC,destructor);return
            elif name=='gr2_hdf_reload':value=state['reload'];events.append(['reload'])
            elif name=='gr2_hdf_update':
                events.append(['update',a]);value=state['update']
                if state['persist']:state['saved']=a
            elif name=='gr2_hdf_configuration_read':
                value=state['read']
                if value:machine.mem_write(a,struct.pack('>I',state['saved']));machine.mem_write(b,struct.pack('>I',5))
            elif name=='gr2_settings_active':value=state['film']
            elif name=='gr2_text_draw_full':
                captions.append(bytes(machine.mem_read(a,b*2)).decode('utf-16-be'))
                x,y,right,bottom=struct.unpack('>4h',machine.mem_read(c,8));self.assertTrue(0<=x<=right<720 and 0<=y<=bottom<480)
            elif name=='gr2_fill_rect':
                x,y,right,bottom=struct.unpack('>4h',machine.mem_read(b,8));self.assertTrue(0<=x<=right<720 and 0<=y<=bottom<480)
            machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in addresses:u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        call=lambda name,*args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,symbols[name],list(args))
        def peek():
            if not call('gr2_hdf_page_peek',0x50003000):return None
            return list(struct.unpack('>4I',u.mem_read(0x50003000,16)))
        def raw(key):
            u.mem_write(0x50003100,struct.pack('>3I',key,17,19));before=bytes(u.mem_read(0x50003100,12))
            result=call('gr2_hdf_page_raw_event',0x50003100);self.assertEqual(bytes(u.mem_read(0x50003100,12)),before);return result
        return state,events,captions,call,peek,raw

    def test_four_grades_saturate_confirm_save_and_back_cancel_with_balanced_overlay_ownership(self):
        s,events,captions,call,peek,raw=self.fixture()
        self.assertEqual(call('gr2_hdf_page_open'),0x51000000);self.assertEqual(peek(),[1,1,0,0])
        before=list(events);self.assertEqual(call('gr2_hdf_page_open'),0);self.assertEqual(events,before)
        self.assertEqual(call('gr2_hdf_page_draw'),1)
        self.assertEqual(captions,['HDF 模拟','左右选择 OK保存 DISP取消','关闭','弱','中','强','全局数字柔焦 · 独立于胶卷'])
        for _ in range(5):self.assertEqual(raw(0x60001009),1)
        self.assertEqual(peek(),[3,1,0,0]);self.assertEqual(raw(0x6000100e),1);self.assertIsNone(peek());self.assertEqual(s['saved'],1)
        self.assertFalse(any(row[0]=='update' for row in events));self.assertEqual(events[-1],['release',0x51000000])
        self.assertEqual(call('gr2_hdf_page_open'),0x51000000)
        for _ in range(5):self.assertEqual(raw(0x60001008),1)
        self.assertEqual(peek(),[0,1,0,0]);self.assertEqual(raw(0x6000100a),1);self.assertEqual(s['saved'],0)
        self.assertEqual(call('gr2_hdf_page_active'),0);self.assertEqual(call('gr2_hdf_page_close'),0)
        self.assertEqual(sum(row[0]=='allocate' for row in events),sum(row[0]=='release' for row in events))

    def test_failed_save_reconciles_persisted_value_stays_open_and_accepts_retry(self):
        s,events,captions,call,peek,raw=self.fixture();call('gr2_hdf_page_open');raw(0x60001009)
        s['update']=0;self.assertEqual(raw(0x60001016),1);self.assertEqual(peek(),[2,2,1,0])
        self.assertEqual(call('gr2_hdf_page_draw'),1);self.assertEqual(captions[-1],'读取或保存失败')
        self.assertEqual(raw(0xdeadbeef),0);self.assertEqual(peek(),[2,2,1,0])
        s['update']=1;self.assertEqual(raw(0x6000100a),1);self.assertIsNone(peek())

    def test_open_failures_do_not_leak_and_unknown_storage_stays_visible_without_writing(self):
        s,events,captions,call,peek,raw=self.fixture()
        s['film']=1;self.assertEqual(call('gr2_hdf_page_open'),0);self.assertEqual(events,[])
        s['film']=0;s['allocate']=0;self.assertEqual(call('gr2_hdf_page_open'),0)
        s['allocate']=1;s['attach']=0;self.assertEqual(call('gr2_hdf_page_open'),0);self.assertEqual(events[-1],['release',0x51000000])
        s.update(attach=1,reload=0,read=0);self.assertEqual(call('gr2_hdf_page_open'),0x51000000);self.assertEqual(peek(),[0,0,1,0])
        self.assertEqual(call('gr2_hdf_page_draw'),1);self.assertEqual(captions[-1],'读取或保存失败')
        self.assertFalse(any(row[0]=='update' for row in events));self.assertEqual(raw(0x6000100e),1);self.assertIsNone(peek())

    def test_original_fonts_draw_dispatch_and_raw_key_owner_execute_the_independent_page(self):
        from scripts.analyze_gr2_native_contract import probe_effect_view_draw
        runtime=self.build()
        result=probe_effect_view_draw(component('gr2','b01firm8'),component('gr2','b01firm6'),native_runtime=runtime,
                                      attach=True,hdf_overlay=True,language=4)
        self.assertGreater(result['hdf_opened'],0);self.assertEqual(result['hdf_duplicate'],0)
        self.assertEqual(result['hdf_initial'],[1,1,0,0]);self.assertEqual(result['hdf_grades'],[0,1,2,3,3])
        self.assertEqual(result['hdf_failed'],[3,3,1,0]);self.assertEqual(result['hdf_reopened_state'],[3,3,0,0])
        self.assertEqual(result['hdf_writes'],[3,2]);self.assertEqual(result['hdf_closed'],[None,None])
        self.assertGreater(result['hdf_changed_bytes'],100000)
        self.assertTrue(result['hdf_root_preserved']);self.assertTrue(result['hdf_pool_restored']);self.assertEqual(result['hdf_raw_double_deliveries'],[])
        self.assertEqual(result['hdf_underlying_effect'],result['hdf_underlying_before']);self.assertTrue(result['stack_preserved']);self.assertTrue(result['guards_unchanged'])

"""UI-owned activation waits for the original service lifecycle."""
import struct
import unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2BootTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    call=runtime_tests.Gr2RuntimeBuildTests.call

    def test_storage_gate_requires_final_return_and_live_original_file_services_without_io(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE
        runtime=self.build();self.assertTrue('gr2_ui_storage_ready' in runtime['symbols'])
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        def word(address,value):u.mem_write(address,struct.pack('>I',value))
        def half(address,value):u.mem_write(address,struct.pack('>H',value))
        word(runtime['symbols']['gr2_activation_ready'],1);word(runtime['symbols']['gr2_startup_complete'],1)
        control=0xa00c2c6c;head=0xa05fa9cc+28;volume=0xa06aa6a0
        word(0xa061ead0,1);word(control+0x20,0);word(control+0x24,0);word(control+8,0xa05fc940)
        word(control+0x1c,head);word(head,0x4d504c20);u.mem_write(head+4,b'\x00');half(head+0x14,1);half(0xa00b5bfe,32)
        word(volume+0x61a8,3);u.mem_write(volume+0x61ac,b'H')
        forbidden=[]
        def io(*args):forbidden.append(True);raise RuntimeError('readiness must not call original I/O or allocate')
        for address in (0xa00653bc,0xa002c70e,0xa0083d30,0xa006798c):u.hook_add(UC_HOOK_CODE,io,begin=address,end=address)
        entry=runtime['symbols']['gr2_ui_storage_ready']
        self.assertEqual(self.call(u,entry,[]),1)
        cases=[(runtime['symbols']['gr2_activation_ready'],0),(runtime['symbols']['gr2_startup_complete'],0),
               (0xa061ead0,0),(control+0x20,1),(control+0x24,1),(control+8,0),(control+0x1c,0),
               (control+0x1c,head+4),(head,0),(volume+0x61a8,1)]
        for address,value in cases:
            with self.subTest(address=hex(address),value=value):
                previous=bytes(u.mem_read(address,4));word(address,value)
                self.assertEqual(self.call(u,entry,[]),0);u.mem_write(address,previous)
        for address,value in ((head+4,b'\x01'),(head+0x14,b'\x00\x00'),(volume+0x61ac,b'G')):
            previous=bytes(u.mem_read(address,len(value)));u.mem_write(address,value)
            self.assertEqual(self.call(u,entry,[]),0);u.mem_write(address,previous)
        self.assertEqual(self.call(u,entry,[]),1);self.assertEqual(forbidden,[])

    def test_ui_owner_restores_once_and_retries_failures_only_on_explicit_menu_keys(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();self.assertTrue('gr2_ui_bootstrap' in runtime['symbols'])
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        symbols=runtime['symbols'];calls=[];behavior={'storage':0,'fail':None}
        names=['gr2_ui_storage_ready','gr2_initialize_state','gr2_configuration_reload','gr2_menu_entries_enable','gr2_effect_names_refresh']
        addresses={symbols[name]:name for name in names}
        def backend(machine,address,size,unused):
            name=addresses[address];arg=machine.reg_read(r.UC_ARM_REG_R0)
            calls.append([name,arg] if name=='gr2_menu_entries_enable' else [name])
            if name=='gr2_ui_storage_ready':value=behavior['storage']
            else:
                value=int(name!=behavior['fail'])
                if name=='gr2_initialize_state':
                    self.assertEqual(struct.unpack('>I',machine.mem_read(symbols['gr2_ui_boot_state'],4))[0],1)
            machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in addresses:u.hook_add(UC_HOOK_CODE,backend,begin=address,end=address)
        key=0x50001000
        def event(value):
            u.mem_write(key,struct.pack('>3I',value,0,0));result=self.call(u,symbols['gr2_ui_bootstrap'],[key])
            self.assertEqual(bytes(u.mem_read(key,12)),struct.pack('>3I',value,0,0));return result
        self.assertEqual(event(0x60000001),0);self.assertEqual(calls,[['gr2_ui_storage_ready']]);calls.clear()
        behavior['storage']=1;behavior['fail']='gr2_initialize_state'
        self.assertEqual(event(0x60000001),0);self.assertEqual(calls,[['gr2_ui_storage_ready'],['gr2_initialize_state']]);calls.clear()
        for value in (0x60000001,0x60001006,0x60001009):self.assertEqual(event(value),0)
        self.assertEqual(calls,[])
        behavior['fail']='gr2_effect_names_refresh'
        self.assertEqual(event(0x6000100a),0)
        self.assertEqual(calls,[['gr2_ui_storage_ready'],['gr2_initialize_state'],['gr2_configuration_reload'],['gr2_menu_entries_enable',1],['gr2_effect_names_refresh'],['gr2_menu_entries_enable',0]])
        calls.clear();behavior['fail']=None
        self.assertEqual(event(0x60001016),1)
        self.assertEqual(calls,[['gr2_ui_storage_ready'],['gr2_initialize_state'],['gr2_configuration_reload'],['gr2_menu_entries_enable',1],['gr2_effect_names_refresh']])
        calls.clear();self.assertEqual(event(0x60000001),1);self.assertEqual(event(0x6000100a),1);self.assertEqual(calls,[])
        self.assertEqual(struct.unpack('>I',u.mem_read(symbols['gr2_ui_boot_state'],4))[0],3)
        u.mem_write(symbols['gr2_ui_boot_state'],struct.pack('>I',1));self.assertEqual(event(0x6000100a),0);self.assertEqual(calls,[])

    def test_installed_ui_chain_restores_the_original_message_after_bootstrap_before_key_routing(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();u=runtime_machine(component('gr2','b01firm8'))
        u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_write(0xa0394950,bytes.fromhex(runtime['ui_event_hook_patch_hex']))
        message=0x50001000;u.mem_write(message,struct.pack('>3I',0x6000100a,7,9));calls=[]
        bootstrap=runtime['symbols']['gr2_ui_bootstrap'];raw=runtime['symbols']['gr2_settings_raw_event']
        def boundary(machine,address,size,unused):
            calls.append(['boot' if address==bootstrap else 'raw',machine.reg_read(r.UC_ARM_REG_R0)])
            machine.reg_write(r.UC_ARM_REG_R1,0xdeadbeef);machine.reg_write(r.UC_ARM_REG_R0,int(address==raw))
            machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in (bootstrap,raw):u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        saved=[0x45670000+i for i in range(8)]
        for i,value in enumerate(saved):u.reg_write(r.UC_ARM_REG_R4+i,value)
        self.assertEqual(self.call(u,0xa039494f,[0x50002000,message]),1)
        self.assertEqual(calls,[['boot',message],['raw',message]])
        self.assertEqual([u.reg_read(r.UC_ARM_REG_R4+i) for i in range(8)],saved)
        self.assertEqual(u.reg_read(r.UC_ARM_REG_SP),0x50018000)
        self.assertEqual(bytes(u.mem_read(message,12)),struct.pack('>3I',0x6000100a,7,9))

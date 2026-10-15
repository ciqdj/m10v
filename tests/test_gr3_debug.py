"""Bounded SD logger: execute real compiled ARM, mock only device facade/heap."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
from scripts.build_gr3_m10v_library import build

class DebugLogArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.manifest = build(Path(cls.tmp.name), debug_mode=True, debug_build_id=0x12345678)
        cls.code = (Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()

    def setUp(self):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.u.mem_map(0x53000000, 0x1200000)
        self.u.mem_write(self.manifest['base'], self.code)
        self.u.mem_map(0x55000000, 0x100000)
        self.files = {}; self.handles = {}; self.calls = []; self.available = True
        self.fail_write = False; self.heap_ok = True
        self.successful_opens = 0
        self.u.mem_write(0x55004014, struct.pack('<I', 0x55004200))
        self.u.mem_write(0x55004200, struct.pack('<I', 0x53900000))
        for index,address in [(7,0x53900100),(8,0x53900200),(9,0x53900300),(10,0x53900400)]:
            self.u.mem_write(0x53900000+index*4,struct.pack('<I',address))
        self.u.hook_add(UC_HOOK_CODE,self.services)

    def services(self,u,address,size,data):
        args=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        result=None
        if address==0x535847d8: result=0x55004000 if self.available else 0
        elif address==0x5320ad88: result=0x55005000
        elif address==0x5320ba9c: result=0x55068200
        elif address==self.manifest['base']+0xa0: result=77
        elif address==0x536af2a8:
            self.assertEqual(args[0],8192); result=0x55010000 if self.heap_ok else 0
        elif address==0x536af2e4: result=0
        elif address==0x53900100:
            name=bytes(u.mem_read(args[1],16)).split(b'\0')[0].decode()
            self.assertIn(name,('C:\\M10VMN0.BIN','C:\\M10VMN1.BIN','C:\\M10VCP0.BIN','C:\\M10VCP1.BIN'))
            self.assertIn(args[2],(0,1)); self.calls.append(('open',name,args[2]))
            result=int(args[2]==0 or name in self.files)
            if result:
                self.successful_opens += 1
                handle=len(self.handles)+1;self.handles[handle]=name
                u.mem_write(args[3],struct.pack('<I',handle))
                if args[2]==0:self.files[name]=b''
        elif address==0x53900200: self.calls.append(('close',args[1]));result=1
        elif address in (0x53900300,0x53900400):
            self.assertEqual(args[3],4096)
            name=self.handles[args[1]]
            if address==0x53900300:
                payload=self.files[name];result=int(len(payload)==4096)
                if result:u.mem_write(args[2],payload)
            else:
                payload=bytes(u.mem_read(args[2],args[3]))
                self.files[name]=payload[:128] if self.fail_write else payload
                result=int(not self.fail_write)
            self.calls.append(('read' if address==0x53900300 else 'write',name))
        if result is not None:
            u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

    def log(self,event=30,a=0x55005000,b=11,c=21,d=33):
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(event,a,b,c)):
            self.u.reg_write(reg,value)
        self.u.mem_write(0x550fe000,struct.pack('<I',d))
        self.u.reg_write(UC_ARM_REG_SP,0x550fe000);self.u.reg_write(UC_ARM_REG_LR,0x550ff000)
        self.u.emu_start(self.manifest['symbols']['m10v_debug_log'],0x550ff000,count=2000000)
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PC),0x550ff000)
        return self.u.reg_read(UC_ARM_REG_R0)

    def invoke(self,symbol,*args):
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):
            self.u.reg_write(reg,value)
        self.u.reg_write(UC_ARM_REG_SP,0x550fe000);self.u.reg_write(UC_ARM_REG_LR,0x550ff000)
        self.u.emu_start(self.manifest['symbols'][symbol],0x550ff000,count=3000000)
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PC),0x550ff000)
        return self.u.reg_read(UC_ARM_REG_R0)

    def test_focus_wrapper_records_real_slot_and_preserves_original_result(self):
        self.u.mem_write(0x55068200,b'\x15')
        self.assertEqual(self.invoke('m10v_menu_focus',0x55005000,11),77)
        records=self.decoded()['records']
        self.assertEqual([r['event'] for r in records],[30,31])
        self.assertEqual(records[0]['arguments'],[0x55005000,11,21,0])
        self.assertEqual(records[1]['arguments'][2],77)

    def test_capture_validation_failure_is_logged_and_preserved(self):
        self.assertEqual(self.invoke('m10v_capture_library',0),0xfffffffd)
        records=self.decoded()['records']
        self.assertEqual([r['event'] for r in records],[100,101])
        self.assertEqual(records[-1]['arguments'][1],0xfffffffd)

    def test_debug_capture_chain_restores_stock_arguments_flags_and_stack(self):
        registers=(UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,
                   UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,
                   UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12)
        values=list(range(13));values[4]=0
        for sp in (0x550fe000,0x550fe004):
            seen=[];cpsr=0x68050013
            def stock(u,address,size,data):
                if address==0x536abd28:
                    seen.append(address)
                    self.assertEqual([u.reg_read(r) for r in registers],values)
                    self.assertEqual(u.reg_read(UC_ARM_REG_SP),sp)
                    self.assertEqual(u.reg_read(UC_ARM_REG_CPSR)&0xff0f0000,cpsr&0xff0f0000)
                    u.reg_write(UC_ARM_REG_R0,99);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            hook=self.u.hook_add(UC_HOOK_CODE,stock)
            for r,v in zip(registers,values):self.u.reg_write(r,v)
            self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,0x550ff000)
            self.u.reg_write(UC_ARM_REG_CPSR,cpsr)
            self.u.emu_start(self.manifest['symbols']['m10v_chain_capture'],0x550ff000,count=3000000)
            self.assertEqual(seen,[0x536abd28]);self.assertEqual(self.u.reg_read(UC_ARM_REG_R0),99)
            self.u.hook_del(hook)

    def decoded(self):
        from scripts.read_gr3_debug_log import decode_logs
        return decode_logs(list(self.files.values()))

    def test_arm_writes_history_with_payload_build_identity_and_balanced_close(self):
        self.assertEqual(self.log(),1);self.assertEqual(self.log(31),1)
        result=self.decoded();records=result['records']
        self.assertEqual([r['event'] for r in records],[30,31])
        self.assertEqual(records[0]['arguments'],[0x55005000,11,21,33])
        self.assertEqual(result['build_ids'],['12345678'])
        self.assertEqual(sum(c[0]=='close' for c in self.calls),self.successful_opens)

    def test_bounded_ring_and_capture_channel_keep_separate_histories(self):
        for i in range(70):self.assertEqual(self.log(30,b=i),1)
        self.assertEqual(self.log(100),1)
        records=self.decoded()['records'];menu=[r for r in records if r['channel']=='menu']
        self.assertEqual(len(menu),63);self.assertEqual(menu[0]['arguments'][1],7)
        self.assertEqual(menu[-1]['sequence'],70)
        self.assertEqual(len([r for r in records if r['channel']=='capture']),1)

    def test_persisted_capture_settings_and_source_decode_after_reader_restart(self):
        self.assertEqual(self.log(112,a=1,b=202534,c=4,d=2),1)
        self.assertEqual(self.log(113,a=1,b=2,c=4,d=3),1)
        self.assertEqual(self.log(114,a=12168,b=9,c=128*96,d=216),1)
        from scripts.read_gr3_debug_log import decode_logs
        result=decode_logs(list(self.files.values()))
        settings=next(r for r in result['records'] if r['event']==112)
        self.assertEqual(settings['settings'],dict(slot=1,gain=6,spread=2,threshold=7,grain=1,soft=3,sequence=4,renderer_revision=2))
        energy=next(r for r in result['records'] if r['event']==114)
        self.assertEqual(energy['highlight_energy'],dict(maximum=12168,active_pixels=9,image_pixels=128*96,gate=216))
        source=next(r for r in result['records'] if r['event']==113)
        self.assertEqual(source['provenance'],dict(slot=1,source='migrated-v2',sequence=4,journal_namespace=3))

    def test_partial_write_preserves_previous_checkpoint(self):
        self.assertEqual(self.log(30),1);self.fail_write=True
        self.assertEqual(self.log(31),0)
        self.assertEqual([r['event'] for r in self.decoded()['records']],[30])

    def test_missing_card_oom_and_reentry_do_not_leave_guard_set(self):
        self.available=False;self.assertEqual(self.log(),0)
        self.assertEqual(self.u.mem_read(0x5506821f,1),b'\0')
        self.available=True;self.heap_ok=False;self.assertEqual(self.log(),0)
        self.assertEqual(self.u.mem_read(0x5506821f,1),b'\0')
        self.u.mem_write(0x5506821f,b'\1');before=list(self.calls)
        self.assertEqual(self.log(),0);self.assertEqual(self.calls,before)
        self.assertEqual(self.u.mem_read(0x5506821f,1),b'\1')
        self.assertEqual(self.log(100),0);self.assertEqual(self.calls,before)
        self.assertEqual(self.u.mem_read(0x5506821f,1),b'\1')

if __name__=='__main__':unittest.main()

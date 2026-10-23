import struct,unittest
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from scripts.build_gr3_menu_controls import build_menu_controls,MENU_ADDRESS

class DedicatedMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.code=build_menu_controls()
    def machine(self):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        for a,n in ((MENU_ADDRESS,4096),(0x5320b000,4096),(0x53584000,4096),(0x55000000,0x10000),(0x57000000,0x10000)):
            u.mem_map(a,n)
        u.mem_write(MENU_ADDRESS,self.code)
        u.mem_write(0x55000004,struct.pack('<I',0x55001000))
        u.mem_write(0x550011c0,b'\0')
        u.mem_write(0x55004000+0x199,bytes([0,8,0,0,0]))
        self.fs_calls=0
        def external(uc,a,size,data):
            if a==0x5320b31c:uc.reg_write(UC_ARM_REG_R0,0x55000000)
            elif a==0x535847d8:self.fs_calls+=1;uc.reg_write(UC_ARM_REG_R0,0)
            else:return
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,external)
        return u
    def call(self,u,op,arg=0,value=0):
        for r,v in ((UC_ARM_REG_R0,op),(UC_ARM_REG_R1,arg),(UC_ARM_REG_R2,value),(UC_ARM_REG_SP,0x5700fff0),(UC_ARM_REG_LR,0x57000000)):
            u.reg_write(r,v)
        u.emu_start(MENU_ADDRESS,0x57000000,count=200000)
        self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x57000000)
        self.assertEqual(u.reg_read(UC_ARM_REG_SP),0x5700fff0)
        return u.reg_read(UC_ARM_REG_R0)
    def test_retired_grain_cannot_write_or_enter_capture_from_legacy_record(self):
        u=self.machine();self.call(u,0,2)
        # Keep old packed record ABI, including formerly supported grain nibble.
        u.mem_write(0x55001b34,struct.pack('<I',0x32533))
        before=bytes(u.mem_read(0x55001b28,32));events=self.fs_calls
        self.assertEqual(self.call(u,2,0x55004000,(4<<8)|1),0)
        self.assertEqual(self.call(u,0,2),0x80040533)
        self.assertEqual(self.call(u,6),0x32533)
        self.assertEqual(bytes(u.mem_read(0x55001b28,32)),before)
        self.assertEqual(self.fs_calls,events)

    def test_defaults_and_record_pointer(self):
        u=self.machine()
        self.assertEqual(self.call(u,5),0x55001000)
        self.assertEqual(self.call(u,0,2),0x80040533)
        self.assertEqual([self.call(u,1,0x55004000,i) for i in range(4)],[3,3,5,2])
        self.assertEqual(self.fs_calls,1)
    def test_independent_sets_and_original_record_bytes(self):
        u=self.machine();original=bytes(u.mem_read(0x55001000,0xb28))
        self.call(u,2,0x55004000,8)
        self.assertEqual(self.call(u,1,0x55004000,0),8)
        u.mem_write(0x55004199,b'\1')
        self.assertEqual(self.call(u,1,0x55004000,0),3)
        self.call(u,2,0x55004000,(3<<8)|3)
        self.assertEqual(self.call(u,1,0x55004000,3),3)
        self.assertEqual(bytes(u.mem_read(0x55001000,0xb28)),original)
        u.mem_write(0x550011c0,b'\1')
        self.assertEqual(self.call(u,0,2),0x80070533)
    def test_invalid_fields_modes_and_busy_initialization_do_not_write(self):
        u=self.machine();self.call(u,0,2)
        original=bytes(u.mem_read(0x55001000,0xb48))
        for val in ((3<<8)|4,(4<<8)|8,9,(5<<8)|0):self.call(u,2,0x55004000,val)
        u.mem_write(0x5500419a,b'\7')
        self.call(u,2,0x55004000,7)
        self.assertEqual(bytes(u.mem_read(0x55001000,0xb48)),original)
        u.mem_write(0x55001b28,struct.pack('<I',1))
        before=bytes(u.mem_read(0x55001b28,32));self.assertEqual(self.call(u,0,2),0x80040533)
        self.assertEqual(bytes(u.mem_read(0x55001b28,32)),before)
    def filesystem(self,u,disk=None,partial=False):
        self.disk=disk;self.file_events=[]
        u.mem_map(0x53100000,4096);u.mem_map(0x53cd1000,4096)
        u.mem_write(0x55000014,struct.pack('<I',0x55000800));u.mem_write(0x55000800,struct.pack('<I',0x53cd1000))
        for offset,fn in ((28,0x53100100),(32,0x53100200),(36,0x53100300),(40,0x53100400)):
            u.mem_write(0x53cd1000+offset,struct.pack('<I',fn))
        def fs(uc,a,n,data):
            args=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            if a==0x535847d8:uc.reg_write(UC_ARM_REG_R0,0x55000000);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
            if a==0x53100100:
                self.assertEqual(bytes(uc.mem_read(args[1],16)).split(b'\0')[0],b'C:\\M10V8CFG.BIN')
                self.file_events.append(('open',args[2]));ok=args[2]==0 or self.disk is not None
                uc.mem_write(args[3],struct.pack('<I',7 if ok else 0));result=int(ok)
            elif a==0x53100200:self.file_events.append(('close',args[1]));result=1
            elif a==0x53100300:
                self.assertEqual(args[3],32);self.file_events.append(('read',32));uc.mem_write(args[2],self.disk[:16] if partial else self.disk);result=1
            elif a==0x53100400:
                self.assertEqual(args[3],32);self.file_events.append(('write',32));self.disk=bytes(uc.mem_read(args[2],32));result=1
            else:return
            uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,fs)
    def test_persisted_settings_reload_without_reading_during_steady_capture(self):
        u=self.machine();self.filesystem(u)
        self.call(u,2,0x55004000,(3<<8)|3)
        self.assertEqual(self.file_events,[('open',1),('open',0),('write',32),('close',7)])
        events=list(self.file_events)
        self.assertEqual(self.call(u,0,2),0x80070533)
        self.assertEqual(self.file_events,events)
        saved=self.disk;u=self.machine();self.filesystem(u,saved)
        self.assertEqual(self.call(u,1,0x55004000,3),3)
        self.assertIn(('read',32),self.file_events)
    def test_partial_and_bad_checksum_files_fall_back_without_stock_writes(self):
        u=self.machine();self.filesystem(u);self.call(u,2,0x55004000,8);saved=self.disk
        for partial,damaged in ((True,saved),(False,saved[:8]+bytes(4)+saved[12:])):
            with self.subTest(partial=partial):
                u=self.machine();prefix=bytes(u.mem_read(0x55001000,0xb28));self.filesystem(u,damaged,partial)
                self.assertEqual(self.call(u,1,0x55004000,0),3)
                self.assertEqual(bytes(u.mem_read(0x55001000,0xb28)),prefix)

"""Execute installed call-site patch through the complete original Still Make.
CPU emulation verifies ABI/state boundaries, not ISP hardware pixel quality.
"""
import hashlib,struct,tempfile,unittest
from unicorn import UC_PROT_READ,UC_PROT_EXEC,UC_HOOK_CODE
from unicorn import arm_const as A
from tests.test_gr3_isp_base import StockISP,ROOT,BASE
from scripts.build_gr3_isp_color_hook import build,SHA,SITE

def target(scale):
    return {'kind':'matrix-curves-post','matrix_q13':[8192,0,0,0,8192,0,0,0,8192],
            'post_q9':[512,0,0,0,512,0,0,0,512],'curves':[i*scale for i in range(256)]*3}

class InstalledColorHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
        cls.slots=[target(45+i) for i in range(5)]
        with tempfile.TemporaryDirectory() as d:cls.code,cls.manifest=build(d,cls.slots,cls.rom)
        cls.patched=bytearray(cls.rom);end=cls.manifest['base']-BASE+len(cls.code)
        cls.patched.extend(bytes(end-len(cls.patched)))
        off=cls.manifest['base']-BASE;cls.patched[off:off+len(cls.code)]=cls.code
        for p in cls.manifest['patches']:struct.pack_into('<I',cls.patched,p['address']-BASE,p['word'])
        cls.patched=bytes(cls.patched)

    def emulator(self,patched=True):
        rom=self.patched if patched else self.rom
        e=StockISP(rom);e.u.mem_protect(BASE,(len(rom)+65535)&~65535,UC_PROT_READ|UC_PROT_EXEC)
        return e

    def test_installed_all_five_slots_only_change_frame_banks(self):
        for tone in (12,18,19,20,21):
            with self.subTest(tone=tone):
                r=self.emulator(False);before,si,_=r.make(tone)
                e=self.emulator();after,esi,_=e.make(tone)
                diff=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
                self.assertGreater(len(diff),0)
                self.assertTrue(all(0x2688<=i<0x5088 for i in diff))
                self.assertEqual(esi,si);self.assertEqual(e.object,r.object)
                self.assertEqual(e.u.mem_read(0x55000000,0x3a080),r.u.mem_read(0x55000000,0x3a080))
                self.assertEqual(e.assertions,[])

    def test_standard_foreign_tones_stage_and_live_identity_unchanged(self):
        for tone,stage,live in [(11,1,False),(22,1,False),(12,0,False),(12,1,True)]:
            with self.subTest(tone=tone,stage=stage,live=live):
                r=self.emulator(False);a,b,_=r.make(tone,stage,live)
                e=self.emulator();c,d,_=e.make(tone,stage,live)
                self.assertEqual(c,a);self.assertEqual(d,b);self.assertEqual(e.object,r.object)

    def test_same_object_reuse_stock_recovery_and_no_curve_accumulation(self):
        e=self.emulator();first,_,st=e.make(12)
        r=self.emulator(False);r.make(12)
        obj=0x60000000;info=obj+0x1400
        gamma=struct.unpack('<I',e.u.mem_read(obj+0x17c,4))[0]
        self.assertEqual(bytes(e.u.mem_read(gamma,0x3240)),bytes(r.u.mem_read(gamma,0x3240)))
        for _ in range(3):
            e.call(0x536dd8f0,obj,info);r.call(0x536dd8f0,obj,info)
            self.assertEqual(bytes(e.u.mem_read(info,0x9000)),first)
            self.assertEqual(bytes(e.u.mem_read(gamma,0x3240)),bytes(r.u.mem_read(gamma,0x3240)))
        for em in (e,r):
            em.u.mem_write(st+0x77c,b'\x0b');em.call(0x536dd8f0,obj,info)
        self.assertEqual(bytes(e.u.mem_read(info,0x9000)),bytes(r.u.mem_read(info,0x9000)))
        self.assertEqual(bytes(e.u.mem_read(gamma,0x3240)),bytes(r.u.mem_read(gamma,0x3240)))

    def test_adapter_preserves_callee_saved_sp_and_original_gamma_return(self):
        exits=[]
        for patched in (False,True):
            e=self.emulator(patched);seen=[]
            def observe(u,at,size,data):
                regs=[getattr(A,'UC_ARM_REG_R'+str(i)) for i in range(13)]+[A.UC_ARM_REG_SP,A.UC_ARM_REG_LR]
                if at==SITE:seen.append([u.reg_read(x) for x in regs])
                if at==SITE+4:
                    after=[u.reg_read(x) for x in regs]
                    self.assertEqual(after[4:12],seen[-1][4:12])
                    self.assertEqual(after[13],seen[-1][13])
                    exits.append(after)
            e.u.hook_add(UC_HOOK_CODE,observe);e.make(12)
            self.assertEqual(len(seen),1)
        self.assertEqual(exits[0],exits[1])

    def test_builder_rejects_wrong_rom_unsupported_fits_and_invalid_targets(self):
        self.assertEqual(hashlib.sha256(self.rom).hexdigest(),SHA)
        with tempfile.TemporaryDirectory() as d:
            for slots,rom in [([target(45)]*5,self.rom[:-1]),([{'kind':'3d-lut-fit'}]*5,self.rom),([target(65)]*5,self.rom),([],self.rom)]:
                with self.assertRaises(ValueError):build(d,slots,rom)
        self.assertEqual(len(self.manifest['patches']),1)
        self.assertFalse(self.manifest['quality_equivalence_proven'])
        self.assertFalse(self.manifest['dynamic_sd_selection'])

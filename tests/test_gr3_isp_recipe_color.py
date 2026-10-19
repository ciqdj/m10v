"""Run installed Develop callback against real stock Still Make and decoder."""
import json,os,shutil,struct,subprocess,tempfile,unittest,zlib
from pathlib import Path
from unicorn import UC_PROT_READ,UC_PROT_EXEC,UC_HOOK_CODE
from unicorn import arm_const as A
from tests.test_gr3_isp_base import StockISP,ROOT,BASE
from scripts.build_gr3_isp_recipe_color import build,SITE
from scripts.build_gr3_m10v_library import FLAGS
from scripts.build_gr3_save_trace import sections

def library_fragment(directory,base=0x54150000):
    # Compile the exact production validator/table decoder, no mocks.
    text=(ROOT/'native/gr3/m10v_library.c').read_text()
    source='#include "'+str(ROOT/'native/gr3/m10v_library.h')+'"\n#include <stddef.h>\n#include "'+str(ROOT/'native/gr3/m10v_legacy_data.h')+'"\n'
    for a,b in [('static uint32_t checksum(', 'static void copy_state('),('int m10v_library_valid(', 'const char *m10v_library_name('),('int m10v_library_tables(', 'static int rounded(')]:source+=text[text.index(a):text.index(b)]
    directory=Path(directory);src=directory/'decoder.c';obj=directory/'decoder.o';elf=directory/'decoder.elf';ld=directory/'decoder.ld'
    src.write_text(source);ld.write_text('SECTIONS { . = '+hex(base)+'; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }')
    clang=os.environ.get('M10V_LLVM_CLANG') or '/opt/homebrew/opt/llvm/bin/clang'
    subprocess.run([clang,*FLAGS,'-c',str(src),'-o',str(obj)],check=True,capture_output=True)
    subprocess.run([shutil.which('ld.lld') or 'ld.lld','-m','armelf','-T',str(ld),str(obj),'-o',str(elf)],check=True,capture_output=True)
    data=elf.read_bytes();rows=sections(data);symbols={}
    for name,r in rows:
        if name=='.text':code=data[r[4]:r[4]+r[5]]
        if r[1]==2:
            strings_row=rows[r[6]][1];strings=data[strings_row[4]:strings_row[4]+strings_row[5]]
            for pos in range(r[4],r[4]+r[5],16):
                n,v,size,info,other,index=struct.unpack_from('<IIIBBH',data,pos)
                name=strings[n:].split(b'\0')[0].decode()
                if name.startswith('m10v_library_'):symbols[name]=v
    return base,code,symbols

def state(films=(34,35,36,37,38),sequence=7):
    data=bytearray(104);struct.pack_into('<IHHI',data,0,0x5630314d,4,104,sequence)
    for i,film in enumerate(films):struct.pack_into('<H6B',data,12+i*8,film,0,0,0,3,5,2)
    struct.pack_into('<I',data,100,zlib.crc32(data[:100]));return bytes(data)

class RecipeColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
        with tempfile.TemporaryDirectory() as d:
            cls.libbase,cls.libcode,cls.libsymbols=library_fragment(d)
            owner={'storage':{'color_offset':0x4a08,'color_bytes':1716,'extended_recipe_bytes':0x50f0},'patches':[{'address':0x53523e0c}]}
            cls.code,cls.manifest=build(d,cls.rom,cls.libsymbols,owner,observer=False)
        cls.candidate=bytearray(cls.rom)
        for at,code in ((cls.libbase,cls.libcode),(cls.manifest['base'],cls.code)):
            end=at-BASE+len(code)
            if end>len(cls.candidate):cls.candidate.extend(bytes(end-len(cls.candidate)))
            cls.candidate[at-BASE:end]=code
        for p in cls.manifest['patches']:cls.candidate[p['address']-BASE:p['address']-BASE+4]=bytes.fromhex(p['replacement_hex'])
        cls.candidate=bytes(cls.candidate)

    def fixture(self,tone=12,stage=0):
        e=StockISP(self.candidate);e.u.mem_protect(BASE,(len(self.candidate)+65535)&~65535,UC_PROT_READ|UC_PROT_EXEC)
        recipe=e.alloc(0x50f0);e.w32(recipe,0x53d0fc90);e.w32(recipe+0x4778,0x31545653)
        obj=e.cursor;e.make(tone,stage);info=obj+0x1400
        context=e.alloc(0x100);si=struct.unpack('<I',e.u.mem_read(info+0x82d0,4))[0]
        e.w32(context+0x30,recipe+0x1a8);e.w32(context+0x34,si)
        return e,recipe,obj,info,context,si

    def snapshot(self,e,recipe,data):
        at=e.alloc(104);e.u.mem_write(at,bytes(data))
        e.call(self.manifest['exports']['m10v_isp_frame_recipe_snapshot'],recipe,at)
        return e.u.reg_read(A.UC_ARM_REG_R0),at

    def callback(self,e,obj,info,context):
        u=e.u
        for i in range(13):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(i)),0x12340000+i)
        for r,v in ((0,obj),(1,info),(3,0x536dd8f0),(6,context)):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(r)),v)
        u.reg_write(A.UC_ARM_REG_SP,0x5effff00);u.reg_write(A.UC_ARM_REG_LR,0x53501d6c);u.reg_write(A.UC_ARM_REG_CPSR,0x13)
        before=[u.reg_read(getattr(A,'UC_ARM_REG_R'+str(i))) for i in range(4,12)]+[u.reg_read(A.UC_ARM_REG_SP)]
        u.emu_start(SITE,SITE+4,count=5000000)
        self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),SITE+4)
        self.assertEqual([u.reg_read(getattr(A,'UC_ARM_REG_R'+str(i))) for i in range(4,12)]+[u.reg_read(A.UC_ARM_REG_SP)],before)
        self.assertEqual(u.reg_read(A.UC_ARM_REG_LR),SITE+4)

    def status(self,e,recipe):return struct.unpack('<I',e.u.mem_read(recipe+0x4a08+12,4))[0]

    def test_actual_develop_callback_all_five_slots_stage0_and1(self):
        for stage in (0,1):
            for tone in (12,18,19,20,21):
                with self.subTest(stage=stage,tone=tone):
                    e,r,o,i,c,si=self.fixture(tone,stage)
                    before=bytes(e.u.mem_read(i,0x9000));shoot=bytes(e.u.mem_read(si,0x80000))
                    self.assertEqual(self.snapshot(e,r,state())[0],1)
                    self.callback(e,o,i,c)
                    self.assertEqual(self.status(e,r),2)
                    after=bytes(e.u.mem_read(i,0x9000));diff=[p for p,(a,b) in enumerate(zip(before,after)) if a!=b]
                    self.assertGreater(len(diff),0)
                    self.assertTrue(all(0x140<=p<0x152 or 0x12a0<=p<0x12b2 or 0x2688<=p<0x5088 for p in diff))
                    self.assertEqual(bytes(e.u.mem_read(si,0x80000)),shoot)
                    self.assertEqual(e.u.mem_read(r+0x4a08+28,12),bytes(12))

    def test_snapshot_survives_external_state_change_and_is_same_cpu_fallback_state(self):
        e,r,o,i,c,si=self.fixture();initial=state()
        result,source=self.snapshot(e,r,initial);self.assertEqual(result,1)
        e.u.mem_write(source,state((65,65,65,65,65),sequence=8))
        self.callback(e,o,i,c)
        out=e.alloc(104);e.call(self.manifest['exports']['m10v_isp_frame_recipe_state'],r,out)
        self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1);self.assertEqual(bytes(e.u.mem_read(out,104)),initial)
        selected=struct.unpack('<I',e.u.mem_read(r+0x4a08+16,4))[0];self.assertEqual(selected,7)

    def test_unsupported_3d_lut_and_wrong_si_leave_frame_stock(self):
        for mismatch in (False,True):
            e,r,o,i,c,si=self.fixture()
            self.assertEqual(self.snapshot(e,r,state((34,)*5 if mismatch else (66,)*5))[0],1)
            if mismatch:e.w32(c+0x34,si+64)
            before=bytes(e.u.mem_read(i,0x9000));self.callback(e,o,i,c)
            self.assertEqual(self.status(e,r),4 if mismatch else 6)
            self.assertEqual(bytes(e.u.mem_read(i,0x9000)),before)

    def test_invalid_state_and_foreign_recipe_do_not_overwrite_snapshot(self):
        e,r,o,i,c,si=self.fixture();self.assertEqual(self.snapshot(e,r,state())[0],1)
        before=bytes(e.u.mem_read(r+0x4a08,1716));bad=bytearray(state());bad[12]^=1
        self.assertEqual(self.snapshot(e,r,bad)[0],0);self.assertEqual(bytes(e.u.mem_read(r+0x4a08,1716)),before)
        e.w32(r,0x12345678);self.assertEqual(self.snapshot(e,r,state())[0],0)

    def test_busy_owner_rejects_reselection_and_same_tuning_recovers_standard(self):
        e,r,o,i,c,si=self.fixture();self.assertEqual(self.snapshot(e,r,state())[0],1)
        e.call(self.manifest['exports']['m10v_isp_frame_recipe_begin'],c,o,i)
        self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
        self.assertEqual(self.snapshot(e,r,state((65,)*5,sequence=9))[0],0)
        e.call(0x536dd8f0,o,i)
        e.call(self.manifest['exports']['m10v_isp_frame_recipe_finish'],c)
        self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
        # Make a fresh stock reference at identical allocation addresses.
        ref=StockISP(self.candidate);rr=ref.alloc(0x50f0);ref.make(12,0)
        for em in (e,ref):
            em.u.mem_write(si+0x77c,b'\x0b');em.call(0x536dd8f0,o,i)
        self.assertEqual(bytes(e.u.mem_read(i,0x9000)),bytes(ref.u.mem_read(i,0x9000)))

    def test_owner_factory_is_required_and_no_snapshot_passes_stock(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):build(d,self.rom,self.libsymbols,{})
        e,r,o,i,c,si=self.fixture();before=bytes(e.u.mem_read(i,0x9000));self.callback(e,o,i,c)
        self.assertEqual(bytes(e.u.mem_read(i,0x9000)),before)

class ObserverProducerTests(unittest.TestCase):
    fixture=RecipeColorTests.fixture
    snapshot=RecipeColorTests.snapshot
    callback=RecipeColorTests.callback
    status=RecipeColorTests.status
    @classmethod
    def setUpClass(cls):
        cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
        with tempfile.TemporaryDirectory() as d:
            cls.libbase,cls.libcode,cls.libsymbols=library_fragment(d)
            cls.libsymbols['m10v_camera_library_load']=0x54140000
            owner={'storage':{'color_offset':0x4a08,'color_bytes':1716,'extended_recipe_bytes':0x50f0},'patches':[{'address':0x53523e0c}]}
            cls.code,cls.manifest=build(d,cls.rom,cls.libsymbols,owner,observer=True,producer_snapshot=True)
        cls.candidate=bytearray(cls.rom)
        for at,code in ((cls.libbase,cls.libcode),(cls.manifest['base'],cls.code)):
            end=at-BASE+len(code)
            if end>len(cls.candidate):cls.candidate.extend(bytes(end-len(cls.candidate)))
            cls.candidate[at-BASE:end]=code
        for p in cls.manifest['patches']:cls.candidate[p['address']-BASE:p['address']-BASE+4]=bytes.fromhex(p['replacement_hex'])
        cls.candidate=bytes(cls.candidate)

    def producer(self,e,recipe,site,data):
        owner=e.alloc(0x1000);e.w32(owner+0xf0,recipe);calls=[]
        def load(u,at,size,userdata):
            if at==self.libsymbols['m10v_camera_library_load']:
                calls.append(at);u.mem_write(u.reg_read(A.UC_ARM_REG_R0),data)
                u.reg_write(A.UC_ARM_REG_R0,0);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
        hook=e.u.hook_add(UC_HOOK_CODE,load)
        u=e.u
        for r in range(13):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(r)),0x12340000+r)
        u.reg_write(A.UC_ARM_REG_R4,owner);u.reg_write(A.UC_ARM_REG_SP,0x5effff00);u.reg_write(A.UC_ARM_REG_LR,0x5e000000)
        u.reg_write(A.UC_ARM_REG_CPSR,0xa80f0013)
        regs=[getattr(A,'UC_ARM_REG_R'+str(r)) for r in range(13)]+[A.UC_ARM_REG_SP,A.UC_ARM_REG_LR,A.UC_ARM_REG_CPSR]
        expected=[u.reg_read(r) for r in regs];expected[2]=recipe
        for n in range(8,16):u.reg_write(getattr(A,'UC_ARM_REG_D'+str(n)),0x1122334455667788+n)
        u.emu_start(site,site+4,count=100000)
        self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),site+4)
        self.assertEqual([u.reg_read(r) for r in regs],expected)
        self.assertEqual([u.reg_read(getattr(A,'UC_ARM_REG_D'+str(n))) for n in range(8,16)],[0x1122334455667788+n for n in range(8,16)])
        u.hook_del(hook)
        return calls

    def test_both_post_mutex_producers_snapshot_once_and_preserve_original_abi(self):
        for site in (0x5351aed4,0x5351b068):
            with self.subTest(site=hex(site)):
                e,r,o,i,c,si=self.fixture();initial=state((66,67,68,33,34))
                self.assertEqual(len(self.producer(e,r,site,initial)),1)
                self.assertEqual(len(self.producer(e,r,site,state())),0)
                out=e.alloc(104);e.call(self.manifest['exports']['m10v_isp_frame_recipe_state'],r,out)
                self.assertEqual(bytes(e.u.mem_read(out,104)),initial)

    def test_source_recipe_is_followed_and_foreign_destination_is_not_marked_observed(self):
        e,source,o,i,c,si=self.fixture()
        destination=e.alloc(0x50f0);e.w32(destination,0x53d0fc90);e.w32(destination+0x4778,0x31545653)
        self.assertEqual(self.snapshot(e,source,state(sequence=7))[0],1)
        self.assertEqual(self.snapshot(e,destination,state(sequence=9))[0],1)
        # C can reside within the destination recipe while C+30 names source.
        actual_context=destination+0x970
        e.w32(actual_context+0x30,source+0x1a8);e.w32(actual_context+0x34,si)
        before=bytes(e.u.mem_read(i,0x9000));self.callback(e,o,i,actual_context)
        self.assertEqual(self.status(e,source),7)
        self.assertEqual(self.status(e,destination),1)
        self.assertEqual(struct.unpack('<I',e.u.mem_read(source+0x4a08+16,4))[0],7)
        self.assertEqual(struct.unpack('<I',e.u.mem_read(destination+0x4a08+16,4))[0],9)
        self.assertEqual(bytes(e.u.mem_read(i,0x9000)),before)

    def test_observer_all_slots_and_3d_lut_remain_byte_identical_to_stock(self):
        for tone in (12,18,19,20,21):
            e,r,o,i,c,si=self.fixture(tone)
            self.assertEqual(len(self.producer(e,r,0x5351b068,state((66,67,68,33,34)))),1)
            before=bytes(e.u.mem_read(i,0x9000))
            for n in range(8,16):e.u.reg_write(getattr(A,'UC_ARM_REG_D'+str(n)),0x1122334455667788+n)
            self.callback(e,o,i,c)
            self.assertEqual(self.status(e,r),7)
            self.assertEqual(bytes(e.u.mem_read(i,0x9000)),before)
            self.assertEqual([e.u.reg_read(getattr(A,'UC_ARM_REG_D'+str(n))) for n in range(8,16)],[0x1122334455667788+n for n in range(8,16)])
        self.assertEqual(len(self.manifest['patches']),3)
        self.assertTrue(self.manifest['observer'])
        self.assertTrue(self.manifest['snapshot_ingress_installed'])

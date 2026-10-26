"""Execute actual candidate menu + journal + renderer dispatch on ARM."""
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_EXEC
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[1]
class UniversalHalationArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=Path(os.environ.get('M10V_HALATION_CANDIDATE',ROOT/'builds/gr3-universal-halation-20261026/candidate'))
        cls.manifest=json.loads((folder/'M10V-runtime-manifest.json').read_text());cls.code=(folder/'M10V-runtime-arm.bin').read_bytes()
        assert cls.manifest['universal_halation'] is True
    def machine(self):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);base=self.manifest['base'];n=(len(self.code)+4095)&~4095
        u.mem_map(base,n);u.mem_write(base,self.code);u.mem_protect(base,n,UC_PROT_READ|UC_PROT_EXEC)
        u.mem_map(0x55000000,0x100000);u.mem_map(0x53825000,0x4000);u.mem_map(0x5339e000,0x2000);u.mem_map(0x53396000,0x2000)
        u.mem_write(0x55004008,struct.pack('<I',0x55004100));u.mem_write(0x55004100,struct.pack('<I',0x55004200));u.mem_write(0x55004220,b'\1')
        self.files={};self.store_fails=False;self.slider=[]
        def service(uc,address,size,data):
            if address==0x53828014:result=0x55004000
            elif address in (0x53825648,0x53825fa8):
                _,name,n,buffer=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
                name=bytes(uc.mem_read(name,12)).split(b'\0')[0].decode();result=0
                if address==0x53825fa8 and not self.store_fails:self.files[name]=bytes(uc.mem_read(buffer,n));result=1
                elif address==0x53825648 and name in self.files and len(self.files[name])==n:uc.mem_write(buffer,self.files[name]);result=1
            elif address==0x5339ee0c:self.slider.append(uc.reg_read(UC_ARM_REG_R1));result=0
            elif address==0x53396f80:result=0
            else:return
            uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,service);return u
    def call(self,u,name,*args):
        sp=0x550fe000;stop=0x550ff000
        for r,a in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(r,a)
        for i,a in enumerate(args[4:]):u.mem_write(sp+4*i,struct.pack('<I',a))
        u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop)
        u.emu_start(self.manifest['symbols'][name],stop,count=10000000)
        self.assertEqual(u.reg_read(UC_ARM_REG_PC),stop);return u.reg_read(UC_ARM_REG_R0)
    def ui(self,u,slot=0):
        ui=0x55007000;u.mem_write(ui+0x198,bytes([25+slot,0,0,0,0,0,0,0]));return ui
    def state(self,u):
        p=0x55008000;self.call(u,'m10v_camera_library_load',p);return bytes(u.mem_read(p,184))
    def test_real_menu_selects_modes_keeps_per_film_parameters_and_reloads_journal(self):
        u=self.machine();ui=self.ui(u);initial=self.state(u)
        self.assertEqual(self.call(u,'m10v_detail_control',1,ui,4),0)
        self.assertEqual(self.call(u,'m10v_detail_control',2,ui,4*256+1),1)
        on=self.state(u);self.assertEqual(on[19],4);self.assertEqual(on[16],3)
        self.assertEqual(on[20:92],initial[20:92])
        self.assertEqual(self.call(u,'m10v_detail_control',2,ui,7),1)
        self.assertEqual(self.state(u)[19],4,'gain edit must preserve selected mode')
        self.assertEqual(self.call(u,'m10v_detail_control',2,ui,4*256+2),1)
        self.assertEqual(self.call(u,'m10v_detail_control',1,ui,4),2)
        self.assertEqual(self.state(u)[19],5)
        self.assertEqual(self.call(u,'m10v_detail_control',2,ui,4*256),1)
        self.assertEqual(self.state(u)[19],6)
        self.assertTrue(any(name.startswith('M10V6') for name in self.files))
        other=self.ui(u,1);self.assertEqual(self.call(u,'m10v_detail_control',1,other,4),0)
    def test_old_nonzero_journal_stays_off_and_save_failure_restores_slider(self):
        u=self.machine();ui=self.ui(u);s=bytearray(self.state(u));s[16]=8;s[19]=2
        import zlib
        struct.pack_into('<I',s,180,zlib.crc32(s[:180]));self.files['M10V6A.bin']=bytes(s)
        self.assertEqual(self.call(u,'m10v_detail_control',1,ui,4),0)
        u.mem_write(ui+0x164,struct.pack('<I',0x55009000));self.store_fails=True
        before=dict(self.files);self.assertEqual(self.call(u,'m10v_detail_control',2,ui,4*256+2),0)
        self.assertEqual(self.files,before);self.assertEqual(self.slider,[0])
    def test_mode_range_validation_and_reset_off(self):
        u=self.machine();ui=self.ui(u)
        self.assertEqual(self.call(u,'m10v_detail_control',2,ui,4*256+3),0)
        self.assertEqual(self.call(u,'m10v_detail_control',2,ui,4*256+1),1)
        self.assertEqual(self.call(u,'m10v_detail_control',7,ui,0),1)
        self.assertEqual(self.call(u,'m10v_detail_control',1,ui,4),0)
    def capture(self,profile=4,gain=4,custom=False,allocation=True):
        from unicorn.arm_const import UC_ARM_REG_C1_C0_2,UC_ARM_REG_FPEXC
        u=self.machine();u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
        for page in (0x536af000,0x5383c000):u.mem_map(page,4096)
        state=0x55008000;self.state(u)
        if custom:self.assertEqual(self.call(u,'m10v_camera_library_select_custom',state,0,79,20),0)
        self.assertEqual(self.call(u,'m10v_camera_library_halation',state,0,gain,3,5,profile),0)
        completed=self.manifest['capture_lifecycle']['snapshot']['exports']['m10v_isp_frame_recipe_completed']
        self.allocations=[];self.frees=[];self.cache=[]
        def boundary(uc,at,size,data):
            if at==0x536af2a8:self.allocations.append(uc.reg_read(UC_ARM_REG_R0));value=0x550b0000 if allocation else 0
            elif at==0x536af2e4:self.frees.append(uc.reg_read(UC_ARM_REG_R0));value=0
            elif at==0x5383c8a8:self.cache.append(uc.reg_read(UC_ARM_REG_R0));value=0
            elif at==completed:value=1
            elif custom and at==self.manifest['symbols']['m10v_sd_camera_custom_record']:
                out=uc.reg_read(UC_ARM_REG_R2);uc.mem_write(out,self.custom_record);value=1
            else:return
            uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,boundary)
        recipe,request,shooting=0x55070000,0x55076000,0x55078000
        for offset,val in ((0x5c,request),(0x60,0x60000000),(0x230,0x55075000),(0x44c8,shooting)):u.mem_write(recipe+offset,struct.pack('<I',val))
        u.mem_write(0x55075000,struct.pack('<HH',6112,4064))
        context=bytearray(0x60);struct.pack_into('<I',context,0,0x53d0fbe0)
        for offset,val in ((0x30,recipe+0x1a8),(0x34,shooting),(0x38,request),(0x3c,recipe+0xb0),(0x48,recipe+0x110),(0x4c,recipe+0x130)):struct.pack_into('<I',context,offset,val)
        u.mem_write(recipe+0x9b8,bytes(context));u.mem_write(request,struct.pack('<I',0x53d0fe60));u.mem_write(request+12,b'\1\1')
        u.mem_write(shooting+0x77c,b'\31');u.mem_write(recipe+0x140,b'\1')
        for desc,y,c in ((recipe+0xb0,0x55010000,0x55020000),(recipe+0x110,0x55090000,0x550a0000)):
            u.mem_write(desc,struct.pack('<4I8H',1,y,c,0,128,96,136,96,0,0,2,0))
        y=bytearray([64]*(136*96+32));uv=bytes([128])*len(y);y[48*136+64:48*136+66]=b'\xff\xff'
        u.mem_write(0x55010000,bytes(y));u.mem_write(0x55020000,uv)
        result=self.call(u,'m10v_capture_library',recipe+0x9b8)
        return result,bytes(u.mem_read(0x55010000,len(y))),bytes(y)
    def test_actual_capture_allocates_spatial_scratch_only_for_explicit_mode(self):
        for profile in (2,4,5,6):
            result,after,before=self.capture(profile)
            self.assertEqual(result,0)
            film=int.from_bytes(bytes.fromhex(self.manifest['initial_state_hex'])[12:14],'little')
            planes=6 if profile==4 and film in (33,67) else 4
            self.assertEqual(self.allocations,[] if profile in (2,6) else [planes*128*96])
            self.assertEqual(self.frees,[] if profile in (2,6) else [0x550b0000])
            if profile in (2,6):self.assertEqual(after,before);self.assertEqual(self.cache,[])
            else:self.assertNotEqual(after,before)
    def test_actual_custom_capture_separates_lut_record_from_spatial_workspace(self):
        import subprocess
        js="import{parseCustomCube}from'./node/gr3-custom-lut.mjs';import{buildSdFilmPack}from'./node/gr3-sd-film-pack.mjs';const cube='LUT_3D_SIZE 2\\n0 0 0\\n1 0 0\\n0 1 0\\n1 1 0\\n0 0 1\\n1 0 1\\n0 1 1\\n1 1 1\\n';process.stdout.write(buildSdFilmPack([],[parseCustomCube(Buffer.from(cube),'test.cube','TEST')]).subarray(4096));"
        self.custom_record=subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT)
        for profile in (4,5):
            result,after,before=self.capture(profile,custom=True)
            self.assertEqual(result,0);self.assertNotEqual(after,before)
            self.assertEqual(self.allocations,[12288+4*128*96]);self.assertEqual(self.frees,[0x550b0000])
    def test_allocation_failure_keeps_pixel_planes_unchanged(self):
        result,after,before=self.capture(4,allocation=False)
        self.assertEqual(result,0xfffffffa);self.assertEqual(after,before);self.assertEqual(self.cache,[])

if __name__=='__main__':unittest.main()

"""Streamed native SD operations execute real GR II pool and file wrappers."""
import struct
import subprocess
import unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import ROOT,component

class Gr2SdTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    call=runtime_tests.Gr2RuntimeBuildTests.call

    def test_native_custom_install_and_reload_execute_original_file_wrappers_and_release_all_pool_storage(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        import zlib
        report=self.build();self.assertIn('gr2_sd_install',report['symbols']);self.assertIn('gr2_sd_custom_record',report['symbols'])
        pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack([],[{name:'Native LUT',rgb:Buffer.alloc(6591,83),sha256:'a'.repeat(64)}]));"],cwd=ROOT)
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(report['base'],bytes.fromhex(report['runtime_hex']));u.mem_map(0x52000000,0x2000);u.mem_map(0x53000000,0x4000)
        table=0x50007000;u.mem_write(0xa00b5bfe,struct.pack('>H',1));u.mem_write(0xa00b5be0,struct.pack('>I',table));u.mem_write(table,struct.pack('>h',-2));self.call(u,0xa0024bcb,[])
        word=lambda p:struct.unpack('>I',u.mem_read(p,4))[0]
        free=lambda:word(word(table+4)+12)*word(table+20)
        before=free();metadata_pool=0x5000c000;u.mem_write(0xa00c2c6c+28,struct.pack('>I',metadata_pool))
        files={'H:/M10V/FILMS.M10':pack};tokens={};metadata=[];closed=[];freed=[];writes=[];events=[]
        def string(uc,p):return bytes(uc.mem_read(p,32)).split(b'\0',1)[0].decode()
        def boundary(uc,address,size,unused):
            a,b,c,d=[uc.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3)];value=0
            events.append((hex(address),hex(a),hex(b),c,hex(d)))
            if address==0xa0065324:
                path,mode=string(uc,a),string(uc,b);self.assertIn(mode,('r','w'))
                if mode=='w' or path in files:
                    value=0x55000000+len(closed)*32;tokens[value]=[path,0]
                    if mode=='w':files[path]=b'';writes.append(path)
            elif address==0xa0024c3c:
                self.assertEqual((a,b),(metadata_pool,0x38));value=0x50009000+len(metadata)*64;metadata.append(value)
            elif address==0xa0024d76:
                self.assertEqual(a,metadata_pool);self.assertIn(b,metadata);self.assertEqual(word(b),0);freed.append(b)
            elif address==0xa00653a0:
                self.assertIn(a,tokens);self.assertEqual(c,0);origin=word(uc.reg_read(r.UC_ARM_REG_SP));self.assertIn(origin,(0,2));tokens[a][1]=len(files[tokens[a][0]])+d if origin==2 else d
            elif address==0xa0065318:uc.mem_write(b,struct.pack('>2I',0,tokens[a][1]))
            elif address==0xa0065386:
                self.assertEqual(b,1);path,position=tokens[d];data=files[path][position:position+c];uc.mem_write(a,data);tokens[d][1]+=len(data);value=len(data)
            elif address==0xa0065428:
                self.assertEqual(c,1);path,position=tokens[d];data=bytes(uc.mem_read(a,b));files[path]=files[path][:position]+data+files[path][position+b:];tokens[d][1]+=b;value=1
            elif address==0xa00652f0:value=int(tokens[a][1]>=len(files[tokens[a][0]]))
            elif address==0xa00652e2:self.assertIn(a,tokens);tokens.pop(a);closed.append(a)
            elif address==0xa00652ce:value=31
            elif address==0xa00267ba:value=1
            elif address in (0xa002b0ee,0xa0027360,0xa00273a4,0xa00a2058,0xa0039de4):value=0
            else:self.fail('original file/pool assertion')
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        for address in (0xa0065324,0xa0024c3c,0xa0024d76,0xa00653a0,0xa0065318,0xa0065386,0xa0065428,0xa00652f0,0xa00652e2,0xa00652ce,0xa002b0ee,0xa0027360,0xa00273a4,0xa00a2058,0xa00267ba,0xa0039de4,0xa0039f9c,0xa003a01a):u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        self.call(u,report['symbols']['m10v_library_init'],[0x50001000]);state=bytearray(u.mem_read(0x50001000,104));struct.pack_into('>I',state,8,10);struct.pack_into('>I',state,100,zlib.crc32(state[:100]));u.mem_write(0x50001000,bytes(state));self.call(u,report['symbols']['gr2_state_encode'],[0x50001000,0x50002000]);files['H:/M10V5A.bin']=bytes(u.mem_read(0x50002000,104))
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_catalog_open'],[0x52000000]),1,str(events))
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_install'],[0x52000000,0,79,0]),0,str((writes,[(path,len(data)) for path,data in files.items()],events[-15:])))
        self.assertEqual(writes,['H:/M10VC00.bin','H:/M10V5B.bin'])
        self.assertEqual(self.call(u,report['symbols']['gr2_load_state'],[0x50001000]),1)
        self.assertEqual(struct.unpack('>H',u.mem_read(0x5000100c,2))[0],79);self.assertEqual(bytes(u.mem_read(0x5000103e,1)),b'\x01')
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_custom_record'],[0x50001000,0,0x53000000,12288]),1)
        self.assertEqual(bytes(u.mem_read(0x53000000,12288)),pack[4096:]);self.assertEqual(tokens,{})
        u.mem_write(0xa00b5bf8,struct.pack('>h',2));u.mem_write(0xa00b5bd4,struct.pack('>I',0x50006c00))
        for i in range(2):u.mem_write(0x50006c00+14*i,struct.pack('>h',-2))
        u.mem_write(0xa06b6de0,b'\1');u.mem_write(0xa06b6de3,b'\1');u.mem_write(0xa00c22c0,struct.pack('>h',1))
        task=0xa05f5c28+68;u.mem_write(task+8,struct.pack('>2h',-1,-1));u.mem_write(task+24,struct.pack('>3h',20,0,20))
        self.assertIn('gr2_settings_backend_bind',report['symbols'])
        u.mem_map(0x54000000,0x2000);ops=0x50004000;page=0x50003000
        self.assertEqual(self.call(u,report['symbols']['gr2_settings_backend_bind'],[0x54000000,ops]),1)
        self.assertEqual(self.call(u,report['symbols']['m10v_settings_open'],[page,ops,1]),0)
        self.call(u,report['symbols']['m10v_settings_key'],[page,ops,4])
        self.assertEqual(word(page+104),2);self.assertEqual(word(page+120),79)
        self.assertEqual(self.call(u,report['symbols']['gr2_configuration_read'],[0x50005000]),1)
        self.assertEqual(bytes(u.mem_read(0x50005000,104)),bytes(u.mem_read(page,104)))
        self.call(u,report['symbols']['m10v_settings_key'],[page,ops,5])
        self.assertEqual(word(page+104),1)
        self.assertEqual(self.call(u,report['symbols']['m10v_settings_open'],[page,ops,3]),0)
        count=len(writes)
        for key in (4,1,5):self.call(u,report['symbols']['m10v_settings_key'],[page,ops,key])
        self.assertEqual(word(page+104),3);self.assertEqual(len(writes),count)
        for key in (4,1,4):self.call(u,report['symbols']['m10v_settings_key'],[page,ops,key])
        self.assertEqual(word(page+104),3);self.assertEqual(writes[-1],'H:/M10V5A.bin')
        self.assertEqual(self.call(u,report['symbols']['gr2_load_state'],[0x50001000]),1);self.assertEqual(bytes(u.mem_read(0x50001034,1)),b'\x01')
        for key in (3,3,3,3,4,1,4):self.call(u,report['symbols']['m10v_settings_key'],[page,ops,key])
        self.assertEqual(self.call(u,report['symbols']['gr2_load_state'],[0x50001000]),1);self.assertEqual(word(0x50001060),1)
        self.assertEqual(self.call(u,report['symbols']['gr2_configuration_read'],[0x50005000]),1)
        committed=bytes(u.mem_read(0x50001000,104));self.assertEqual(bytes(u.mem_read(0x50005000,104)),committed)
        files['H:/M10VC00.bin']=b'bad snapshot'
        self.assertEqual(self.call(u,report['symbols']['gr2_configuration_reload'],[]),0)
        self.assertEqual(self.call(u,report['symbols']['gr2_configuration_read'],[0x50005000]),1)
        self.assertEqual(bytes(u.mem_read(0x50005000,104)),committed)
        self.assertEqual(self.call(u,report['symbols']['gr2_configuration_clear'],[]),1)
        self.assertEqual(len(metadata),len(closed));self.assertEqual(len(metadata),len(freed));self.assertEqual(free(),before)

    def test_frozen_custom_install_commits_journal_only_after_verified_inactive_snapshot(self):
        from unicorn import UC_HOOK_CODE,arm_const as r
        import zlib
        report=self.build();self.assertIn('gr2_pack_install',report['symbols'])
        u=runtime_tests.Gr2RuntimeBuildTests.machine(self,report);u.mem_map(0x51000000,0x2000);u.mem_map(0x52000000,0x8000)
        pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack([],[{name:'Install LUT',rgb:Buffer.alloc(6591,83),sha256:'a'.repeat(64)}]));"],cwd=ROOT)
        files={};writes=[];fail={'journal':False};storage=0x50000000;pack_io=0x50000008;state=0x50001000;wire=0x50002000;manifest=0x51000000;work=0x52000000
        u.mem_write(storage,struct.pack('>4I',0x5001d000,0x5001d004,0x5001d008,0x5001d00c))
        def boundary(uc,address,size,unused):
            a,b,c,d=[uc.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3)];path=bytes(uc.mem_read(a,32)).split(b'\0',1)[0].decode();value=0
            if address==0x5001d000:
                data=files.get(path,b'')[:c];uc.mem_write(b,data);value=len(data)
            elif address==0x5001d004:
                value=13 if fail['journal'] and 'M10V5' in path else c;files[path]=bytes(uc.mem_read(b,value));writes.append(path)
            elif address==0x5001d008:
                self.assertEqual(path,'H:/M10V/FILMS.M10');uc.mem_write(b,struct.pack('>I',len(pack)));value=1
            else:
                self.assertEqual(path,'H:/M10V/FILMS.M10');data=pack[b:b+d];uc.mem_write(c,data);value=len(data)
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,boundary,begin=0x5001d000,end=0x5001d00c)
        self.call(u,report['symbols']['m10v_library_init'],[state]);value=bytearray(u.mem_read(state,104));struct.pack_into('>I',value,8,10);struct.pack_into('>I',value,100,zlib.crc32(value[:100]));u.mem_write(state,bytes(value));self.call(u,report['symbols']['gr2_state_encode'],[state,wire]);files['H:/M10V5A.bin']=bytes(u.mem_read(wire,104))
        self.assertEqual(self.call(u,report['symbols']['gr2_pack_manifest_load'],[pack_io,manifest,work]),1)
        def install():
            u.mem_write(0x50018000,struct.pack('>3I',79,0,work))
            return self.call(u,report['symbols']['gr2_pack_install'],[pack_io,storage,manifest,0])
        fail['journal']=True;self.assertEqual(install(),0xfffffffe)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[storage,state]),1)
        self.assertEqual(struct.unpack('>H',u.mem_read(state+12,2))[0],34)
        self.assertEqual(writes,['H:/M10VC00.bin','H:/M10V5B.bin'])
        fail['journal']=False;writes.clear();self.assertEqual(install(),0)
        self.assertEqual(writes,['H:/M10V5B.bin'])
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[storage,state]),1)
        self.assertEqual(struct.unpack('>H',u.mem_read(state+12,2))[0],79);self.assertEqual(bytes(u.mem_read(state+62,1)),b'\x01')
        writes.clear();pack=pack[:4096]+bytes([pack[4096]^1])+pack[4097:]
        self.assertNotEqual(install(),0);self.assertEqual(writes,[])
        self.assertEqual(files['H:/M10VC00.bin'],subprocess.check_output(['node','--input-type=module','-e',"import {customFilmRecord} from './node/gr3-sd-film-pack.mjs';process.stdout.write(customFilmRecord({name:'Install LUT',rgb:Buffer.alloc(6591,83)},79));"],cwd=ROOT))

    def test_native_sd_fetch_uses_real_pool_and_stock_file_wrappers_without_retained_handles(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();u=runtime_machine(component('gr2','b01firm8'));u.mem_write(report['base'],bytes.fromhex(report['runtime_hex']))
        pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack());"],cwd=ROOT)
        table=0x50007000;u.mem_write(0xA00B5BFE,struct.pack('>H',1));u.mem_write(0xA00B5BE0,struct.pack('>I',table));u.mem_write(table,struct.pack('>h',-2))
        self.call(u,0xA0024BCB,[])
        word=lambda p:struct.unpack('>I',u.mem_read(p,4))[0]
        free=lambda:word(word(table+4)+12)*word(table+20)
        before=free();pool=0x5000C000;u.mem_write(0xA00C2C6C+28,struct.pack('>I',pool))
        tokens={};handles=[];closed=[];freed=[];requests=[];behavior={'no_card':False,'corrupt':False}
        def string(uc,p):return bytes(uc.mem_read(p,32)).split(b'\0',1)[0].decode()
        def boundary(uc,address,size,context):
            a,b,c,d=[uc.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3)];value=0
            if address==0xA0065324:
                self.assertEqual(string(uc,a),'H:/M10V/FILMS.M10');self.assertEqual(string(uc,b),'r')
                if not behavior['no_card']:
                    value=0x5000B000+len(closed)*32;tokens[value]=0
            elif address==0xA0024C3C:
                self.assertEqual((a,b),(pool,0x38));value=0x50009000+len(handles)*64;handles.append(value)
            elif address==0xA0024D76:
                self.assertEqual(a,pool);self.assertIn(b,handles);self.assertEqual(bytes(uc.mem_read(b,4)),bytes(4));freed.append(b)
            elif address==0xA00653A0:
                self.assertIn(a,tokens);self.assertEqual(c,0)
                origin=word(uc.reg_read(r.UC_ARM_REG_SP));self.assertIn(origin,(0,2));tokens[a]=len(pack)+d if origin==2 else d
            elif address==0xA0065318:uc.mem_write(b,struct.pack('>2I',0,tokens[a]))
            elif address==0xA0065386:
                self.assertEqual(b,1);self.assertIn(d,tokens);position=tokens[d]
                payload=pack[position:position+c]
                if behavior['corrupt'] and position>=4096 and payload:payload=bytes([payload[0]^1])+payload[1:]
                uc.mem_write(a,payload);tokens[d]+=len(payload);value=len(payload);requests.append((position,c))
            elif address==0xA00652F0:value=int(tokens[a]>=len(pack))
            elif address==0xA00652E2:self.assertIn(a,tokens);tokens.pop(a);closed.append(a)
            elif address==0xA00652CE:value=31
            elif address==0xA00267BA:value=1
            elif address in (0xA0039F9C,0xA003A01A):self.fail('stock FILE assertion')
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        for address in (0xA002B0EE,0xA0027360,0xA00273A4,0xA00A2058,0xA0065324,0xA0024C3C,0xA0024D76,0xA00653A0,0xA0065318,0xA0065386,0xA00652F0,0xA00652E2,0xA00652CE,0xA00267BA,0xA0039DE4,0xA0039F9C,0xA003A01A):
            u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_item'],[0]),33)
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_record'],[0,33,0x50004000,12288]),33)
        self.assertEqual(bytes(u.mem_read(0x50004000,12288)),pack[4096:16384])
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_catalog_name'],[0,33,0x50001000,24]),1)
        self.assertEqual(bytes(u.mem_read(0x50001000,24)).split(b'\0',1)[0],pack[4112:4136].split(b'\0',1)[0])
        manifest=0x50010000
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_catalog_open'],[manifest]),1)
        frozen=bytes(u.mem_read(manifest,4108))
        u.mem_write(0x50018000,struct.pack('>I',12288))
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_frozen_record'],[manifest,0,33,0x50004000]),33)
        self.assertEqual(bytes(u.mem_read(0x50004000,12288)),pack[4096:16384])
        u.mem_write(0x50018000,struct.pack('>I',12288))
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_frozen_record'],[manifest,0,33,manifest]),0)
        self.assertEqual(bytes(u.mem_read(manifest,4108)),frozen)
        behavior['corrupt']=True;u.mem_write(0x50004000,b'\xa5'*12288)
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_record'],[0,33,0x50004000,12288]),0)
        self.assertEqual(bytes(u.mem_read(0x50004000,12288)),b'\xa5'*12288)
        behavior['no_card']=True
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_item'],[0]),0)
        self.assertEqual(tokens,{})
        self.assertEqual(len(closed),len(freed));self.assertEqual(len(handles),len(freed))
        self.assertEqual(free(),before)
        self.assertTrue(all(count in (4096,12288) for _,count in requests))

"""Streamed native SD operations execute real GR II pool and file wrappers."""
import struct
import subprocess
import unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import ROOT,component

class Gr2SdTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    call=runtime_tests.Gr2RuntimeBuildTests.call

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
        behavior['corrupt']=True;u.mem_write(0x50004000,b'\xa5'*12288)
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_record'],[0,33,0x50004000,12288]),0)
        self.assertEqual(bytes(u.mem_read(0x50004000,12288)),b'\xa5'*12288)
        behavior['no_card']=True
        self.assertEqual(self.call(u,report['symbols']['gr2_sd_item'],[0]),0)
        self.assertEqual(tokens,{})
        self.assertEqual(len(closed),len(freed));self.assertEqual(len(handles),len(freed))
        self.assertEqual(free(),before)
        self.assertTrue(all(count in (4096,12288) for _,count in requests))

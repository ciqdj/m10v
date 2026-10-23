"""Common SD bytes must remain little endian on the GR II big-endian CPU."""
import struct
import unittest
import zlib
from tests import test_gr2_runtime_build as runtime_tests

class Gr2StorageTests(unittest.TestCase):
    def test_native_empty_journal_proof_uses_original_sdk_and_never_accepts_media_or_short_read_failures(self):
        from scripts.analyze_gr2_native_contract import probe_fat_directory
        from tests.test_unity_update import component
        runtime=self.build();self.assertIn('gr2_journals_absent',runtime['symbols'])
        for entries,error,short,expected in (((),0,False,1),(('M10V5A.bin',),0,False,0),(('M10V5B.bin',),0,False,0),(('M10V5C.bin','OTHER.bin'),0,False,1),((),9,False,-1),((),3,False,-1),((),0,True,-1)):
            with self.subTest(entries=entries,error=error,short=short):
                report=probe_fat_directory(component('gr2','b01firm8'),entries=entries,read_error=error,short_read=short,native_runtime=runtime,cache_boundary=True)
                self.assertEqual(report['native_absent_return'],expected);self.assertTrue(report['pool_restored']);self.assertTrue(report['stack_preserved'])
        unready=probe_fat_directory(component('gr2','b01firm8'),native_runtime=runtime,ready=False,cache_boundary=True)
        self.assertEqual(unready['native_absent_return'],-1);self.assertEqual(unready['record_reads'],[]);self.assertTrue(unready['pool_restored'])

    build=runtime_tests.Gr2RuntimeBuildTests.build
    machine=runtime_tests.Gr2RuntimeBuildTests.machine
    call=runtime_tests.Gr2RuntimeBuildTests.call
    def test_native_file_bridge_admits_only_ten_owned_custom_snapshot_names(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from tests.test_unity_update import component
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();u=runtime_machine(component('gr2','b01firm8'));u.mem_write(report['base'],bytes.fromhex(report['runtime_hex']));opened=[]
        def open_failure(uc,address,size,unused):
            opened.append(bytes(uc.mem_read(uc.reg_read(r.UC_ARM_REG_R0),32)).split(b'\0',1)[0].decode())
            self.assertEqual(uc.reg_read(r.UC_ARM_REG_R1),1);uc.reg_write(r.UC_ARM_REG_R0,0);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,open_failure,begin=0xa002c70e,end=0xa002c70e)
        allowed=[f'H:/M10VC{slot}{bank}.bin' for slot in range(5) for bank in range(2)]
        denied=['H:/M10VC50.bin','H:/M10VC02.bin','H:/M10VC00.bin.extra','H:/M10VC00.bin/../other','H:/M10V/FILMS.M10','A:/M10VC00.bin','H:/M10VC0.bin','H:/M10VC000.bin']
        for path in allowed+denied:
            with self.subTest(path=path):
                opened.clear();u.mem_write(0x50001000,path.encode()+b'\0')
                self.assertEqual(self.call(u,report['symbols']['gr2_file_write'],[0x50001000,0x50002000,16]),0xffffffff)
                self.assertEqual(opened,[path] if path in allowed else [])

    def test_custom_snapshot_writes_inactive_bank_verifies_exact_readback_and_keeps_active_copy(self):
        import subprocess
        from tests.test_unity_update import ROOT
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();self.assertIn('gr2_custom_snapshot_store',report['symbols']);self.assertIn('gr2_custom_snapshot_read',report['symbols'])
        raw=subprocess.check_output(['node','--input-type=module','-e',"import {customFilmRecord} from './compat/gr2-v1/node/gr3-sd-film-pack.mjs';for(const id of [79,80])process.stdout.write(customFilmRecord({name:'LUT '+id,rgb:Buffer.from(Array.from({length:6591},(_,i)=>(i+id)%256))},id));"],cwd=ROOT)
        records=[raw[:12288],raw[12288:]];u=self.machine(report);u.mem_map(0x52000000,0x4000);u.mem_map(0x53000000,0x4000)
        io=0x50000000;state=0x50001000;bank=0x50002000;work=0x53000000;record=0x52000000
        u.mem_write(io,struct.pack('>2I',0x5001d000,0x5001d004));files={};writes=[];behavior={'short':False,'trailing':False}
        def boundary(uc,address,size,unused):
            path=bytes(uc.mem_read(uc.reg_read(r.UC_ARM_REG_R0),20)).split(b'\0',1)[0].decode();buffer=uc.reg_read(r.UC_ARM_REG_R1);count=uc.reg_read(r.UC_ARM_REG_R2)
            self.assertIn(path,('H:/M10VC00.bin','H:/M10VC01.bin'))
            if address==0x5001d000:
                data=files.get(path,b'')+(b'!' if behavior['trailing'] and path.endswith('01.bin') else b'');data=data[:count];uc.mem_write(buffer,data);value=len(data)
            else:
                data=bytes(uc.mem_read(buffer,count));value=23 if behavior['short'] else count;files[path]=data[:value];writes.append(path)
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,boundary,begin=0x5001d000,end=0x5001d004)
        self.call(u,report['symbols']['m10v_library_init'],[state]);u.mem_write(record,records[0])
        def store():
            u.mem_write(bank,struct.pack('>I',0xa5a5a5a5));u.mem_write(0x50018000,struct.pack('>2I',work,bank))
            return self.call(u,report['symbols']['gr2_custom_snapshot_store'],[io,state,0,record])
        self.assertEqual(store(),1);self.assertEqual(struct.unpack('>I',u.mem_read(bank,4))[0],0)
        self.assertEqual(files['H:/M10VC00.bin'],records[0])
        wire=bytearray(u.mem_read(state,104));struct.pack_into('>H',wire,12,79);wire[62]=1;struct.pack_into('>I',wire,100,zlib.crc32(wire[:100]));u.mem_write(state,bytes(wire));u.mem_write(record,records[1])
        before=bytes(u.mem_read(state,104));behavior['short']=True
        self.assertEqual(store(),0);self.assertEqual(struct.unpack('>I',u.mem_read(bank,4))[0],0xa5a5a5a5)
        self.assertEqual(files['H:/M10VC00.bin'],records[0]);self.assertEqual(bytes(u.mem_read(state,104)),before)
        behavior['short']=False;behavior['trailing']=True;self.assertEqual(store(),0)
        behavior['trailing']=False;self.assertEqual(store(),1);self.assertEqual(struct.unpack('>I',u.mem_read(bank,4))[0],1)
        self.assertEqual(files['H:/M10VC00.bin'],records[0]);self.assertEqual(files['H:/M10VC01.bin'],records[1])
        u.mem_write(0x50018000,struct.pack('>I',work));self.assertEqual(self.call(u,report['symbols']['gr2_custom_snapshot_read'],[io,state,0,record]),1)
        self.assertEqual(bytes(u.mem_read(record,12288)),records[0])
        files['H:/M10VC00.bin']=records[0]+b'!';u.mem_write(record,b'\xa5'*12288);u.mem_write(0x50018000,struct.pack('>I',work))
        self.assertEqual(self.call(u,report['symbols']['gr2_custom_snapshot_read'],[io,state,0,record]),0)
        self.assertEqual(bytes(u.mem_read(record,12288)),b'\xa5'*12288)

    def test_state_codec_crosses_native_endian_and_refuses_corrupt_payload_atomically(self):
        report=self.build();self.assertIn('gr2_state_encode',report['symbols']);u=self.machine(report)
        self.call(u,report['symbols']['m10v_library_init'],[0x50001000])
        self.assertEqual(self.call(u,report['symbols']['gr2_state_encode'],[0x50001000,0x50002000]),1)
        expected=bytearray(104);struct.pack_into('<IHHI',expected,0,0x5630314d,4,104,0)
        for i in range(5):
            struct.pack_into('<H6B',expected,12+i*8,33 if i==4 else i+34,0,0,3,3,5,2)
            expected[56+i*8]=1;expected[59+i*8]=4
        struct.pack_into('<I',expected,100,zlib.crc32(expected[:100]))
        self.assertEqual(bytes(u.mem_read(0x50002000,104)),bytes(expected))
        self.assertEqual(self.call(u,report['symbols']['gr2_state_decode'],[0x50002000,0x50003000]),1)
        self.assertEqual(bytes(u.mem_read(0x50003000,104)),bytes(u.mem_read(0x50001000,104)))
        for offset,repair in ((12,False),(12,True),(96,True)):
            corrupt=bytearray(expected);corrupt[offset]=255
            if repair:struct.pack_into('<I',corrupt,100,zlib.crc32(corrupt[:100]))
            u.mem_write(0x50002000,bytes(corrupt));u.mem_write(0x50003000,b'\xa5'*104)
            self.assertEqual(self.call(u,report['symbols']['gr2_state_decode'],[0x50002000,0x50003000]),0)
            self.assertEqual(bytes(u.mem_read(0x50003000,104)),b'\xa5'*104)

    def test_existing_sd_pack_and_recipe_hashes_execute_on_big_endian_cpu(self):
        import subprocess
        from tests.test_unity_update import ROOT
        report=self.build();u=self.machine(report)
        pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './compat/gr2-v1/node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack());"],cwd=ROOT)
        u.mem_write(0x50001000,pack[:4096])
        self.assertEqual(self.call(u,report['symbols']['m10v_sd_header'],[0x50001000,len(pack)]),46)
        for i in range(46):
            identity=struct.unpack_from('<I',pack,64+i*12)[0];record=pack[4096+i*12288:4096+(i+1)*12288]
            u.mem_write(0x50002000,record)
            with self.subTest(identity=identity):self.assertEqual(self.call(u,report['symbols']['m10v_sd_record'],[0x50002000,len(record),identity]),identity)
        corrupt=bytearray(pack[4096:4096+12288]);corrupt[80]^=1;struct.pack_into('<I',corrupt,12284,zlib.crc32(corrupt[:-4]));u.mem_write(0x50002000,bytes(corrupt))
        self.assertEqual(self.call(u,report['symbols']['m10v_sd_record'],[0x50002000,12288,33]),0)

    def test_dual_journal_recovery_readback_and_sequence_wrap(self):
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();self.assertIn('gr2_journal_load',report['symbols']);u=self.machine(report)
        files={};behavior={'short_write':False,'bad_readback':False};events=[]
        read_address=0x5001d000;write_address=0x5001d004
        u.mem_write(0x50000000,struct.pack('>2I',read_address,write_address))
        def io(uc,address,size,context):
            path=bytes(uc.mem_read(uc.reg_read(r.UC_ARM_REG_R0),32)).split(b'\0',1)[0].decode()
            buffer=uc.reg_read(r.UC_ARM_REG_R1);count=uc.reg_read(r.UC_ARM_REG_R2)
            if address==read_address:
                payload=files.get(path,b'')[:count]
                if behavior['bad_readback'] and payload:payload=bytes([payload[0]^1])+payload[1:]
                uc.mem_write(buffer,payload);value=len(payload);events.append(('read',path,count))
            else:
                payload=bytes(uc.mem_read(buffer,count));value=29 if behavior['short_write'] else count
                files[path]=payload[:value];events.append(('write',path,count))
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,io,begin=read_address,end=write_address)
        self.call(u,report['symbols']['m10v_library_init'],[0x50001000])
        self.call(u,report['symbols']['gr2_state_encode'],[0x50001000,0x50002000]);base=bytearray(u.mem_read(0x50002000,104))
        def wire(sequence):
            value=bytearray(base);struct.pack_into('<I',value,8,sequence);struct.pack_into('<I',value,100,zlib.crc32(value[:100]));return bytes(value)
        a='H:/M10V5A.bin';b='H:/M10V5B.bin';files[a]=wire(10);files[b]=wire(11)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50003000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50003008,4))[0],11)
        files[b]=wire(11)+b'!'
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50003000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50003008,4))[0],10)
        files[b]=wire(11);u.mem_write(0x50002000,wire(12));self.call(u,report['symbols']['gr2_state_decode'],[0x50002000,0x50003000])
        behavior['short_write']=True
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_store'],[0x50000000,0x50003000]),0)
        self.assertEqual(files[b],wire(11))
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50004000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50004008,4))[0],11)
        behavior['short_write']=False
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_store'],[0x50000000,0x50003000]),1)
        self.assertEqual(files[a],wire(12))
        behavior['bad_readback']=True
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_store'],[0x50000000,0x50003000]),0)
        behavior['bad_readback']=False
        # A candidate that loses journal arbitration was not committed.
        files[b]=wire(100)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_store'],[0x50000000,0x50003000]),0)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50004000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50004008,4))[0],100)
        files[a]=wire(0);files[b]=wire(0xffffffff)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50004000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50004008,4))[0],0)
        files.clear();u.mem_write(0x50004000,b'\xa5'*104)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50004000]),0)
        self.assertEqual(bytes(u.mem_read(0x50004000,104)),b'\xa5'*104)

    def test_compiled_file_bridge_closes_and_frees_its_own_metadata_on_short_write_and_close_error(self):
        from scripts.analyze_gr2_native_contract import probe_sd_file_lifecycle
        from tests.test_unity_update import component
        report=self.build();self.assertIn('gr2_file_read',report['symbols'])
        for write_error,close_error,written,read in ((False,False,104,104),(True,False,0xffffffff,29),(False,True,0xffffffff,0xffffffff)):
            with self.subTest(write_error=write_error,close_error=close_error):
                result=probe_sd_file_lifecycle(component('gr2','b01firm8'),native_runtime=report,fail_write=write_error,fail_close=close_error)
                self.assertEqual(result['write_returned'],written);self.assertEqual(result['read_returned'],read)
                self.assertEqual(result['backend_close_calls'],2);self.assertEqual(result['metadata_free_calls'],2)
                self.assertTrue(result['magic_cleared_before_free'])

    def test_compiled_pack_range_reads_seek_and_always_close_without_whole_pack_allocation(self):
        from scripts.analyze_gr2_native_contract import probe_sd_file_lifecycle
        from tests.test_unity_update import component
        report=self.build();self.assertTrue('gr2_file_read_at' in report['symbols'])
        payload=bytes((i*23+19)&255 for i in range(104));code=component('gr2','b01firm8')
        for offset,fail_seek in ((0,False),(29,False),(104,False),(105,False),(29,True)):
            with self.subTest(offset=offset,fail_seek=fail_seek):
                actual=probe_sd_file_lifecycle(code,native_runtime=report,read_offset=offset,fail_seek=fail_seek)
                expected=payload[offset:]
                self.assertEqual(actual['read_returned'],0xffffffff if fail_seek else len(expected))
                self.assertEqual(actual['backend_close_calls'],1);self.assertEqual(actual['metadata_free_calls'],1)
                self.assertTrue(actual['magic_cleared_before_free'])
                if not fail_seek:self.assertEqual(actual['buffer_hex'],expected.hex()+'a5'*(105-len(expected)))

    def test_compiled_file_size_checks_64_bit_position_close_and_keeps_failed_output_unchanged(self):
        from scripts.analyze_gr2_native_contract import probe_sd_file_lifecycle
        from tests.test_unity_update import component
        report=self.build();self.assertTrue('gr2_file_size' in report['symbols']);code=component('gr2','b01firm8')
        for flags in ({},{'reported_size':0},{'reported_size':0x100000001},{'fail_seek':True},{'fail_tell':True},{'fail_close':True},{'fail_open':True}):
            with self.subTest(flags=flags):
                actual=probe_sd_file_lifecycle(code,native_runtime=report,query_size=True,**flags)
                success=not any(flags.get(key) for key in ('fail_seek','fail_tell','fail_close','fail_open')) and flags.get('reported_size',104)<1<<32
                self.assertEqual(actual['size_returned'],int(success))
                expected=flags.get('reported_size',104).to_bytes(4,'big').hex() if success else 'a5'*4
                self.assertEqual(actual['buffer_hex'],expected+'a5'*101)
                self.assertEqual(actual['backend_close_calls'],0 if flags.get('fail_open') else 1)
                self.assertEqual(actual['metadata_free_calls'],actual['backend_close_calls'])

    def test_streamed_pack_fetch_checks_actual_size_identity_and_record_before_acceptance(self):
        import subprocess
        from tests.test_unity_update import ROOT
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();self.assertTrue('gr2_pack_fetch' in report['symbols']);u=self.machine(report)
        pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './compat/gr2-v1/node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack());"],cwd=ROOT)
        source={'bytes':pack};requests=[];size_fn=0x5001d000;read_fn=0x5001d004
        u.mem_write(0x50000000,struct.pack('>2I',size_fn,read_fn))
        def io(uc,address,size,context):
            data=source['bytes']
            if address==size_fn:uc.mem_write(uc.reg_read(r.UC_ARM_REG_R1),struct.pack('>I',len(data)));value=1
            else:
                offset=uc.reg_read(r.UC_ARM_REG_R1);target=uc.reg_read(r.UC_ARM_REG_R2);count=uc.reg_read(r.UC_ARM_REG_R3)
                payload=data[offset:offset+count];uc.mem_write(target,payload);value=len(payload);requests.append((offset,count))
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,io,begin=size_fn,end=read_fn)
        def fetch(index,expected,full):
            u.mem_write(0x50018000,struct.pack('>I',full))
            return self.call(u,report['symbols']['gr2_pack_fetch'],[0x50000000,index,expected,0x50004000])
        for index in (0,13,45):
            identity=struct.unpack_from('<I',pack,64+index*12)[0]
            self.assertEqual(fetch(index,0,0),identity);self.assertEqual(fetch(index,identity,1),identity)
            self.assertEqual(bytes(u.mem_read(0x50005000,12288)),pack[4096+index*12288:4096+(index+1)*12288])
        self.assertEqual(fetch(46,0,0),0);self.assertEqual(fetch(0,288,1),0)
        for invalid in (pack[:-1],pack+b'!',pack[:4096]+bytes([pack[4096]^1])+pack[4097:]):
            source['bytes']=invalid
            self.assertEqual(fetch(0,33,1),0)
        self.assertTrue(all(count in (4096,12288) for _,count in requests))

    def test_catalog_manifest_rejects_changed_custom_content_even_when_numeric_id_is_unchanged(self):
        import subprocess
        from tests.test_unity_update import ROOT
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();self.assertTrue('gr2_pack_manifest_load' in report['symbols']);u=self.machine(report)
        program="import {buildSdFilmPack} from './compat/gr2-v1/node/gr3-sd-film-pack.mjs';import {parseCustomCube} from './node/gr3-custom-lut.mjs';const cube='LUT_3D_SIZE 2\\n0 0 0\\n1 0 0\\n0 1 0\\n1 1 0\\n0 0 1\\n1 0 1\\n0 1 1\\n1 1 1\\n';for(const name of ['FIRST','SECOND'])process.stdout.write(buildSdFilmPack([],[parseCustomCube(Buffer.from(cube),'identity.cube',name)]));"
        packs=subprocess.check_output(['node','--input-type=module','-e',program],cwd=ROOT);first,second=packs[:16384],packs[16384:]
        self.assertEqual(len(second),16384);self.assertEqual(struct.unpack_from('<I',first,64)[0],79);self.assertEqual(struct.unpack_from('<I',second,64)[0],79)
        source={'bytes':first};size_fn=0x5001d000;read_fn=0x5001d004;u.mem_write(0x50000000,struct.pack('>2I',size_fn,read_fn))
        def io(uc,address,size,context):
            data=source['bytes']
            if address==size_fn:uc.mem_write(uc.reg_read(r.UC_ARM_REG_R1),struct.pack('>I',len(data)));value=1
            else:
                offset=uc.reg_read(r.UC_ARM_REG_R1);target=uc.reg_read(r.UC_ARM_REG_R2);count=uc.reg_read(r.UC_ARM_REG_R3)
                payload=data[offset:offset+count];uc.mem_write(target,payload);value=len(payload)
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,io,begin=size_fn,end=read_fn)
        manifest=0x50008000;work=0x50004000
        self.assertEqual(self.call(u,report['symbols']['gr2_pack_manifest_load'],[0x50000000,manifest,work]),1)
        saved=bytes(u.mem_read(manifest,4108))
        def fetch():
            u.mem_write(0x50018000,struct.pack('>I',work))
            return self.call(u,report['symbols']['gr2_pack_fetch_frozen'],[0x50000000,manifest,0,79])
        self.assertEqual(fetch(),79)
        source['bytes']=second
        self.assertEqual(fetch(),0xfffffffe)
        self.assertEqual(bytes(u.mem_read(manifest,4108)),saved)
        source['bytes']=first+b'!';self.assertEqual(fetch(),0xfffffffe)
        self.assertEqual(self.call(u,report['symbols']['gr2_pack_manifest_load'],[0x50000000,manifest,manifest]),0)
        self.assertEqual(bytes(u.mem_read(manifest,4108)),saved)

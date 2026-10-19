"""Execute locked ORIGINAL ARM serializers and compare isolated native outputs.

Run with .venv/bin/python -m unittest tests.test_gr3_iip_graph outside the
macOS sandbox (Unicorn JIT SIGILL in sandbox). No camera or IIP pixel emulator:
only RAM register images are mapped. Event service/cache endpoints are explicit
ABI test doubles; original control flow executes, hardware does not.
"""
import hashlib
import random
import struct
import tempfile
import unittest
from pathlib import Path
from scripts.build_gr3_iip_graph import build,FIRMWARE_SHA256
ROOT=Path(__file__).resolve().parents[1]
class IipOriginalArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_EXEC
        from unicorn import arm_const as A
        cls.A=A;cls.hook_kind=UC_HOOK_CODE
        cls.tmp=tempfile.TemporaryDirectory();cls.report=build(cls.tmp.name)
        fw=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
        if hashlib.sha256(fw).hexdigest()!=FIRMWARE_SHA256:raise AssertionError('locked official RTOS mismatch')
        cls.u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        cls.u.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A9)
        cls.u.mem_map(0x53000000,(len(fw)+4095)&~4095);cls.u.mem_write(0x53000000,fw)
        cls.u.mem_protect(0x53000000,(len(fw)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC)
        code=(Path(cls.tmp.name)/'m10v-iip-graph-arm.bin').read_bytes()
        cls.u.mem_map(cls.report['base'],(len(code)+4095)&~4095);cls.u.mem_write(cls.report['base'],code)
        cls.u.mem_map(0x55000000,0x100000)
        cls.u.mem_map(0x5536d000,0x1000) # original assertion logger flag page
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def call(self,fn,*args):
        A=self.A;u=self.u;sp=0x550fd000;stop=0x550ff000
        u.mem_write(sp,b'\0'*128)
        for i,v in enumerate(args):
            if i<4:u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
            else:u.mem_write(sp+4*(i-4),struct.pack('<I',v))
        u.reg_write(A.UC_ARM_REG_SP,sp);u.reg_write(A.UC_ARM_REG_LR,stop)
        u.emu_start(fn,stop,count=100000)
        self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),stop,'instruction budget exhausted')
        return u.reg_read(A.UC_ARM_REG_R0)
    def put(self,addr,values):self.u.mem_write(addr,struct.pack('<'+'I'*len(values),*values))
    def test_original_stage_route_executes_original_dispatch_without_query_or_extra_event(self):
        A=self.A;u=self.u
        u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
        ctx,params,settings=0x55001000,0x55002000,0x55003000
        self.put(ctx,[0,0,0x55004000,0]);self.put(0x55004000,[0,0x55005000,0,0])
        self.put(params,[0,0x55006000,0x55007000,0,settings]+[0]*6+[0,0x10000])
        u.mem_write(settings,struct.pack('<hhhhf',1,2,0,3,1.0))
        for fail in (False,True):
            calls=[]
            def hook(uc,pc,size,data):
                if pc in (0x5367b540,0x5367c158,0x53680088):
                    args=tuple(uc.reg_read(getattr(A,f'UC_ARM_REG_R{i}')) for i in range(4))
                    calls.append((pc,args))
                    # Original stage calls these once for sizing (r2=0), then
                    # for execution. Let original dispatcher own that choice.
                    uc.reg_write(A.UC_ARM_REG_R0,0 if fail and args[2] else 1)
                    uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
                elif pc in (0x536a9e8c,0x536a9dd4,0x5376cd10):
                    self.fail('adapter added an independent graph or event')
            handle=u.hook_add(self.hook_kind,hook)
            try: result=self.call(self.report['symbols']['m10v_iip_original_stage_owned'],ctx,params)
            finally:u.hook_del(handle)
            self.assertEqual(result,0xfffffffc if fail else 0)
            expected=[0x5367b540,0x5367c158,0x53680088,0x5367b540]
            if not fail:expected += [0x5367c158,0x53680088]
            self.assertEqual([c[0] for c in calls],expected)
            self.assertTrue(all(args[0]==ctx for _,args in calls))

    def test_original_release_status_predicates_are_not_generic_dma_idle(self):
        unit,registers=0x5500a000,0x5500b000
        self.put(unit,[0]*5+[registers])
        for status in range(8):
            self.put(registers,[0,status,0xa5a50003])
            self.assertEqual(self.call(0x53778490,unit),int(not(status&4)))
            self.assertEqual(self.call(0x53778474,unit),int((status&3)==3))
            # AbortMultipleImageProcess with nonzero flag only clears control
            # low2; original function does not read status, wait, or ack DMA.
            self.call(0x5377876c,unit,1)
            self.assertEqual(struct.unpack('<III',self.u.mem_read(registers,12)),
                             (0,status,0xa5a50000))

    def test_gpc_full_image_matches_original_setters_including_reserved_bits(self):
        rng=random.Random(0x1a59)
        for _ in range(100):
            initial=rng.randbytes(64);alpha=rng.getrandbits(32)
            e=[rng.getrandbits(32) for _ in range(4)];r=[rng.getrandbits(32) for _ in range(4)];f=[rng.getrandbits(32) for _ in range(5)]
            self.u.mem_write(0x55001000,initial);self.u.mem_write(0x55002000,initial)
            self.put(0x55003000,e);self.put(0x55004000,r);self.put(0x55005000,f);self.put(0x55006000,[0x55001000])
            self.call(0x53776ad0,0x55006000,alpha)
            for i in range(4):
                self.call(0x53776b18+20*i,0x55006000,e[i])
                self.call(0x53776b68+20*i,0x55006000,r[i])
                self.call(0x53776bb8+20*i,0x55006000,f[i])
            self.call(0x53776c08,0x55006000,f[4])
            self.assertEqual(self.call(self.report['symbols']['m10v_iip_gpc_patch'],0x55002000,64,alpha,0x55003000,0x55004000,0x55005000),0)
            self.assertEqual(self.u.mem_read(0x55001000,64),self.u.mem_read(0x55002000,64))
    def test_spf_all_four_17_value_banks_match_original_without_touching_other_bits(self):
        rng=random.Random(0x5ff)
        for bank,fn in enumerate((0x5377ae18,0x5377af70,0x5377b0c8,0x5377b264)):
            for _ in range(25):
                initial=rng.randbytes(0x284);values=[rng.getrandbits(32) for _ in range(17)]
                self.u.mem_write(0x55001000,initial);self.u.mem_write(0x55002000,initial)
                self.put(0x55003000,values);self.put(0x55006000,[0,0x55001000])
                self.call(fn,0x55006000,0x55003000)
                self.assertEqual(self.call(self.report['symbols']['m10v_iip_spf_bank_patch'],0x55002000,0x284,bank,0x55003000),0)
                self.assertEqual(self.u.mem_read(0x55001000,0x284),self.u.mem_read(0x55002000,0x284))
    def test_lut_signed_samples_stride_and_cache_abi_match_original_data_loop(self):
        A=self.A;u=self.u;cache=[]
        def hook(uc,pc,size,data):
            if pc==0x536bbc3c:
                cache.append(tuple(uc.reg_read(getattr(A,f'UC_ARM_REG_R{i}')) for i in range(3)))
                uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
        handle=u.hook_add(self.hook_kind,hook)
        try:
            for count,stride in ((1,0),(32,0),(256,1),(256,3),(1024,2)):
                values=[-32768,-1,0,1,32767]*500
                u.mem_write(0x55008000,struct.pack('<'+'h'*len(values),*values))
                u.mem_write(0x55001000,b'\xa5'*4100);u.mem_write(0x55003000,b'\xa5'*4100)
                self.call(0x5376c314,0,0x55001000,0x55008000,count,stride)
                self.assertEqual(self.call(self.report['symbols']['m10v_iip_lut_words'],0x55003000,1024,0x55008000,len(values),count,stride),0)
                self.assertEqual(u.mem_read(0x55001000,4100),u.mem_read(0x55003000,4100))
                self.assertEqual(cache[-1],(0x5536d1b4,0x55001000,count*4))
        finally:u.hook_del(handle)
    def test_invalid_native_inputs_leave_destination_untouched(self):
        self.u.mem_write(0x55001000,b'\xa5'*0x284);initial=bytes(self.u.mem_read(0x55001000,0x284))
        funcs=self.report['symbols']
        for args in ((0x55001000,1024,0x55008000,10,20,1),(0x55001000,10,0x55008000,10,11,0),(0x55001000,1024,0x55001000,10,10,1),(0x55001000,1024,0x55008000,10,0,1)):
            self.assertEqual(self.call(funcs['m10v_iip_lut_words'],*args),0xffffffff)
        self.assertEqual(self.call(funcs['m10v_iip_gpc_patch'],0x55001000,63,0,0x55003000,0x55004000,0x55005000),0xffffffff)
        self.assertEqual(self.call(funcs['m10v_iip_gpc_patch'],0x55001000,64,0,0x55001000,0x55004000,0x55005000),0xffffffff)
        self.assertEqual(self.call(funcs['m10v_iip_spf_bank_patch'],0x55001000,0x284,4,0x55003000),0xffffffff)
        self.assertEqual(self.call(funcs['m10v_iip_spf_bank_patch'],0x55001000,0x283,0,0x55003000),0xffffffff)
        self.assertEqual(bytes(self.u.mem_read(0x55001000,0x284)),initial)
    def test_original_wait_consumes_partial_completion_and_rejects_error_events(self):
        A=self.A;u=self.u;events=[];waits=[];clears=[]
        def hook(uc,pc,size,data):
            if pc==0x536a9e8c:
                args=[uc.reg_read(getattr(A,f'UC_ARM_REG_R{i}')) for i in range(4)];waits.append(args)
                result,bits=events.pop(0);uc.mem_write(args[2],struct.pack('<I',bits));uc.reg_write(A.UC_ARM_REG_R0,result)
            elif pc==0x536a9dd4:clears.append(uc.reg_read(A.UC_ARM_REG_R1))
            elif pc!=0x536b82d4:return
            uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
        handle=u.hook_add(self.hook_kind,hook)
        try:
            events.extend([(1,0x100),(1,0x400)])
            self.assertEqual(self.call(0x5368a510,0x5500a000,0x500),1)
            self.assertEqual(clears,[0x100,0x400]);self.assertEqual(len(waits),2)
            self.assertEqual([(x[0],x[1],x[3]) for x in waits],[(0x5500a00c,0xca00502,5000),(0x5500a00c,0xca00402,5000)])
            waits.clear();clears.clear();events.append((1,0x08000400))
            self.assertEqual(self.call(0x5368a510,0x5500a000,0x400),0)
            self.assertEqual(clears,[0x08000000,0x400]);self.assertFalse(events)
            waits.clear();clears.clear();events.append((0,0))
            self.assertEqual(self.call(0x5368a510,0x5500a000,0x400),0)
            self.assertEqual(len(waits),1);self.assertEqual(clears,[0])
            waits.clear();clears.clear()
            self.assertEqual(self.call(0x5368a510,0x5500a000,0),1)
            self.assertEqual(waits,[]);self.assertEqual(clears,[])
        finally:u.hook_del(handle)
    def test_original_false_assertion_logs_and_returns_without_abort(self):
        # Execute the REAL assertion routine's false branch, stubbing only its
        # log/current-thread/stacktrace services. This independently justifies
        # the returning assertion boundary used by the release-timeout test.
        A=self.A;u=self.u;logs=[]
        def hook(uc,pc,size,data):
            def ret(v=0):uc.reg_write(A.UC_ARM_REG_R0,v);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
            if pc==0x536b82d4:logs.append(pc);ret()
            elif pc==0x536b09f0:ret(1)
            elif pc==0x5381fc8c:ret(0)
        handle=u.hook_add(self.hook_kind,hook)
        try:self.call(0x536b93d0,0,0x5403018c,0x54030204,0x348,0x54034d18)
        finally:u.hook_del(handle)
        self.assertGreater(len(logs),3)
        self.assertEqual(u.mem_read(0x5536d113,1),b'\0','logger clears its flag then returns')

    def test_original_release_can_return_after_both_idle_poll_timeouts(self):
        # Prove the safety blocker: ORIGINAL composite/release control flow
        # continues after each 5002-iteration idle-poll timeout. Driver statuses
        # are explicit always-busy test doubles; this does not emulate hardware.
        A=self.A;u=self.u;task,graph=0x5500e000,0x55010000
        u.mem_write(task,b'\0'*0x200);u.mem_write(graph,b'\0'*0x120)
        self.put(graph+0x9c,[task]);u.mem_write(graph+0x40,b'\x01')
        u.mem_write(graph+0xa0+0x74,b'\x01');u.mem_write(task+0xfc,b'\x01')
        polls={0x53778490:0,0x53778474:0};assertions=[]
        # Synchronization and driver backend boundaries only. Original timeout
        # branches, counters and cleanup bookkeeping all execute unmodified.
        backend={0x536ae71c,0x536ae870,0x536a848c,0x536a8544,
                 0x53562910,0x536b0014,0x536b0a74,0x53778458,
                 0x53784de0,0x537780b8,0x537780e4,0x5377808c,0x5376eb2c}
        def hook(uc,pc,size,data):
            def ret(v=0):uc.reg_write(A.UC_ARM_REG_R0,v);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
            if pc in polls:polls[pc]+=1;ret(1)
            elif pc==0x536b93d0:
                if not uc.reg_read(A.UC_ARM_REG_R0):assertions.append(uc.reg_read(A.UC_ARM_REG_R3))
                ret() # original assertion logger itself also returns
            elif pc in backend:ret()
        handle=u.hook_add(self.hook_kind,hook)
        try:
            u.reg_write(A.UC_ARM_REG_R0,graph);u.reg_write(A.UC_ARM_REG_SP,0x550fd000);u.reg_write(A.UC_ARM_REG_LR,0x550ff000)
            u.emu_start(0x5376c044,0x550ff000,count=500000)
            self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x550ff000)
            self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),1,'release reports active state, not idle result')
        finally:u.hook_del(handle)
        self.assertEqual(polls,{0x53778490:5002,0x53778474:5002})
        self.assertEqual(assertions,[0x348,0x354])
        self.assertEqual(u.mem_read(graph+0x40,1),b'\0')
        self.assertEqual(struct.unpack('<I',u.mem_read(graph+0x9c,4))[0],0)
        # A caller can see released bookkeeping even though both driver status
        # doubles STILL report busy. It must not free/reuse DMA memory on this.

    def test_original_spf_template_initialization_has_real_legal_lowpass_coefficients(self):
        # Entire original ARM initialization executes; no service or arithmetic
        # stubs, no pixel hardware, stop BEFORE caller descriptor dereferences.
        A=self.A;u=self.u
        for i in range(3):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),0x5500a000+i*0x1000)
        u.reg_write(A.UC_ARM_REG_SP,0x550fd000);u.reg_write(A.UC_ARM_REG_LR,0x550ff000)
        u.emu_start(0x536793c0,0x53679848,count=100000)
        self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x53679848)
        base=u.reg_read(A.UC_ARM_REG_FP)-0x2dc
        expected=((20,34,20,34,40,34,20,34,20),
                  (15,25,15,25,96,25,15,25,15),
                  (10,18,10,18,144,18,10,18,10),
                  (5,9,5,9,200,9,5,9,5))
        for i,first9 in enumerate(expected):
            kernel=struct.unpack('<17h',u.mem_read(base+i*0x4c+0x2a,34))
            self.assertEqual(kernel,first9+(0,)*8);self.assertEqual(sum(kernel),256)
        # Sum256 strongly suggests Q8 unity but is NOT proof of hardware scale.

    def test_probe_uses_original_three_node_control_flow_and_keeps_pixels_unemulated(self):
        # Backend/RTOS calls below are ABI test doubles. The TWO original NEON
        # u64 shifts only build CPU resource bitsets. Unicorn 2.1.4 on this ARM64
        # host SIGILLs on these even outside sandbox, so their documented ARM CPU
        # semantics are stepped explicitly. This is NOT unmodified original ARM
        # end-to-end execution and is NOT proof of IIP filtering or pixel math.
        A=self.A;u=self.u;records=[];shifts=[];handles=[]
        u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
        ctx,owner,task,work=0x5500a000,0x5500d000,0x5500e000,0x55020000
        self.put(ctx,[0,0,owner,0]);self.put(owner,[0,task,0,0x5500f000])
        u.mem_write(work-16,b'\x55'*16);u.mem_write(work+6144,b'\xaa'*16)
        def hook(uc,pc,size,data):
            def reg(i):return uc.reg_read(getattr(A,f'UC_ARM_REG_R{i}'))
            def ret(v=0):uc.reg_write(A.UC_ARM_REG_R0,v);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
            if pc in (0x5376c434,0x5376c45c):
                shift=uc.reg_read(A.UC_ARM_REG_D17)&255
                if shift&128:shift-=256
                v=uc.reg_read(A.UC_ARM_REG_D8)
                v=((v<<shift) if shift>=0 else (v>>-shift))&0xffffffffffffffff if abs(shift)<64 else 0
                uc.reg_write(A.UC_ARM_REG_D16,v);uc.reg_write(A.UC_ARM_REG_PC,pc+4);shifts.append(pc)
            elif pc==0x5376bfdc:
                records.append(('bind',reg(0),reg(1),reg(2))) # observe; execute original
            elif pc==0x53779dd4:
                handles.append(len(handles));ret(handles[-1])
            elif pc==0x5376ebd0:records.append(('reserve',reg(0),reg(1)));ret(1)
            elif pc==0x53870da4:ret() # original format-record flush backend
            elif pc in (0x536bbc3c,0x536bbcac):records.append(('cache',pc,reg(1),reg(2)));ret()
            elif pc==0x5387110c:
                records.append(('node',reg(0),bytes(u.mem_read(reg(1),16))));ret()
            elif pc==0x5376e55c:records.append(('submit',reg(0),reg(1)));ret()
            elif pc==0x536a9e8c:
                records.append(('wait',reg(0),reg(1),reg(3)))
                u.mem_write(reg(2),struct.pack('<I',0x400));ret(1)
            elif pc==0x536a9dd4:records.append(('clear',reg(0),reg(1)));ret()
            elif pc==0x5376ed74:records.append(('release',reg(0),reg(1),reg(2)));ret()
            elif pc==0x536b93d0:
                self.assertNotEqual(reg(0),0,'original assertion failed at line '+hex(reg(3)));ret()
            elif pc in (0x536af2a8,0x536af2e4):self.fail('caller-RAM probe must not allocate/free original heap')
        handle=u.hook_add(self.hook_kind,hook)
        try:
            self.assertEqual(self.call(self.report['symbols']['m10v_iip_spf_probe_owned'],ctx,work,6144,8,20,4096),0)
        finally:u.hook_del(handle)
        self.assertEqual([r[2] for r in records if r[0]=='bind'],[work+0x660]*2)
        self.assertEqual([r[3] for r in records if r[0]=='bind'],[work+0x40,work+0x90])
        self.assertEqual([r[1] for r in records if r[0]=='node'],[2,4,31])
        self.assertEqual([r[1:3] for r in records if r[0]=='submit'],[(task,work+0x700)])
        self.assertEqual([r[1:] for r in records if r[0]=='wait'],[(ctx+12,0xca00402,5000)])
        order=[r[0] for r in records]
        self.assertLess(order.index('submit'),order.index('wait'));self.assertLess(order.index('wait'),order.index('release'))
        header=struct.unpack('<11I',u.mem_read(work,44))
        self.assertEqual(header[:7],(0x31504653,1,8,20,4096,0,0))
        self.assertEqual(header[8:11],(0xa55a,0xa55a,0),'NO hardware pixel computation is simulated')
        self.assertEqual(bytes(u.mem_read(work+0x1000,2048)),b'\x5a\xa5'*1024)
        self.assertEqual(struct.unpack('<17H',u.mem_read(work+0x780,34)),(0,)*8+(20,)+(0,)*8)
        self.assertEqual(struct.unpack('<I',u.mem_read(work+0x40+0x3c,4))[0],work+0x800)
        self.assertEqual(struct.unpack('<I',u.mem_read(work+0x90+0x3c,4))[0],work+0x1000)
        self.assertTrue(shifts);self.assertEqual(u.mem_read(work-16,16),b'\x55'*16);self.assertEqual(u.mem_read(work+6144,16),b'\xaa'*16)

if __name__=='__main__':unittest.main()

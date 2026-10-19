"""Independent data-only observer and conservative native entry contract."""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class Snapshot(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ('magic model model_vptr quick quick_vptr actual pending inflight shooting2f shooting30 shooting31 quick_state timer_review timer_wait quick_flags').split()]
class Record(C.Structure):
    _fields_=[('boundary',C.c_uint32),('time',C.c_uint32),('payload',C.c_uint32),('state',Snapshot)]
class Trace(C.Structure):
    _fields_=[('count',C.c_uint32),('dropped',C.c_uint32),('records',Record*16)]
READ=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32)
START=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint32))
class ViewRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();out=Path(cls.tmp.name)/'view.dylib'
        subprocess.run(['cc','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'native/gr3/m10v_view_recovery.c'),'-o',str(out)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(out));cls.lib.m10v_view_snapshot_read.argtypes=[C.POINTER(Snapshot),READ,C.c_void_p]
        cls.lib.m10v_view_recovery_decide.argtypes=[C.POINTER(Snapshot),C.c_uint32]
        cls.lib.m10v_view_recovery_request.argtypes=[C.POINTER(Snapshot),C.c_uint32,READ,C.c_void_p,START,C.c_void_p]
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        self.mem={0x55064398:1,0x55067958:0x53b4e7b0,0x55067960:4,0x55063910:1,0x550639ec:0x58000000,0x58000000:0x53b41380,0x5800016c:2}
        self.reads=[];self.calls=[]
        def read(c,a,n):self.reads.append((a,n));return self.mem.get(a,0)
        def start(c,m,fn):self.calls.append((m,list(fn[:4])));return 1
        self.reader=READ(read);self.starter=START(start);self.s=Snapshot()
    def snap(self):return self.lib.m10v_view_snapshot_read(C.byref(self.s),self.reader,None)
    def test_initialized_guard_and_exact_model_vptr(self):
        self.mem[0x55064398]=0;self.assertEqual(self.snap(),0);self.assertEqual(len(self.reads),1)
        self.mem[0x55064398]=1;self.mem[0x55067958]=123;self.assertEqual(self.snap(),0)
    def test_factory_slot_snapshot_no_initialization(self):
        self.assertEqual(self.snap(),1);self.assertEqual(self.s.quick,0x58000000);self.assertEqual(self.s.quick_state,2)
        self.mem[0x55063910]=0;self.assertEqual(self.snap(),1);self.assertEqual(self.s.quick,0)
    def test_bad_quick_pointer_never_followed(self):
        self.mem[0x550639ec]=0xfffffff0;self.assertEqual(self.snap(),1)
        self.assertFalse(any(a>=0xfffffff0 for a,n in self.reads))
    def test_every_required_fact_mandatory(self):
        self.snap()
        for bit in (1,2,4,8,16):self.assertEqual(self.lib.m10v_view_recovery_decide(C.byref(self.s),31^bit),0)
    def test_busy_capture_and_pending_deny(self):
        for field in ('inflight','pending','shooting2f','shooting30','shooting31'):
            self.snap();setattr(self.s,field,1);self.assertEqual(self.lib.m10v_view_recovery_decide(C.byref(self.s),31),0)
    def test_states_only_paused_can_request(self):
        self.snap()
        for state in range(8):
            self.s.actual=state;self.assertEqual(self.lib.m10v_view_recovery_decide(C.byref(self.s),31),1 if state==4 else 2 if state==2 else 0)
    def test_request_rereads_and_calls_only_original_signature(self):
        self.snap();self.mem[0x55067962]=1
        self.assertEqual(self.lib.m10v_view_recovery_request(C.byref(self.s),31,self.reader,None,self.starter,None),0);self.assertEqual(self.calls,[])
        self.mem[0x55067962]=0
        self.assertEqual(self.lib.m10v_view_recovery_request(C.byref(self.s),31,self.reader,None,self.starter,None),3)
        self.assertEqual(self.calls,[(0x55067958,[0,0,0,0])])
        # Accepted request does not forge a completion/current-state write.
        self.assertEqual(self.mem[0x55067960],4)
    def test_caller_trace_bounded_copies_no_pointer_retention(self):
        self.snap();t=Trace();append=self.lib.m10v_view_trace_append
        append.argtypes=[C.POINTER(Trace),C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(Snapshot)]
        for i in range(16):self.assertEqual(append(C.byref(t),i,i*100,169,C.byref(self.s)),1)
        self.s.actual=99
        self.assertEqual(t.records[0].state.actual,4)
        self.assertEqual(append(C.byref(t),16,0,0,C.byref(self.s)),0)
        self.assertEqual((t.count,t.dropped),(16,1))
    def test_actual_arm_deferred_native_completion_repair(self):
        result=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/analyze_gr3_view_deferred.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('patched ARM performs one native completion',result.stdout)
    def test_actual_stock_arm_timer_state2_gap_and_busy_queue(self):
        result=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/analyze_gr3_v7_liveview.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn('24 original ARM',result.stdout)
if __name__=='__main__':unittest.main()

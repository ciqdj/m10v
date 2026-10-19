"""Control state must survive trace drains and reject unproved RAW disappearance."""
import ctypes,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Token(ctypes.Structure):_fields_=[('w',ctypes.c_uint32*12)]
class RawLifetimeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();p=Path(cls.temp.name)/'token.dylib'
  subprocess.run(['clang','-shared','-fPIC','-Wall','-Wextra','-Werror',str(ROOT/'native/gr3/m10v_capture_raw_lifetime.c'),'-o',str(p)],check=True,capture_output=True)
  cls.lib=ctypes.CDLL(str(p));cls.owner=0x5c000028;cls.si=0x66000000;cls.backing=0xa6d48380;cls.source=0xa6e08370
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def call(self,name,t,*args):return getattr(self.lib,'m10v_capture_raw_'+name)(ctypes.byref(t),*map(ctypes.c_uint32,args))
 def fresh(self):
  t=Token();self.call('init',t,self.owner);return t
 def begin(self,t,caller=0x5351fd54):self.call('release_begin',t,self.owner,self.si,self.backing,self.source,caller)
 def pool(self,t,result=1,backing=None):self.call('pool_return',t,self.owner,self.si,1,self.backing if backing is None else backing,result)
 def clear(self,t):self.call('set_after',t,self.owner,self.si,1,0,self.backing,self.source,0,0)
 def finish(self,t):self.call('release_finish',t,self.owner,self.si,0,0)
 def status(self,t,source=0,backing=0,si=None,owner=None):return self.call('classify',t,self.owner if owner is None else owner,self.si if si is None else si,backing,source)
 def test_real_release_sequence_accepts_no_raw_pointer_and_rejects_other_frame(self):
  t=self.fresh();self.begin(t);self.pool(t);self.clear(t);self.finish(t)
  self.assertEqual(self.status(t),2);self.assertEqual(self.status(t,si=self.si+4),0);self.assertEqual(self.status(t,owner=self.owner+0x50f0),0)
 def test_missing_pool_failure_wrong_backing_and_wrong_caller_never_attest(self):
  for mode in ('no_pool','pool_failed','wrong_backing','wrong_caller','clear_without_begin','finish_without_clear'):
   t=self.fresh()
   if mode!='clear_without_begin':self.begin(t,0x5351f3ac if mode=='wrong_caller' else 0x5351fd54)
   if mode not in ('no_pool','clear_without_begin'):self.pool(t,0 if mode=='pool_failed' else 1,self.backing+32 if mode=='wrong_backing' else None)
   if mode!='finish_without_clear':self.clear(t)
   self.finish(t);self.assertEqual(self.status(t),0,mode)
 def test_reallocation_transfer_or_new_set_invalidates_released_state(self):
  for reset in ('invalidate','set'):
   t=self.fresh();self.begin(t);self.pool(t);self.clear(t);self.finish(t);self.assertEqual(self.status(t),2)
   if reset=='invalidate':self.call('invalidate',t,self.owner)
   else:self.call('set_after',t,self.owner,self.si,1,self.backing+64,0,0,self.backing+64,self.source+64)
   self.assertEqual(self.status(t),0);self.assertEqual(self.status(t,source=self.source+64,backing=self.backing+64),1)
 def test_raw_null_without_attestation_rejected_and_live_raw_stays_live(self):
  t=self.fresh();self.assertEqual(self.status(t),0);self.assertEqual(self.status(t,source=self.source,backing=self.backing),1)
  self.begin(t);self.assertEqual(self.status(t,source=self.source,backing=self.backing),0)
 def test_no_release_token_survives_reinitialization(self):
  t=self.fresh();self.begin(t);self.pool(t);self.clear(t);self.finish(t);self.call('init',t,self.owner);self.assertEqual(self.status(t),0)
if __name__=='__main__':unittest.main()

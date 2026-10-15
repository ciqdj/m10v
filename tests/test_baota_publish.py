"""Exercise deployment guards and rollback with fake host commands, no network."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'skills/m10v-baota-publish/scripts/update-server.sh'
BEFORE='1'*40
AFTER='2'*40
FAKE='''#!/usr/bin/env python3
import os,sys
from pathlib import Path
name=Path(sys.argv[0]).name;a=sys.argv[1:];root=Path(os.environ['M10V_DEPLOY_ROOT'])
with (root/'trace').open('a') as f:f.write(name+' '+repr(a)+'\\n')
if name=='git':
 if a[:2]==['remote','get-url']:print(os.getenv('FAKE_ORIGIN','https://github.com/zhaoo/m10v.git'))
 elif a[0]=='status':
  if os.getenv('FAKE_STATUS_FAIL'):sys.exit(128)
  print(' M server-edit' if os.getenv('FAKE_DIRTY') else '',end='')
 elif a[0]=='branch':print('main')
 elif a[0]=='rev-parse':print(os.environ['FAKE_EXPECTED'] if (a[1]=='origin/main' or a[1].startswith('refs/m10v/releases/')) else (root/'head').read_text())
 elif a[0]=='merge':(root/'head').write_text(a[-1])
 elif a[0]=='reset':(root/'head').write_text(a[-1])
elif name=='systemctl':
 if a[0]=='show':print('www' if a[3]=='User' else str(root))
elif name=='runuser':sys.exit(int(os.getenv('FAKE_BUILD_FAIL','0')))
elif name=='flock':sys.exit(int(os.getenv('FAKE_LOCK_FAIL','0')))
elif name=='curl':Path(a[a.index('-o')+1]).write_text('<input id="debug-mode">')
'''
class BaotaPublishTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.bin=self.root/'commands';self.bin.mkdir()
  for name in ('git','systemctl','runuser','flock','chown','curl'):
   p=self.bin/name;p.write_text(FAKE);p.chmod(0o755)
  (self.root/'head').write_text(BEFORE)
  (self.root/'.venv/bin').mkdir(parents=True)
  (self.root/'.venv/bin/python').symlink_to(Path(__import__('sys').executable))
  (self.root/'bin').mkdir()
  for name in ('fwdc239b-gr3-official.bin','fwdc243b-gr3x-official.bin'):(self.root/'bin'/name).write_bytes(b'protected')
  self.env={**os.environ,'PATH':str(self.bin)+':'+os.environ['PATH'],'M10V_DEPLOY_ROOT':str(self.root),'M10V_DEPLOY_NODE':__import__('sys').executable,'M10V_DEPLOY_LOCK':str(self.root/'lock'),'FAKE_EXPECTED':AFTER}
 def run_script(self,*args,**env):
  return subprocess.run(['bash',str(SCRIPT),*args],env={**self.env,**env},capture_output=True,text=True)
 def trace(self):return (self.root/'trace').read_text() if (self.root/'trace').exists() else ''
 def test_invalid_sha_never_touches_server(self):
  r=self.run_script('--deploy','main');self.assertEqual(r.returncode,2);self.assertEqual(self.trace(),'')
 def test_git_status_failure_stops_before_mutation(self):
  r=self.run_script('--deploy',AFTER,FAKE_STATUS_FAIL='1');self.assertNotEqual(r.returncode,0)
  self.assertNotIn("'fetch'",self.trace());self.assertNotIn("'restart'",self.trace())
 def test_github_origin_without_dot_git_is_accepted(self):
  r=self.run_script('--check',FAKE_ORIGIN='https://github.com/zhaoo/m10v');self.assertEqual(r.returncode,0,r.stderr)
 def test_check_is_read_only(self):
  r=self.run_script('--check');self.assertEqual(r.returncode,0,r.stderr)
  self.assertNotIn("'fetch'",self.trace());self.assertNotIn("'restart'",self.trace())
 def test_dirty_checkout_and_lock_conflict_stop_before_fetch(self):
  r=self.run_script('--deploy',AFTER,FAKE_DIRTY='1');self.assertNotEqual(r.returncode,0);self.assertNotIn("'fetch'",self.trace())
  r=self.run_script('--deploy',AFTER,FAKE_LOCK_FAIL='1');self.assertNotEqual(r.returncode,0);self.assertNotIn("'fetch'",self.trace())
 def test_changed_remote_stops_before_merge(self):
  r=self.run_script('--deploy',AFTER,FAKE_EXPECTED='3'*40);self.assertNotEqual(r.returncode,0)
  self.assertNotIn("'merge',",self.trace());self.assertNotIn("'restart'",self.trace())
 def test_build_failure_restores_previous_commit(self):
  r=self.run_script('--deploy',AFTER,FAKE_BUILD_FAIL='1');self.assertNotEqual(r.returncode,0)
  self.assertEqual((self.root/'head').read_text(),BEFORE);self.assertIn("'reset', '--keep'",self.trace());self.assertNotIn('DEPLOY_OK',r.stdout)
 def test_bundle_path_verifies_and_avoids_github_fetch(self):
  bundle=self.root/'release.bundle';bundle.write_bytes(b'fixture')
  r=self.run_script('--deploy',AFTER,str(bundle));self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn("'bundle', 'verify'",self.trace());self.assertIn('refs/m10v/releases/'+AFTER,self.trace())
  self.assertNotIn("'fetch', 'origin'",self.trace())
 def test_success_checks_builds_restart_and_exact_commit(self):
  r=self.run_script('--deploy',AFTER);self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual((self.root/'head').read_text(),AFTER);self.assertIn('DEPLOY_OK commit='+AFTER,r.stdout)
  self.assertIn('scripts/build_gr3_device_candidate.mjs',self.trace());self.assertIn('M10V_PYTHON=',self.trace());self.assertEqual(self.trace().count('runuser '),2);self.assertIn("'restart'",self.trace())
  self.assertEqual((self.root/'bin/fwdc239b-gr3-official.bin').read_bytes(),b'protected')
if __name__=='__main__':unittest.main()

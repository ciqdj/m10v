import os,subprocess,unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'deploy/receive-ssh.sh'
class RestrictedSshTests(unittest.TestCase):
 def test_commands_cannot_escape_fixed_deploy_entry(self):
  for command in ['', 'bash', 'deploy main', 'deploy '+'a'*40+'; id', 'deploy $(id)', 'deploy '+'a'*40+' extra', 'git-upload-pack repo']:
   r=subprocess.run(['bash',str(SCRIPT)],env={**os.environ,'SSH_ORIGINAL_COMMAND':command},input=b'',capture_output=True)
   self.assertEqual(r.returncode,2,(command,r.stderr))
   self.assertIn(b'Only deploy',r.stderr)

class RestrictedSshTransferTests(unittest.TestCase):
 def run_transfer(self,fail=False):
  import tempfile,sys
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);commands=root/'commands';commands.mkdir();work=root/'bundle';work.mkdir()
   fake='''#!PYTHON
import os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
if name=='mktemp':print(os.environ['FIXTURE_WORK'])
elif name=='bash':
 assert sys.argv[1]=='/usr/local/lib/m10v-deploy/update-server.sh'
 assert sys.argv[2]=='--deploy' and sys.argv[3]=='a'*40
 assert Path(sys.argv[4]).read_bytes()==b'fixture-bundle'
 print('DEPLOY_OK commit='+sys.argv[3]+' service=active')
 sys.exit(int(os.environ['FIXTURE_FAIL']))
elif name=='tee':sys.stdout.buffer.write(sys.stdin.buffer.read())
'''.replace('PYTHON',sys.executable)
   for name in ['mktemp','bash','tee']:
    p=commands/name;p.write_text(fake);p.chmod(0o755)
   return subprocess.run(['/bin/bash',str(SCRIPT)],env={**os.environ,'PATH':str(commands)+':'+os.environ['PATH'],'SSH_ORIGINAL_COMMAND':'deploy '+'a'*40,'FIXTURE_WORK':str(work),'FIXTURE_FAIL':'7' if fail else '0'},input=b'fixture-bundle',capture_output=True)
 def test_bundle_and_exact_sha_reach_fixed_executor(self):
  r=self.run_transfer();self.assertEqual(r.returncode,0,r.stderr);self.assertIn(b'DEPLOY_OK',r.stdout)
 def test_deployment_error_survives_log_pipeline(self):
  r=self.run_transfer(True);self.assertEqual(r.returncode,7,r.stderr)

if __name__=='__main__':unittest.main()

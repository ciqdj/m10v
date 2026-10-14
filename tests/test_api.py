import http.client
import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest

from m10v_core.api import create_server
from m10v_core.storage import Store
from .test_firmware import SAMPLE, SHA


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = create_server(Store(Path(self.temp.name)))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, body=b'', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return result

    def test_loopback_and_locked_status(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        status, raw, _ = self.request('GET', '/api/status')
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertFalse(payload['can_generate'])
        self.assertEqual(payload['features']['crop']['status'], 'unsupported')
        self.assertEqual(payload['features']['shutdown']['status'], 'unsupported')
        self.assertIn('unproven_cpu_checksum_repair', payload['blockers'])
        self.assertIn('hardware_recovery_not_verified', payload['blockers'])
        self.assertTrue(payload['session_token'])

    def test_remote_bind_rejected(self):
        with self.assertRaises(ValueError):
            create_server(Store(Path(self.temp.name)), host='0.0.0.0')

    def test_state_change_requires_token_and_same_origin(self):
        token = json.loads(self.request('GET', '/api/status')[1])['session_token']
        self.assertEqual(self.request('POST', '/api/import', b'bad')[0], 403)
        headers = {'X-M10V-Token': token, 'Origin': 'https://foreign.example'}
        self.assertEqual(self.request('POST', '/api/import', b'bad', headers)[0], 403)

    def test_modified_build_routes_are_absent(self):
        token = json.loads(self.request('GET', '/api/status')[1])['session_token']
        self.assertEqual(self.request('POST', '/api/build', b'', {'X-M10V-Token': token})[0], 404)
        self.assertEqual(self.request('GET', '/builds/candidate.bin')[0], 404)
        self.assertEqual(self.request('GET', '/../fwdc239b.bin')[0], 404)

    @unittest.skipUnless(SAMPLE.exists(), 'local official sample unavailable')
    def test_exact_import_and_report(self):
        token = json.loads(self.request('GET', '/api/status')[1])['session_token']
        headers = {'X-M10V-Token': token, 'Content-Type': 'application/octet-stream'}
        status, raw, _ = self.request('POST', '/api/import', SAMPLE.read_bytes(), headers)
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload['sha256'], SHA)
        self.assertEqual(len(payload['sections']), 14)
        status, raw, _ = self.request('GET', '/api/projects/' + SHA)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['sha256'], SHA)

    def test_upload_limit_and_unsupported_method(self):
        token = json.loads(self.request('GET', '/api/status')[1])['session_token']
        headers = {'X-M10V-Token': token, 'Content-Length': '999999999'}
        self.assertEqual(self.request('POST', '/api/import', b'x', headers)[0], 413)
        self.assertEqual(self.request('PUT', '/api/import', b'x', headers)[0], 405)

    @unittest.skipUnless(SAMPLE.exists(), 'local official sample unavailable')
    def test_orphan_original_is_not_a_project(self):
        original = Path(self.temp.name) / 'projects' / SHA / 'original.bin'
        original.parent.mkdir(parents=True)
        original.write_bytes(SAMPLE.read_bytes())
        self.assertEqual(self.request('GET', '/api/projects/' + SHA)[0], 404)

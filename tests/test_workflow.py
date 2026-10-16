import http.client
from pathlib import Path
import tempfile
from threading import Thread
import unittest

from m10v_core.api import create_server
from m10v_core.storage import Store


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = create_server(Store(Path(self.temp.name)))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request('GET', path)
        response = connection.getresponse()
        result = response.status, response.read().decode()
        connection.close()
        return result

    def test_home_exposes_current_model_launcher(self):
        status, page = self.get('/')
        self.assertEqual(status, 200)
        for route in ('/gr3/', '/gr4/', '/gr2/', '/guide/', '/changelog/'):
            self.assertIn('href="'+route+'"', page)
        self.assertIn('GR III 与 GR IIIx', page)
        self.assertIn('36 套胶卷', page)
        self.assertNotIn('id="build-button"', page)

    def test_static_assets_served_and_unknown_path_rejected(self):
        self.assertEqual(self.get('/app.js')[0], 200)
        status, styles = self.get('/styles.css')
        self.assertEqual(status, 200)
        self.assertNotIn('https://', styles)
        self.assertEqual(self.get('/candidate.bin')[0], 404)

    def test_home_styles_and_client_service_status_contract(self):
        status, page = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn('href="/styles.css"', page)
        _, script = self.get('/app.js')
        self.assertIn('/api/platform/adapters', script)
        self.assertIn('本地服务已连接', script)
        self.assertIn('工作区状态不可用', script)

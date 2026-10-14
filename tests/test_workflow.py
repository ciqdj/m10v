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

    def test_page_exposes_actual_import_backup_and_locked_features(self):
        status, page = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn('选择官方固件', page)
        self.assertIn('导出电脑端备份', page)
        self.assertIn('验证备份包', page)
        self.assertIn('自定义裁切比例', page)
        self.assertIn('关机画面', page)
        self.assertIn('id="crop-form"', page)
        self.assertIn('id="shutdown-catalog"', page)
        self.assertIn('修改固件导出已锁定', page)
        self.assertNotIn('id="build-button"', page)

    def test_static_assets_served_and_unknown_path_rejected(self):
        self.assertEqual(self.get('/app.js')[0], 200)
        status, styles = self.get('/styles.css')
        self.assertEqual(status, 200)
        self.assertNotIn('https://', styles)
        self.assertEqual(self.get('/candidate.bin')[0], 404)

    def test_direct_file_open_keeps_styling_and_explains_server_requirement(self):
        status, page = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn('href="styles.css"', page)
        self.assertIn('src="app.js"', page)
        _, script = self.get('/app.js')
        self.assertIn("location.protocol === 'file:'", script)
        self.assertIn('npm start', script)
        self.assertIn("$('firmware-picker').addEventListener('click'", script)

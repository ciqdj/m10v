# SPDX-License-Identifier: GPL-2.0-only
"""Loopback-only HTTP boundary for read-only GR III work."""

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import tempfile
from urllib.parse import urlsplit

from .backup import export_backup, inspect_backup, restore_backup
from .firmware import FirmwareIdentityError, inspect_official
from .storage import Store


MAX_UPLOAD = 128 * 1024 * 1024
WEB = Path(__file__).resolve().parents[1] / 'web'


def create_server(store: Store, host: str = '127.0.0.1', port: int = 0) -> ThreadingHTTPServer:
    if host != '127.0.0.1':
        raise ValueError('m10v only binds to 127.0.0.1')
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'm10v/0.1'

        def log_message(self, format, *args):
            pass

        def _send(self, status, body, kind='application/json; charset=utf-8', filename=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def _host_valid(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def _authorized(self):
            if self.headers.get('X-M10V-Token') != token:
                return False
            origin = self.headers.get('Origin')
            return origin is None or origin == f'http://127.0.0.1:{self.server.server_port}'

        def _body(self):
            length = self.headers.get('Content-Length')
            if length is None or not length.isdecimal():
                raise ValueError('missing or invalid Content-Length')
            size = int(length)
            if size > MAX_UPLOAD:
                raise OverflowError('upload exceeds limit')
            data = self.rfile.read(size)
            if len(data) != size:
                raise ValueError('incomplete upload')
            return data

        def _report(self, data):
            return asdict(inspect_official(data))

        def _route(self, method):
            if not self._host_valid():
                return self._send(403, {'error': 'invalid host'})
            path = urlsplit(self.path).path
            if path != self.path or '%' in path or '\\' in path or '..' in path:
                return self._send(404, {'error': 'not found'})
            if method == 'GET':
                if path == '/api/status':
                    return self._send(200, {
                        'session_token': token, 'can_generate': False,
                        'model': 'GR III', 'hardware': 'not_tested',
                        'blockers': ['unproven_cpu_checksum_repair', 'hardware_recovery_not_verified'],
                        'features': {
                            'crop': {'status': 'unsupported', 'can_preview': True, 'can_generate': False},
                            'shutdown': {'status': 'unsupported', 'can_preview': True, 'can_generate': False},
                        },
                    })
                if path.startswith('/api/projects/'):
                    try:
                        return self._send(200, self._report(store.read_original(path.split('/')[-1])))
                    except (OSError, ValueError):
                        return self._send(404, {'error': 'project not found'})
                static = {'/': ('index.html', 'text/html; charset=utf-8'),
                          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                          '/styles.css': ('styles.css', 'text/css; charset=utf-8')}
                if path in static and (WEB / static[path][0]).is_file():
                    return self._send(200, (WEB / static[path][0]).read_bytes(), static[path][1])
                return self._send(404, {'error': 'not found'})
            if method != 'POST':
                return self._send(405, {'error': 'method not allowed'})
            known = path in ('/api/import', '/api/backup/inspect', '/api/backup/restore') or (
                path.startswith('/api/projects/') and path.endswith('/backup') and len(path.split('/')) == 5)
            if not known:
                return self._send(404, {'error': 'not found'})
            if not self._authorized():
                return self._send(403, {'error': 'authorization failed'})
            try:
                raw = self._body()
                if path == '/api/import':
                    record = store.import_official(raw)
                    return self._send(200, {'project_id': record.id, **self._report(raw)})
                if path.endswith('/backup'):
                    project_id = path.split('/')[-2]
                    with tempfile.TemporaryDirectory(prefix='m10v-export-') as folder:
                        archive = Path(folder) / 'backup.zip'
                        export_backup(store, project_id, archive)
                        return self._send(200, archive.read_bytes(), 'application/zip',
                                          'm10v-gr3-backup.zip')
                with tempfile.TemporaryDirectory(prefix='m10v-import-') as folder:
                    archive = Path(folder) / 'backup.zip'
                    archive.write_bytes(raw)
                    if path == '/api/backup/inspect':
                        return self._send(200, asdict(inspect_backup(archive)))
                    with tempfile.TemporaryDirectory(prefix='m10v-rehearsal-') as rehearsal:
                        trial = restore_backup(Store(Path(rehearsal)), archive)
                    actual = restore_backup(store, archive)
                    return self._send(200, {'project_id': actual.id, 'original_sha256': trial.sha256,
                                            'rehearsal': 'passed', 'camera_recovery': 'not_tested'})
            except OverflowError as exc:
                return self._send(413, {'error': str(exc)})
            except (ValueError, OSError, FirmwareIdentityError) as exc:
                return self._send(400, {'error': str(exc)})

        def do_GET(self):
            self._route('GET')

        def do_POST(self):
            self._route('POST')

        def do_PUT(self):
            self._route('PUT')

    return ThreadingHTTPServer((host, port), Handler)

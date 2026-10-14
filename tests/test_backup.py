import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from m10v_core.storage import Store
from m10v_core.backup import export_backup, inspect_backup, restore_backup
from .test_firmware import SAMPLE, SHA


@unittest.skipUnless(SAMPLE.exists(), 'local official sample unavailable')
class BackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = SAMPLE.read_bytes()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'store')
        self.project = self.store.import_official(self.data)
        self.archive = self.root / 'backup.zip'

    def test_round_trip_in_fresh_directory(self):
        result = export_backup(self.store, self.project.id, self.archive)
        self.assertEqual(result.original_sha256, SHA)
        self.assertEqual(inspect_backup(self.archive).original_sha256, SHA)
        restored_store = Store(self.root / 'fresh')
        restored = restore_backup(restored_store, self.archive)
        self.assertEqual(restored.sha256, SHA)
        self.assertEqual(restored_store.read_original(restored.id), self.data)
        self.assertEqual(restored_store.read_project(restored.id), self.project)

    def test_modified_member_rejected_and_store_unchanged(self):
        export_backup(self.store, self.project.id, self.archive)
        self._rewrite({'original/fwdc239b.bin': b'bad'})
        with self.assertRaises(ValueError):
            restore_backup(self.store, self.archive)
        self.assertEqual(self.store.read_original(self.project.id), self.data)

    def test_extra_and_traversal_members_rejected(self):
        export_backup(self.store, self.project.id, self.archive)
        for name in ('extra.txt', '../outside.txt'):
            with self.subTest(name=name):
                self._rewrite({name: b'evil'})
                with self.assertRaises(ValueError):
                    inspect_backup(self.archive)
                export_backup(self.store, self.project.id, self.archive)

    def test_duplicate_and_symlink_members_rejected(self):
        export_backup(self.store, self.project.id, self.archive)
        with zipfile.ZipFile(self.archive, 'a') as archive:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                archive.writestr('project.json', b'{}')
        with self.assertRaises(ValueError):
            inspect_backup(self.archive)
        export_backup(self.store, self.project.id, self.archive)
        with zipfile.ZipFile(self.archive) as archive:
            members = [(info, archive.read(info)) for info in archive.infolist()
                       if info.filename != 'project.json']
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for info, data in members:
                archive.writestr(info, data)
            link = zipfile.ZipInfo('project.json')
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            archive.writestr(link, b'target')
        with self.assertRaises(ValueError):
            inspect_backup(self.archive)

    def test_missing_member_and_bad_json_rejected(self):
        export_backup(self.store, self.project.id, self.archive)
        self._rewrite({'project.json': b'{invalid'})
        with self.assertRaises(ValueError):
            inspect_backup(self.archive)
        export_backup(self.store, self.project.id, self.archive)
        self._rewrite({'project.json': None})
        with self.assertRaises(ValueError):
            inspect_backup(self.archive)

    def test_failed_atomic_rename_preserves_original(self):
        original = self.store.read_original(self.project.id)
        fresh = Store(self.root / 'failed-import')
        with patch('m10v_core.storage.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                fresh.import_official(self.data)
        self.assertFalse((fresh.root / 'projects' / (self.project.id + '.json')).exists())
        self.assertEqual(self.store.read_original(self.project.id), original)

    def test_symlinked_store_directory_cannot_redirect_original(self):
        outside = self.root / 'outside'
        outside.mkdir()
        diverted = Store(self.root / 'diverted')
        diverted.root.mkdir()
        (diverted.root / 'projects').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            diverted.import_official(self.data)
        self.assertEqual(list(outside.iterdir()), [])

    def test_official_original_is_not_writable(self):
        original = self.store.root / 'projects' / self.project.id / 'original.bin'
        self.assertEqual(original.stat().st_mode & 0o222, 0)

    def test_project_publish_failure_leaves_no_original(self):
        fresh = Store(self.root / 'partial')
        real_replace = os.replace

        def fail_project(source, destination):
            if str(destination).endswith(self.project.id):
                raise OSError('project publish failed')
            return real_replace(source, destination)

        with patch('m10v_core.storage.os.replace', side_effect=fail_project):
            with self.assertRaises(OSError):
                fresh.import_official(self.data)
        self.assertFalse((fresh.root / 'projects' / self.project.id).exists())

    def _rewrite(self, changes):
        with zipfile.ZipFile(self.archive) as archive:
            rows = [(info, archive.read(info)) for info in archive.infolist()]
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for info, data in rows:
                if info.filename in changes:
                    data = changes.pop(info.filename)
                if data is not None:
                    archive.writestr(info, data)
            for name, data in changes.items():
                archive.writestr(name, data)

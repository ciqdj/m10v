# SPDX-License-Identifier: GPL-2.0-only
"""Portable computer-side backup; not a camera Flash recovery mechanism."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import tempfile
import zipfile

from .firmware import inspect_official
from .storage import ProjectRecord, Store


ORIGINAL = 'original/fwdc239b.bin'
PROJECT = 'project.json'
NOTICE = 'README-恢复说明.txt'
EXPECTED = {ORIGINAL, PROJECT, NOTICE, 'manifest.json'}
MAX_MEMBER = 128 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
INSTRUCTIONS = ('这是电脑端项目备份，不包含相机内部 Flash/NAND。\n'
                '请在 m10v 中导入并验证。原厂 BIN 不保证能降级刷回或修复变砖相机。\n').encode()


@dataclass(frozen=True)
class BackupReport:
    project_id: str
    original_sha256: str
    member_count: int


def _json(data: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result

    def bad_constant(value):
        raise ValueError('invalid JSON number')

    try:
        return json.loads(data, object_pairs_hook=unique, parse_constant=bad_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid backup JSON') from exc


def _canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode()


def export_backup(store: Store, project_id: str, destination: Path) -> BackupReport:
    record = store.read_project(project_id)
    original = store.read_original(project_id)
    payloads = {ORIGINAL: original, PROJECT: _canonical(asdict(record)), NOTICE: INSTRUCTIONS}
    manifest = {'schema_version': 1, 'members': {
        name: {'sha256': sha256(data).hexdigest(), 'size': len(data)}
        for name, data in payloads.items()}}
    payloads['manifest.json'] = _canonical(manifest)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.m10v-backup-', dir=destination.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=False) as archive:
            for name, data in payloads.items():
                archive.writestr(name, data)
        inspected = inspect_backup(Path(temporary))
        with open(temporary, 'rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return inspected
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_backup(path: Path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != len(EXPECTED) or {i.filename for i in infos} != EXPECTED:
            raise ValueError('backup members differ from expected set')
        if len({i.filename.casefold() for i in infos}) != len(EXPECTED):
            raise ValueError('duplicate backup member')
        total = 0
        rows = {}
        for info in infos:
            if info.is_dir() or info.file_size > MAX_MEMBER:
                raise ValueError('unsafe backup member')
            mode = (info.external_attr >> 16) & 0o170000
            if mode not in (0, stat.S_IFREG):
                raise ValueError('backup contains non-file member')
            total += info.file_size
            if total > MAX_TOTAL:
                raise ValueError('backup exceeds size limit')
            with archive.open(info) as member:
                data = member.read(info.file_size + 1)
            if len(data) != info.file_size:
                raise ValueError('backup member size mismatch')
            rows[info.filename] = data
    return rows


def _validate(path: Path):
    try:
        rows = _read_backup(path)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError('invalid backup ZIP') from exc
    manifest = _json(rows['manifest.json'])
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise ValueError('unsupported backup manifest')
    members = manifest.get('members')
    if not isinstance(members, dict) or set(members) != EXPECTED - {'manifest.json'}:
        raise ValueError('backup manifest members differ')
    for name, value in members.items():
        if (not isinstance(value, dict) or set(value) != {'sha256', 'size'} or
                value['size'] != len(rows[name]) or
                value['sha256'] != sha256(rows[name]).hexdigest()):
            raise ValueError('backup member hash or length differs')
    if rows[NOTICE] != INSTRUCTIONS:
        raise ValueError('backup recovery notice differs')
    report = inspect_official(rows[ORIGINAL])
    raw_record = _json(rows[PROJECT])
    if not isinstance(raw_record, dict) or set(raw_record) != set(ProjectRecord.__dataclass_fields__):
        raise ValueError('invalid backup project')
    record = ProjectRecord(**raw_record)
    if (record.id, record.sha256, record.size, record.model,
            record.public_version, record.internal_version) != (
            report.sha256, report.sha256, report.size, report.model,
            report.public_version, report.internal_version):
        raise ValueError('backup project identity mismatch')
    return BackupReport(record.id, report.sha256, len(rows)), rows


def inspect_backup(path: Path) -> BackupReport:
    return _validate(Path(path))[0]


def restore_backup(store: Store, path: Path) -> ProjectRecord:
    _, rows = _validate(Path(path))
    record = store.import_official(rows[ORIGINAL])
    if store.read_project(record.id) != record or store.read_original(record.id) != rows[ORIGINAL]:
        raise ValueError('restored data failed readback')
    return record

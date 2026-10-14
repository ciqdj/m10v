# SPDX-License-Identifier: GPL-2.0-only
"""Atomically published, read-only GR III originals and project records."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from .firmware import inspect_official


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    sha256: str
    size: int
    model: str
    public_version: str
    internal_version: str


def _fsync_directory(path: Path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_staged(path: Path, data: bytes, mode: int):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, mode)
    with path.open('rb') as stream:
        os.fsync(stream.fileno())


class Store:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    @staticmethod
    def _id(value: str):
        if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('invalid project id')
        return value

    def _projects(self, create=False):
        if create:
            self.root.mkdir(parents=True, exist_ok=True)
        projects = self.root / 'projects'
        if projects.is_symlink():
            raise ValueError('project directory is a symlink')
        if create:
            projects.mkdir(exist_ok=True)
        if projects.exists() and (not projects.is_dir() or projects.resolve() != projects):
            raise ValueError('project directory is unsafe')
        return projects

    def _folder(self, project_id: str) -> Path:
        folder = self._projects() / self._id(project_id)
        if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
            raise ValueError('project path is unsafe')
        return folder

    def import_official(self, data: bytes) -> ProjectRecord:
        report = inspect_official(data)
        record = ProjectRecord(report.sha256, report.sha256, report.size, report.model,
                               report.public_version, report.internal_version)
        projects = self._projects(create=True)
        destination = self._folder(record.id)
        if destination.exists():
            if self.read_project(record.id) != record or self.read_original(record.id) != data:
                raise ValueError('existing project differs from official input')
            return record
        staging = Path(tempfile.mkdtemp(prefix='.m10v-', dir=projects))
        try:
            _write_staged(staging / 'original.bin', data, 0o400)
            encoded = (json.dumps(asdict(record), sort_keys=True) + '\n').encode()
            _write_staged(staging / 'project.json', encoded, 0o400)
            _fsync_directory(staging)
            os.replace(staging, destination)
            _fsync_directory(projects)
            return record
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def read_project(self, project_id: str) -> ProjectRecord:
        folder = self._folder(project_id)
        path = folder / 'project.json'
        if path.is_symlink() or path.stat().st_size > 8192:
            raise ValueError('unsafe project record')
        fields = json.loads(path.read_text())
        record = ProjectRecord(**fields)
        if record.id != project_id or record.sha256 != project_id:
            raise ValueError('project identity mismatch')
        return record

    def read_original(self, project_id: str) -> bytes:
        self.read_project(project_id)
        folder = self._folder(project_id)
        path = folder / 'original.bin'
        if path.is_symlink() or path.stat().st_size > 128 * 1024 * 1024:
            raise ValueError('unsafe original file')
        if path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError('original file is writable')
        data = path.read_bytes()
        if inspect_official(data).sha256 != project_id:
            raise ValueError('stored original identity mismatch')
        return data

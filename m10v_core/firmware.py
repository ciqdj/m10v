# SPDX-License-Identifier: GPL-2.0-only
"""Exact-identity GR III inspection. This module has no patch interface."""

from dataclasses import dataclass
from hashlib import sha256
import struct

from .codec.container import inspect_container
from .codec.frames import decode_payload, framed_container, section_rows
from .profile import GR3


class FirmwareIdentityError(ValueError):
    """The file cannot be identified as the one supported official baseline."""


@dataclass(frozen=True)
class SectionReport:
    name: str
    size: int
    sha256: str


@dataclass(frozen=True)
class FirmwareReport:
    model: str
    public_version: str
    internal_version: str
    sha256: str
    size: int
    sections: tuple[SectionReport, ...]
    proof: dict[str, bool]


def _checked(data: bytes):
    if len(data) != GR3.file_size:
        raise FirmwareIdentityError('size: unsupported firmware length')
    digest = sha256(data).hexdigest()
    if digest != GR3.sha256:
        raise FirmwareIdentityError('identity: full-file SHA-256 differs from the supported GR III baseline')
    try:
        info = inspect_container(data)
        if (info['project'], info['header_project_copy'], info['footer_project_copy']) != (
                GR3.project, GR3.project_copy, GR3.project_copy):
            raise FirmwareIdentityError('container: wrong project number')
        if (info['header_marker'], info['footer_marker'], info['firmware_type']) != (
                GR3.marker, GR3.marker, GR3.firmware_type):
            raise FirmwareIdentityError('container: wrong marker or firmware type')
        if info['additive_sum32'] != 0:
            raise FirmwareIdentityError('container: additive checksum failed')
        if (info['metadata_length'], info['header_record_count'], info['decoded_size']) != (
                GR3.metadata_length, GR3.metadata_record_count, GR3.decoded_size):
            raise FirmwareIdentityError('container: unsupported metadata or decoded length')
        decoded, frames = decode_payload(data[GR3.container_header_size:info['payload_end']],
                                         info['decoded_size'])
        rows = section_rows(decoded)
        if len(rows) != len(GR3.sections):
            raise FirmwareIdentityError('sections: unexpected count')
        position = 0
        sections = []
        for row, rule in zip(rows, GR3.sections):
            end = position + GR3.section_header_size + rule.payload_bytes
            if (row['name'], row['start'], row['end'], row['flags'], row.get('resource_count')) != (
                    rule.name, position, end, rule.flags, rule.resource_count):
                raise FirmwareIdentityError(f'sections: layout mismatch at {rule.name}')
            block = decoded[position:end]
            sections.append(SectionReport(rule.name, len(block), sha256(block).hexdigest()))
            position = end
        if position + GR3.decoded_checksum_size != len(decoded):
            raise FirmwareIdentityError('sections: decoded trailer mismatch')
        by_name = {row['name']: row for row in rows}

        def payload(name):
            row = by_name[name]
            return decoded[row['start'] + GR3.section_header_size:row['end']]

        rtos, cpu = payload('RTOS'), payload('CPU')
        if len(rtos) != GR3.rtos_size or sha256(rtos).hexdigest() != GR3.rtos_sha256:
            raise FirmwareIdentityError('rtos: unsupported baseline content')
        if struct.unpack_from('<3I', rtos, GR3.startup_offset) != GR3.startup_copy:
            raise FirmwareIdentityError('rtos: startup copy layout mismatch')
        for name, word in (
            ('rtos', int.from_bytes(rtos[GR3.rtos_version_offset:GR3.rtos_version_offset+4], 'big')),
            ('cpu', int.from_bytes(cpu[GR3.cpu_version_offset:GR3.cpu_version_offset+4], 'big')),
            *[(name, int.from_bytes(data[offset:offset+4], 'big'))
              for name, offset in GR3.outer_version_offsets],
        ):
            if word != GR3.version_word:
                raise FirmwareIdentityError(f'version: {name} differs')
        return info, decoded, frames, tuple(sections)
    except FirmwareIdentityError:
        raise
    except (ValueError, IndexError, KeyError, struct.error, UnicodeError) as exc:
        raise FirmwareIdentityError(f'parse: invalid GR III firmware: {exc}') from exc


def inspect_official(data: bytes) -> FirmwareReport:
    """Return facts only after full identity and structural checks pass."""
    if not isinstance(data, bytes):
        raise FirmwareIdentityError('input: firmware must be bytes')
    _, _, frames, sections = _checked(data)
    return FirmwareReport(
        GR3.model, GR3.public_version, GR3.internal_version,
        GR3.sha256, len(data), sections,
        {'identity': True, 'container': True, 'decoded': True,
         'sections': True, 'versions': True, 'strict_frames': bool(frames)},
    )


def _noop_repack(data: bytes) -> bytes:
    """Internal offline regression proof; never exposed through the HTTP API."""
    info, decoded, _, _ = _checked(data)
    payload = data[GR3.container_header_size:info['payload_end']]
    rebuilt = framed_container(data, payload, decoded)
    if rebuilt != data:
        raise FirmwareIdentityError('repack: no-op reconstruction differs from official bytes')
    return rebuilt

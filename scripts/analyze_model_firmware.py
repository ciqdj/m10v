#!/usr/bin/env python3
"""Read-only, exact-image inventories for model-port research.

Official firmware and extracted components stay in local ignored directories.
This entry point never installs a patch or emits modified update firmware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GR4_SHA = 'a2f664dfca034059eb0fd6e18ab08684c326b4a034d85c164dad7e1ec9b5655f'
GR4_BYTES = 38648776


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_gr4(data: bytes) -> dict:
    if len(data) != GR4_BYTES:
        raise ValueError('GR IV size differs from the supported official image')
    if digest(data) != GR4_SHA:
        raise ValueError('GR IV identity differs from the supported official image')
    sys.path.insert(0, str(ROOT / 'vendor/gr4'))
    from gr4_editor.firmware import _load_bytes, _repack_frames
    from gr4_editor.codec.frames import framed_container
    image = _load_bytes(data)
    payload, replay = _repack_frames(data, image.decoded, image.decoded, False)
    repacked = framed_container(data, payload, image.decoded)
    if repacked != data:
        raise ValueError('GR IV unmodified repack differs from input')
    sections = []
    for section in image.sections:
        body = image.decoded[section['start'] + 16:section['end']]
        sections.append({**section, 'sha256': digest(body)})
    return {
        'schema': 'm10v-model-firmware-inventory/v1',
        'model': 'GR IV', 'public_version': '1.11',
        'internal_version': image.internal_version, 'sha256': digest(data),
        'size': len(data), 'decoded_bytes': len(image.decoded),
        'frames': image.layout_proof['frames'], 'sections': sections,
        'container': image.container,
        'proof': {**image.layout_proof, 'byte_exact_roundtrip': True,
                  'repack': replay},
        'hardware_tested': False,
        'port': {
            'rtos_load_base': '0x53000000',
            'native_film_runtime': 'not_ported',
            'reference_color_resources': 'known_exact_source',
            'capture_abi': 'requires_independent_trace',
            'persistence_abi': 'requires_independent_trace',
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--model', choices=('gr4',), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--extract', action='store_true')
    args = parser.parse_args()
    data = args.input.read_bytes()
    result = inspect_gr4(data)
    destination = args.out.resolve()
    source = args.input.resolve()
    if destination == source or destination in source.parents:
        raise ValueError('output must not overwrite or contain the official input')
    destination.mkdir(parents=True, exist_ok=True)
    if args.extract:
        from gr4_editor.firmware import _load_bytes
        image = _load_bytes(data)
        for row in image.sections:
            target = destination / (row['name'] + '.bin')
            if target.resolve() == source:
                raise ValueError('component output would overwrite the input')
            target.write_bytes(image.decoded[row['start'] + 16:row['end']])
    report_path = destination / 'inventory.json'
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'model': result['model'], 'report': str(report_path),
                      'sha256': result['sha256'], 'roundtrip': True}))


if __name__ == '__main__':
    main()

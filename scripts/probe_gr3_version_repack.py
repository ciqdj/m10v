"""Memory-only version-field/checksum arithmetic probe; never saves a BIN."""

from hashlib import sha256
import json
from pathlib import Path
import sys

from m10v_core.codec.container import repair_last_word
from m10v_core.codec.frames import section_rows
from m10v_core.firmware import _checked
from gr3_probe_codec import repack_probe


def main(path: Path):
    original = path.read_bytes()
    _, decoded, frames, _ = _checked(original)
    rows = {row['name']: row for row in section_rows(decoded)}
    old, new = bytes.fromhex('020a151b'), bytes.fromhex('020a151c')
    target = bytearray(decoded)
    sites = []
    for name, offset in [('RTOS', 0x2038), ('CPU', 0x90)]:
        position = rows[name]['start'] + 16 + offset
        if target[position:position + 4] != old:
            raise ValueError(f'{name} version differs')
        target[position:position + 4] = new
        sites.append(position)

    cpu_start = rows['CPU']['start'] + 16
    cpu = memoryview(target)[cpu_start:cpu_start + 0x20000]
    cpu_checksum_offset = 0x7c
    total = 0
    for offset in range(0, len(cpu), 4):
        if offset != cpu_checksum_offset:
            total = (total + int.from_bytes(cpu[offset:offset + 4], 'big')) & 0xffffffff
    cpu[cpu_checksum_offset:cpu_checksum_offset + 4] = ((-total) & 0xffffffff).to_bytes(4, 'big')
    if sum(int.from_bytes(cpu[i:i + 4], 'big') for i in range(0, len(cpu), 4)) & 0xffffffff:
        raise ValueError('CPU checksum repair failed')
    del cpu
    target = repair_last_word(target)

    template = bytearray(original)
    for offset in (0x38, 0x50):
        if template[offset:offset + 4] != old:
            raise ValueError('outer version differs')
        template[offset:offset + 4] = new
    candidate, codec = repack_probe(bytes(template), decoded, frames, target)
    if any(candidate[offset:offset + 4] != new for offset in (0x38, 0x50)):
        raise ValueError('outer version readback differs')
    permitted = {byte for position in sites for byte in range(position, position + 4)}
    permitted.update(range(cpu_start + cpu_checksum_offset, cpu_start + cpu_checksum_offset + 4))
    permitted.update(range(len(target) - 4, len(target)))
    differences = [i for i, (a, b) in enumerate(zip(decoded, target)) if a != b]
    if any(i not in permitted for i in differences):
        raise ValueError('decoded version probe changed unexpected bytes')
    print(json.dumps({
        'source_sha256': sha256(original).hexdigest(),
        'probe_only': True, 'candidate_saved': False,
        'old_internal_version': '2.10.21.27',
        'probe_internal_version': '2.10.21.28',
        'outer_version_offsets': ['0x38', '0x50'],
        'decoded_version_offsets': [hex(position) for position in sites],
        'cpu_checksum_offset': '0x7c',
        'cpu_checksum_word': hex(int.from_bytes(
            target[cpu_start + cpu_checksum_offset:cpu_start + cpu_checksum_offset + 4], 'big')),
        'source_bytes': len(original), 'probe_container_bytes': len(candidate),
        'decoded_differences': len(differences),
        **codec,
    }, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1] if len(sys.argv) > 1 else 'fwdc239b.bin'))

"""Memory-only GR III RES frame-repack probe; never writes a candidate BIN.

Mutates one JPEG payload byte solely to exercise encoder/checksum roundtrip.
Passing this probe does not establish camera update or JPEG decode acceptance.
"""
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
    rows = section_rows(decoded)
    res = next(row for row in rows if row['name'] == 'RES')
    cursor = res['start'] + 16
    target_path = b'B:\\Resource\\Jpeg\\Collabo.jpg'
    target = bytearray(decoded)
    modified_at = None
    for _ in range(res['resource_count']):
        name = bytes(decoded[cursor:cursor + 32]).split(b'\0', 1)[0]
        size = int.from_bytes(decoded[cursor + 32:cursor + 36], 'little')
        end = cursor + 36 + size
        if end > res['end']:
            raise ValueError('RES record exceeds section')
        if name == target_path:
            if size != 111155:
                raise ValueError('Collabo length differs')
            modified_at = cursor + 36 + 1000
            target[modified_at] ^= 1
        cursor = end
    if modified_at is None or cursor != res['end']:
        raise ValueError('Collabo or RES layout differs')

    target = repair_last_word(target)
    candidate, codec = repack_probe(original, decoded, frames, target)
    for row in rows:
        if row['name'] != 'RES' and decoded[row['start']:row['end']] != target[row['start']:row['end']]:
            raise ValueError('non-RES section changed')
    differences = [i for i, (before, after) in enumerate(zip(decoded, target)) if before != after]
    # Some checksum bytes can remain equal after repair. All differences must
    # be restricted to the JPEG byte and decoded checksum word.
    if modified_at not in differences or any(i != modified_at and i < len(target) - 4
                                             for i in differences):
        raise ValueError('decoded changes escaped the allowed coordinates')
    print(json.dumps({
        'source_sha256': sha256(original).hexdigest(),
        'probe_only': True, 'candidate_saved': False,
        'modified_decoded_offset': hex(modified_at),
        'source_bytes': len(original), 'probe_container_bytes': len(candidate),
        'decoded_differences': len(differences),
        **codec,
    }, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1] if len(sys.argv) > 1 else 'fwdc239b.bin'))

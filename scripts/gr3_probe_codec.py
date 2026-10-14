"""In-memory frame replay for exact-baseline GR III research probes."""

from m10v_core.codec.container import inspect_container, sum32
from m10v_core.codec.frames import (
    FrameError, _decode_body, _literal_chunks, decode_payload, framed_container,
)


def repack_probe(template: bytes, decoded: bytes, frames, target: bytes):
    if len(target) != len(decoded) or sum32(target) != 0:
        raise ValueError('probe decoded shape or checksum differs')
    info = inspect_container(template)
    source_payload = template[128:info['payload_end']]
    encoded, output = bytearray(), bytearray()
    reused = replaced = generated = 0
    for frame in frames:
        desired = target[frame.decoded_start:frame.decoded_end]
        raw = source_payload[frame.encoded_start:frame.encoded_end]
        start = len(output)
        exact = False
        try:
            _decode_body(raw[2:], frame.literal, output, start + len(desired))
            exact = output[start:] == desired
        except FrameError:
            pass
        if exact:
            encoded.extend(raw)
            reused += 1
        else:
            del output[start:]
            literal, count = _literal_chunks(desired)
            encoded.extend(literal)
            output.extend(desired)
            generated += count
            replaced += 1
    encoded.extend(b'\0\0')
    if bytes(output) != target or decode_payload(encoded, len(target))[0] != target:
        raise ValueError('frame probe decode differs')
    candidate = framed_container(template, encoded, target)
    candidate_info = inspect_container(candidate)
    if candidate_info['additive_sum32'] != 0 or (
        decode_payload(candidate[128:candidate_info['payload_end']], len(target))[0] != target
    ):
        raise ValueError('container probe decode or checksum differs')
    return candidate, {
        'reused_frames': reused, 'replaced_frames': replaced,
        'generated_literal_frames': generated,
        'container_sum32': candidate_info['additive_sum32'],
        'decoded_sum32': sum32(target), 'fresh_decode_exact': True,
    }

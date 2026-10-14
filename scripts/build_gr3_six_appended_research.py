"""Reproduce the six-film GR III research candidate; never a product export.

Requires sibling gr3-film-mods/gr-custom-tool checkouts and Homebrew llvm.
The v16 RAW/EXIF routines are loaded without its missing GR IV MultiAxial table.
Camera persistence, playback, effect dispatch and return-to-stock are unverified.
"""
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT.parent / 'gr3-film-mods'
SOURCE = ROOT / 'fwdc239b.bin'
DEST = ROOT / 'builds/gr3-extension-validation/six-appended-rawdev-research.bin'
SOURCE_SHA = 'd6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4'
BUILDER_SHA = '30f44121bb151865c2a953e2fb12a89e33380016326e40d2f98e7b78926831c2'
RAW_DEV_SHA = '7ee4e90f65a2c87a1558ef8cd4818889471e66642ee54aaa489b0a9dd03983e5'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if sha(SOURCE.read_bytes()) != SOURCE_SHA:
        raise RuntimeError('official GR III 2.10 source differs')
    if sha((UPSTREAM / 'make_slots.py').read_bytes()) != BUILDER_SHA or \
            sha((UPSTREAM / 'make_slots16.py').read_bytes()) != RAW_DEV_SHA:
        raise RuntimeError('research source version differs')
    os.environ.setdefault('GR_CUSTOM_TOOL', str(ROOT.parent / 'gr-custom-tool'))
    sys.path.insert(0, str(UPSTREAM))
    import make_slots as m13
    import make_slots15 as m15
    from gr3patch import Image, BASE
    from gr4_editor.codec.container import repair_last_word, sum32
    from gr4_editor.codec.frames import framed_container
    from gr4_editor.firmware import _repack_frames

    # v16 imports the absent GR IV table at module load; only its independent
    # RAW development and EXIF routines are used in this source-locked probe.
    code = (UPSTREAM / 'make_slots16.py').read_text()
    functions = 'RD_CONV, RD_TONE' + code.split('RD_CONV, RD_TONE', 1)[1].split(
        "if __name__ == '__main__':", 1)[0]
    scope = {'M15': m15, 'struct': struct, 'code': m15.code, 'put': m15.put, 'B': m15.B}
    exec(compile(functions, str(UPSTREAM / 'make_slots16.py'), 'exec'), scope)

    fits = UPSTREAM / 'work'
    choices = [
        ('portra', 'Portra 400', fits / 'films_v11/fits/portra_b4n3_lab.json'),
        ('ektar', 'Ektar 100', fits / 'films_v11/fits/ektar_b1n3_lab.json'),
        ('gold', 'Gold 200', fits / 'films_v11/fits/gold_b4n3_lab.json'),
        ('pro400h', 'Pro 400H', fits / 'films_v11/fits/pro400h_own_b4n3_lab.json'),
        ('vision3', 'Vision3 250D', fits / 'films_v11/fits/vision3250d_2383_b4n3_lab.json'),
        ('classicneg', 'Classic Neg', fits / 'films_v12/fits/classicneg_b4n3_lab.json'),
    ]
    films = [(key, name, json.loads(path.read_text())) for key, name, path in choices]
    image = Image(str(SOURCE))
    info = m13.patch(image, films)
    old_end = image.rtos_end
    growth = 0x4000
    image.target[old_end:old_end] = bytes(growth)
    image.rtos_end += growth
    struct.pack_into('<I', image.target, image.rtos0 - 4, image.rtos_end - image.rtos0)
    new_va = BASE + old_end - image.rtos0
    extra = m15.Space([(new_va, new_va + growth)])
    m15.FALLBACK.clear()
    m15.FALLBACK.append(extra)
    proxy = extra.take(len(films), 'proxy table')
    image.write(proxy, bytes(len(films)))
    info['_code']['space'].append(('proxy table', hex(proxy), len(films)))
    extended = [(key, name, fit, None) for key, name, fit in films]
    raw = scope['patch_rawdev'](image, extended, info)
    exif = scope['patch_exif_tone'](image, extended)
    target = repair_last_word(bytes(image.target))
    if sum32(target) != 0:
        raise RuntimeError('decoded checksum differs')
    payload, replay = _repack_frames(image.candidate, image.original, target, growth=True)
    candidate = framed_container(image.candidate, payload, target)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(candidate)
    print(json.dumps({'status': 'OFFLINE_RESEARCH_ONLY', 'path': str(DEST),
                      'sha256': sha(candidate), 'rtos_growth': growth,
                      'raw_enums': raw['enums'], 'image_tone': exif['codes'],
                      'frame_replay': replay['fresh_history_roundtrip_exact'],
                      'camera_tested': False, 'settings_persistence_verified': False}))


if __name__ == '__main__':
    main()

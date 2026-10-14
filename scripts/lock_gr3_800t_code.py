"""Refresh reviewed native code bytes after running ARM validation/review."""
import hashlib
import json
import tempfile
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_gr3_camera_adapter import build_adapter
from scripts.build_gr3_halation import ROOT, build
from scripts.build_gr3_menu_patches import build_menu_patches


def make_lock():
    with tempfile.TemporaryDirectory() as folder:
        manifest = build(folder)
        core = (Path(folder) / 'halation-arm.bin').read_bytes()
    adapters = {}
    for slot, tone in {'vivid': 12, 'bleach': 18, 'retro': 19, 'hdr': 20, 'cross': 21}.items():
        for strength, name in ((1, 'weak'), (2, 'strong')):
            code = build_adapter(1, tone, strength)
            adapters[slot + '/' + name] = {'hex': code.hex(), 'sha256': hashlib.sha256(code).hexdigest(), 'bytes': len(code)}
    extension,patches,report=build_menu_patches(Path('/tmp/m10v-800t-analysis/rtos.bin').read_bytes())
    sources = ['native/gr3/menu_controls.c','scripts/build_gr3_menu_controls.py','scripts/build_gr3_menu_patches.py','native/gr3/halation_camera.c', 'native/gr3/halation_controls.h', 'native/gr3/halation_core.c', 'native/gr3/halation_core.h',
               'scripts/build_gr3_camera_adapter.py', 'scripts/build_gr3_halation.py']
    return {'schema': 'm10v-gr3-800t-code-lock/v1',
            'sources': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources},
            'kernel': {'hex': core.hex(), 'sha256': manifest['codeSha256'], 'bytes': len(core)},
            'adapters': adapters,'menu':{'hex':extension.hex(),'bytes':len(extension),'sha256':hashlib.sha256(extension).hexdigest(),'patches':patches,'report':report}}


if __name__ == '__main__':
    (ROOT / 'native/gr3/800t-code-lock.json').write_text(json.dumps(make_lock(), indent=2) + '\n')

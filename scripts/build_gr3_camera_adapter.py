"""Compile a research capture adapter with an explicit, unproved camera order."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from scripts.build_gr3_halation import ROOT, FLAGS, extract_text
ADAPTER_FLAGS = ['-Os' if flag == '-O2' else flag for flag in FLAGS]


def build_adapter(order, tone, strength):
    if order not in (1, 2) or tone not in (12, 18, 19, 20, 21) or strength not in (1, 2):
        raise ValueError('invalid research capture configuration')
    with tempfile.TemporaryDirectory(prefix='m10v-camera-') as folder:
        obj = Path(folder) / 'adapter.o'
        subprocess.run(['clang', *ADAPTER_FLAGS, f'-DM10V_CAMERA_ORDER={order}',
                        f'-DM10V_CAMERA_TONE={tone}', f'-DM10V_CAMERA_STRENGTH={strength}',
                        '-c', str(ROOT / 'native/gr3/halation_camera.c'), '-o', str(obj)],
                       check=True, capture_output=True)
        code = extract_text(obj.read_bytes(), 'm10v_capture_800t')
    if len(code) > 0x800 - 0x20:
        raise ValueError('capture adapter overlaps fixed core placement')
    return code

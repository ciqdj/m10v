"""800T container constructor for the exact offline-verified still contract.

The public platform fixes order1 from original CPU evidence. Order2 is only
available to the research CLI. Every container requires independent decoding.
"""
import hashlib
import json
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_gr3_camera_adapter import build_adapter, ADAPTER_FLAGS
from scripts.build_gr3_halation import build as build_kernel
from scripts.analyze_gr3_800t_mapping import inspect_mapping
from scripts.build_gr3_menu_patches import build_menu_patches
from reconstruction.firmware_store.browser_engine import _template, _program, _timestamp_tune
from reconstruction.firmware_store.profile import inspect_official_source
from reconstruction.firmware_store.hook_compiler import collect_feature_hooks
from reconstruction.firmware_store.film_component import film_patches
from reconstruction.firmware_store.patch_registry import PatchPlanRegistry
from reconstruction.firmware_store.extended_container import rebuild_extended_rtos
from reconstruction.firmware_patch import PatchSpec
from reconstruction.icon_resources import RTOS_PAYLOAD_OFFSET, ICONBIN_PAYLOAD_OFFSET, ICONBIN_PAYLOAD_SIZE

TONES = {'vivid': 12, 'bleach': 18, 'retro': 19, 'hdr': 20, 'cross': 21}


def construct_800t(source, prepared, order):
    checked = inspect_official_source(source)
    if checked.profile_id != 'gr3-2.10' or prepared['source_sha256'] != checked.source_sha256:
        raise ValueError('800T requires exact GR III 2.10 source')
    mapping = inspect_mapping(checked.rtos)
    configuration = prepared['configuration']
    strength = {'weak': 1, 'strong': 2}[configuration['strength']]
    adapter = build_adapter(order, TONES[configuration['slot']], strength)
    with tempfile.TemporaryDirectory(prefix='m10v-800t-core-') as folder:
        kernel_manifest = build_kernel(folder)
        core = (Path(folder) / 'halation-arm.bin').read_bytes()
    template, linked = _template()
    timestamp = configuration['timestamp']
    features = ('timestamp',) if timestamp else ()
    tune = _timestamp_tune(template) if timestamp else None
    base, _ = _program(template, [], features, tune=tune)
    program = bytearray(base + bytes(49152 - len(base)))
    if len(program) != 49152 or any(program[0x5000:]):
        raise ValueError('800T research extension placement is occupied')
    expected_call = bytes.fromhex('b30300eb' if timestamp else '45f7ffeb')
    if program[0x3380:0x3384] != expected_call:
        raise ValueError('capture trampoline call preimage differs')
    struct.pack_into('<I', program, 0x3380, 0xeb00071e)
    # Called inside the original all-register/APSR-preserving trampoline.
    chain = [0xe92d4010, 0xe1a04000, 0xeb000004, 0xe1a00004, 0xe8bd4010]
    chain += [0xe51ff004, 0x540ba254] if timestamp else [0xe12fff1e]
    program[0x5000:0x5000 + 4 * len(chain)] = struct.pack('<' + 'I' * len(chain), *chain)
    program[0x5020:0x5020 + len(adapter)] = adapter
    if 0x5800 + len(core) > 0x6800:
        raise ValueError('800T kernel exceeds extension page')
    program[0x5800:0x5800 + len(core)] = core
    patches = list(collect_feature_hooks(checked.reference_rtos(), linked, features)) if features else []
    if not timestamp:
        patches.append(PatchSpec(offset=RTOS_PAYLOAD_OFFSET + 0x5048e8,
                                 expected=bytes.fromhex('0e9d06eb'), replacement=bytes.fromhex('9fd22eeb'),
                                 label='800T research capture trampoline', provenance='exact GR III capture call'))
    icons = checked.decoded[ICONBIN_PAYLOAD_OFFSET:ICONBIN_PAYLOAD_OFFSET + ICONBIN_PAYLOAD_SIZE]
    patches.extend(film_patches(checked.reference_rtos(), icons, prepared['color_plan'].get('custom', [])))
    menu_report=None
    if configuration['slot']=='bleach':
        menu_extension,menu_patches,menu_report=build_menu_patches(checked.rtos)
        program[0x8000:]=menu_extension
        patches.extend(PatchSpec(offset=RTOS_PAYLOAD_OFFSET+row['address']-0x53000000,
            expected=bytes.fromhex(row['expected']),replacement=bytes.fromhex(row['replacement']),
            label=row['label'],provenance='reviewed dedicated 800T controls') for row in menu_patches)
    for patch in patches:
        if any(patch.offset < end and start < patch.offset + len(patch.expected)
               for start, end in checked.identity_spans()):
            raise ValueError('800T patch overlaps model identity')
    registry = PatchPlanRegistry(checked.decoded, allowed_ranges=checked.allowed_ranges)
    registry.register('800t-research', 'RTOS', tuple(p for p in patches if p.offset < ICONBIN_PAYLOAD_OFFSET))
    registry.register('800t-icons', 'ICONBIN', tuple(p for p in patches if p.offset >= ICONBIN_PAYLOAD_OFFSET))
    frozen = registry.freeze()
    candidate, structural = rebuild_extended_rtos(source, tail_offset=template['tail_offset'],
                                                  tail=bytes(program), patches=frozen.patches,
                                                  locks=checked.profile.locks)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    expectation = {'schema': 'm10v-gr3-800t-expected-bytes/v1', 'source_sha256': checked.source_sha256,
                   'configuration_sha256': prepared['configuration_sha256'],
                   'tail_offset': template['tail_offset'], 'tail_hex': program.hex(),
                   'patches': [{'offset': p.offset, 'expected_hex': p.expected.hex(),
                                'replacement_hex': p.replacement.hex()} for p in frozen.patches]}
    receipt = {'schema': 'm10v-gr3-800t-research-build/v1',
               'status': ('OFFLINE_VERIFIED_EXPERIMENTAL_CANDIDATE' if order == 1 else
                          'RESEARCH_CONTAINER_CAMERA_ORDER_UNPROVED'), 'camera_tested': False,
               'candidate_sha256': sha(candidate), 'configuration': configuration,
               'research_chroma_order': order, 'kernel': kernel_manifest,
               'adapter_sha256': sha(adapter), 'adapter_bytes': len(adapter), 'adapter_flags': ADAPTER_FLAGS,
               'startup_mapping': mapping, 'container': structural, 'independent_menu':menu_report,
               'dng_preview_may_share_jpeg_effect': True}
    return candidate, receipt, expectation


if __name__ == '__main__':
    source_path, preparation_path, output_path, order = sys.argv[1:]
    candidate, receipt, expectation = construct_800t(Path(source_path).read_bytes(),
                                                     json.loads(Path(preparation_path).read_text()), int(order))
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(candidate)
    out.with_suffix('.research.json').write_text(json.dumps(receipt, indent=2) + '\n')
    out.with_suffix('.expected.json').write_text(json.dumps(expectation, indent=2) + '\n')
    print(json.dumps(receipt))

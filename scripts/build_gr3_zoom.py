"""Preimage-checked GR III two-slot focal runtime, with no writable globals."""
import hashlib
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['m10v_zoom.c',
 'm10v_zoom_camera.c',
 'm10v_zoom_menu.c',
 'm10v_zoom_live.c',
 'm10v_zoom_live.S',
 'm10v_zoom_capture.c',
 'm10v_zoom_capture_adapters.c',
 'm10v_zoom_capture_hooks.S']
EXPORTS=['m10v_zoom_adjust',
 'm10v_zoom_bits',
 'm10v_zoom_camera_bits',
 'm10v_zoom_camera_load',
 'm10v_zoom_camera_save',
 'm10v_zoom_camera_select',
 'm10v_zoom_camera_slot',
 'm10v_zoom_caption',
 'm10v_zoom_capture_caption',
 'm10v_zoom_capture_caption_hook',
 'm10v_zoom_capture_custom',
 'm10v_zoom_capture_geometry',
 'm10v_zoom_capture_icon_hook',
 'm10v_zoom_capture_marker_decode',
 'm10v_zoom_capture_marker_encode',
 'm10v_zoom_capture_marker_read',
 'm10v_zoom_capture_marker_summary',
 'm10v_zoom_capture_marker_write',
 'm10v_zoom_capture_native_resolution',
 'm10v_zoom_capture_quality_count',
 'm10v_zoom_capture_quality_value',
 'm10v_zoom_capture_raw_bits',
 'm10v_zoom_capture_raw_count',
 'm10v_zoom_capture_raw_value',
 'm10v_zoom_capture_replay_rect',
 'm10v_zoom_capture_resolution',
 'm10v_zoom_capture_resolution_hook',
 'm10v_zoom_cycle',
 'm10v_zoom_label_adj',
 'm10v_zoom_label_live',
 'm10v_zoom_label_menu',
 'm10v_zoom_label_slot',
 'm10v_zoom_live_apply',
 'm10v_zoom_load',
 'm10v_zoom_menu_key',
 'm10v_zoom_menu_open',
 'm10v_zoom_mm',
 'm10v_zoom_native_back_bits',
 'm10v_zoom_native_front_bits',
 'm10v_zoom_native_set_bits',
 'm10v_zoom_open',
 'm10v_zoom_save',
 'm10v_zoom_selected',
 'm10v_zoom_set',
 'm10v_zoom_title']
LIVE_HOOKS=[{'address': 1394306032,
  'link': False,
  'preimage': 3785408525,
  'symbol': 'm10v_zoom_set'},
 {'address': 1394216456,
  'link': False,
  'preimage': 3785408525,
  'symbol': 'm10v_zoom_set'},
 {'address': 1394311972,
  'link': False,
  'preimage': 3809030612,
  'symbol': 'm10v_zoom_selected'},
 {'address': 1394217552,
  'link': False,
  'preimage': 3785408525,
  'symbol': 'm10v_zoom_selected'},
 {'address': 1394766264,
  'link': False,
  'preimage': 3785408525,
  'symbol': 'm10v_zoom_cycle'},
 {'address': 1394178308,
  'link': True,
  'preimage': 3942927191,
  'symbol': 'm10v_zoom_label_live'},
 {'address': 1394298456,
  'link': True,
  'preimage': 3942897154,
  'symbol': 'm10v_zoom_label_menu'},
 {'address': 1394226344,
  'link': True,
  'preimage': 3942915182,
  'symbol': 'm10v_zoom_label_adj'}]
CAPTURE_HOOKS=[{'address': 1399466544,
  'fallback_existing_address': 1410045008,
  'fallback_symbol': 'm10v_zoom_original_resolution',
  'official_preimage_hex': 'f87adfed',
  'symbol': 'm10v_zoom_capture_resolution_hook',
  'trampoline_original_instruction_then_branch': None},
 {'address': 1398819608,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_marker_write',
  'official_preimage_hex': '1c3090e5',
  'symbol': 'm10v_zoom_capture_marker_write',
  'trampoline_original_instruction_then_branch': 1398819612},
 {'address': 1398534140,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_marker_read',
  'official_preimage_hex': '0dc0a0e1',
  'symbol': 'm10v_zoom_capture_marker_read',
  'trampoline_original_instruction_then_branch': 1398534144},
 {'address': 1398548380,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_marker_summary',
  'official_preimage_hex': '0dc0a0e1',
  'symbol': 'm10v_zoom_capture_marker_summary',
  'trampoline_original_instruction_then_branch': 1398548384},
 {'address': 1395144448,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_raw_count',
  'official_preimage_hex': '0dc0a0e1',
  'symbol': 'm10v_zoom_capture_raw_count',
  'trampoline_original_instruction_then_branch': 1395144452},
 {'address': 1395144588,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_raw_value',
  'official_preimage_hex': '0dc0a0e1',
  'symbol': 'm10v_zoom_capture_raw_value',
  'trampoline_original_instruction_then_branch': 1395144592},
 {'address': 1395303600,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_crop_icon',
  'official_preimage_hex': '0dc0a0e1',
  'symbol': 'm10v_zoom_capture_icon_hook',
  'trampoline_original_instruction_then_branch': 1395303604},
 {'address': 1395304040,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_crop_caption',
  'official_preimage_hex': '0dc0a0e1',
  'symbol': 'm10v_zoom_capture_caption_hook',
  'trampoline_original_instruction_then_branch': 1395304044},
 {'address': 1398728848,
  'fallback_existing_address': None,
  'fallback_symbol': 'm10v_zoom_original_replay_rect',
  'official_preimage_hex': '0dc0a0e1',
  'symbol': 'm10v_zoom_capture_replay_rect',
  'trampoline_original_instruction_then_branch': 1398728852}]
BINDINGS={'__aeabi_uidiv': 1393809488,
 'm10v_zoom_native_ifd_byte': 1398604988,
 'm10v_zoom_native_ifd_write_byte': 1398604468,
 'm10v_zoom_native_raw_mag': 1395144364,
 'm10v_zoom_native_summary_write': 1398530152}

def build(base, stock, aspect=False):
    from scripts.build_gr3_m10v_library import FLAGS,link_object
    from scripts.build_gr3_menu_patches import branch
    for hook in [*LIVE_HOOKS,*CAPTURE_HOOKS]:
        address=hook['address']
        expected=hook.get('preimage')
        if expected is None:expected=int.from_bytes(bytes.fromhex(hook['official_preimage_hex']),'little')
        if struct.unpack_from('<I',stock,address-0x53000000)[0]!=expected:
            raise ValueError(f'zoom hook preimage differs at {address:#x}')
    image=bytearray();bindings=dict(BINDINGS)
    for hook in CAPTURE_HOOKS:
        name=hook['fallback_symbol'];address=hook['address']
        if name=='m10v_zoom_original_resolution' and aspect:
            bindings[name]=0x540b9450
            continue
        entry=base+len(image);bindings[name]=entry
        original=struct.unpack_from('<I',stock,address-0x53000000)[0]
        if name=='m10v_zoom_original_resolution':
            # PC-relative VLDR s15 is the native displaced instruction.
            # Keep its exact literal value and all registers intact.
            if original!=0xeddf7af8:raise ValueError('resolution VLDR preimage differs')
            literal=struct.unpack_from('<I',stock,address-0x53000000+8+0xf8*4)[0]
            image+=struct.pack('<III',0xeddf7a00,branch(entry+4,address+4),literal)
        else:
            image+=struct.pack('<II',original,branch(entry+4,address+4))
    clang=os.environ.get('M10V_LLVM_CLANG') or shutil.which('clang')
    lld=os.environ.get('M10V_LLVM_LD') or shutil.which('ld.lld')
    if not lld:
        lld=next((p for p in ['/opt/homebrew/opt/lld/bin/ld.lld','/usr/local/opt/lld/bin/ld.lld'] if Path(p).exists()),None)
    if not clang or not lld:raise ValueError('zoom build requires clang and ld.lld')
    with tempfile.TemporaryDirectory(prefix='m10v-zoom-') as tmp:
        folder=Path(tmp);objects=[]
        for name in SOURCES:
            obj=folder/(name+'.o')
            subprocess.run([clang,*FLAGS,'-c',str(ROOT/'native/gr3'/name),'-o',str(obj)],check=True,capture_output=True)
            objects.append(str(obj))
        linked=folder/'zoom.o'
        subprocess.run([lld,'-r',*objects,'-o',str(linked)],check=True,capture_output=True)
        image+=bytes(-len(image)&15)
        code,symbols=link_object(linked.read_bytes(),base+len(image),bindings,'m10v_zoom_',additional_exports=EXPORTS)
        image+=code
    patches=[]
    for hook in [*LIVE_HOOKS,*CAPTURE_HOOKS]:
        expected=hook.get('preimage')
        if expected is None:expected=int.from_bytes(bytes.fromhex(hook['official_preimage_hex']),'little')
        address=hook['address']
        patches.append(dict(address=address,expected=expected,
            replacement=branch(address,symbols[hook['symbol']],hook.get('link',False)),name=hook['symbol']))
    sources=['native/gr3/'+name for name in SOURCES]
    sources+=['native/gr3/m10v_zoom.h','native/gr3/m10v_zoom_camera.h',
              'native/gr3/m10v_zoom_menu.h','native/gr3/m10v_zoom_capture.h','scripts/build_gr3_zoom.py','node/gr3-zoom.mjs']
    return bytes(image),dict(schema='m10v-gr3-zoom/v1',base=base,bytes=len(image),
        symbols=symbols,bindings=bindings,patches=patches,aspect=aspect,
        slots=2,min_mm=28,max_mm=100,title_id=1024,focal_first_id=1031,
        sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources},camera_tested=False)

"""Compile and link the original M10V runtime; this emits no camera firmware."""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
FLAGS = ['--target=armv7-none-eabi', '-mcpu=cortex-a9', '-marm', '-mfloat-abi=soft',
         '-Os', '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
         '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
         '-fno-vectorize', '-fno-slp-vectorize', '-Wall', '-Wextra', '-Werror']


def link_object(elf, base, externals=None, prefix='m10v_library_'):
    """Bounded ELF32 ARM relocator for our freestanding .text/.rodata module.

    Unknown sections, symbols, addends or relocation kinds fail closed. This
    does not invoke or imitate any third-party camera-mod linker/template.
    """
    if elf[:7] != b'\x7fELF\x01\x01\x01' or struct.unpack_from('<HH', elf, 16) != (1, 40):
        raise ValueError('expected a relocatable little-endian ARM ELF32')
    shoff = struct.unpack_from('<I', elf, 32)[0]
    entsize, count, names_index = struct.unpack_from('<HHH', elf, 46)
    if entsize != 40 or shoff + entsize * count > len(elf) or names_index >= count:
        raise ValueError('invalid section directory')
    sections = [struct.unpack_from('<10I', elf, shoff + i * entsize) for i in range(count)]
    names_row = sections[names_index]; names = elf[names_row[4]:names_row[4] + names_row[5]]
    image_sections = []; symbols = {}; starts = {}; cursor = base; tables = {}
    for index, row in enumerate(sections):
        name = names[row[0]:].split(b'\0', 1)[0].decode('ascii')
        if row[2] & 2 and row[5]:
            if name.startswith('.ARM.exidx'): continue
            if row[1] != 1 or row[2] & 1 or not (name in ('.text', '.rodata') or name.startswith('.rodata.')) or row[8] > 16 or not row[8]:
                raise ValueError('unexpected allocated section: ' + name)
            cursor = (cursor + row[8] - 1) & ~(row[8] - 1)
            starts[index] = cursor; image_sections.append((index, row)); cursor += row[5]
            if cursor > base + 65536: raise ValueError('runtime exceeds code budget')
    image = bytearray((cursor - base + 3) & ~3)
    for index, row in image_sections:
        at = starts[index] - base
        image[at:at + row[5]] = elf[row[4]:row[4] + row[5]]
    for index, row in enumerate(sections):
        if row[1] != 2: continue
        strings_row = sections[row[6]]; strings = elf[strings_row[4]:strings_row[4] + strings_row[5]]
        table = []
        for at in range(row[4], row[4] + row[5], 16):
            n, value, size, info, other, section = struct.unpack_from('<IIIBBH', elf, at)
            symbol = strings[n:].split(b'\0', 1)[0].decode('ascii')
            if section == 0 and symbol and symbol not in (externals or {}):
                raise ValueError('undefined symbol: ' + symbol)
            address = starts[section] + value if section in starts else (externals or {}).get(symbol)
            table.append((symbol, address))
            if symbol.startswith(prefix) and info & 15 == 2 and section in starts:
                if address is None or not base <= address < base + 65536 or address & 3:
                    raise ValueError('invalid ARM entry')
                symbols[symbol] = address
        tables[index] = table
    for row in sections:
        if row[1] not in (4, 9) or not row[5] or row[7] not in starts: continue
        if row[1] != 9 or row[9] != 8 or row[6] not in tables: raise ValueError('unsupported relocation directory')
        target = row[7]
        for at in range(row[4], row[4] + row[5], 8):
            offset, info = struct.unpack_from('<II', elf, at); symbol_index, kind = info >> 8, info & 255
            if offset & 3 or offset + 4 > sections[target][5] or symbol_index >= len(tables[row[6]]):
                raise ValueError('relocation out of range')
            name, value = tables[row[6]][symbol_index]
            if value is None: raise ValueError('relocation targets unloaded section: ' + name)
            place = starts[target] + offset; out_at = place - base
            word = struct.unpack_from('<I', image, out_at)[0]
            if kind == 2:  # R_ARM_ABS32: compiler-generated local ARM switch labels only
                target_address = value + word
                text_ranges = [(starts[i], starts[i]+s[5]) for i,s in image_sections
                               if names[s[0]:].split(b'\0',1)[0] == b'.text']
                if target_address & 3 or not any(lo <= target_address < hi for lo,hi in text_ranges):
                    raise ValueError('absolute switch relocation leaves local ARM text')
                word = target_address
            elif kind in (28, 29):  # R_ARM_CALL / R_ARM_JUMP24
                if word & 0x0f000000 != (0x0b000000 if kind == 28 else 0x0a000000):
                    raise ValueError('branch relocation is not ARM B/BL')
                addend = (word & 0xffffff) << 2
                if addend & 0x02000000: addend -= 0x04000000
                delta = value + addend - place
                if delta & 3 or not -(1 << 25) <= delta < (1 << 25): raise ValueError('ARM call out of range')
                word = (word & 0xff000000) | ((delta >> 2) & 0xffffff)
            elif kind in (43, 44):  # R_ARM_MOVW_ABS_NC / R_ARM_MOVT_ABS
                expected = 0x03000000 if kind == 43 else 0x03400000
                if word & 0x0ff00000 != expected or ((word >> 4) & 0xf000) | (word & 0xfff):
                    raise ValueError('unsupported MOV relocation instruction/addend')
                immediate = value & 65535 if kind == 43 else value >> 16
                word = (word & ~0x000f0fff) | ((immediate & 0xf000) << 4) | (immediate & 0xfff)
            else: raise ValueError('unsupported ARM relocation: ' + str(kind))
            struct.pack_into('<I', image, out_at, word)
    required = {
        'm10v_halation': {'m10v_halation'},
        'm10v_library_': {'m10v_library_init', 'm10v_library_valid', 'm10v_library_name',
            'm10v_library_select', 'm10v_library_texture', 'm10v_library_halation', 'm10v_library_detail', 'm10v_library_tables', 'm10v_library_stamp', 'm10v_library_render'},
        'm10v_camera_library_': {'m10v_camera_library_load', 'm10v_camera_library_select',
            'm10v_camera_library_texture', 'm10v_camera_library_halation', 'm10v_camera_library_stamp', 'm10v_camera_library_detail'},
        'm10v_menu_': {'m10v_menu_count', 'm10v_menu_max_count', 'm10v_menu_index', 'm10v_menu_name',
            'm10v_menu_value_name', 'm10v_menu_icon', 'm10v_menu_value_icon', 'm10v_menu_focus',
            'm10v_menu_confirm', 'm10v_menu_key', 'm10v_menu_enter'},
        'm10v_capture_': {'m10v_capture_library'},
        'm10v_resource_': {'m10v_resource_primary', 'm10v_resource_secondary'},
        'm10v_chain_': {'m10v_chain_capture'},
        'm10v_icon_': {'m10v_icon_pixels'},
        'm10v_sd_': {'m10v_sd_u32','m10v_sd_crc','m10v_sd_header','m10v_sd_record'},
        'm10v_sd_camera_': {'m10v_sd_camera_item','m10v_sd_camera_install'},
        'm10v_debug_': {'m10v_debug_log'},
        'm10v_detail_': {'m10v_detail_table','m10v_detail_control'},
    }[prefix]
    if set(symbols) != required or not image_sections: raise ValueError('runtime API incomplete')
    return bytes(image), symbols


def build(out_dir, base=0x540b6000, initial_state_hex=None, debug_mode=False, debug_build_id=0, sd_library=False):
    if type(debug_mode) is not bool or not isinstance(debug_build_id,int) or not 0<=debug_build_id<=0xffffffff:
        raise ValueError('invalid debug build options')
    if initial_state_hex is None:
        initial = bytearray(64)
        struct.pack_into('<IHHI', initial, 0, 0x5630314d, 2, 64, 0)
        for i in range(5): struct.pack_into('<H6B', initial, 12+i*8, 33 if i == 4 else i+34, 0, 0, 3,3,5,2)
        struct.pack_into('<I', initial, 60, zlib.crc32(initial[:60]))
    else:
        initial = bytes.fromhex(initial_state_hex)
        if len(initial) != 64 or struct.unpack_from('<IHHI',initial) != (0x5630314d,2,64,0):
            raise ValueError('invalid initial state header')
        for i in range(5):
            film, grain, soft, gain, spread, threshold, profile = struct.unpack_from('<H6B', initial, 12+i*8)
            if not 1 <= film <= 65 or grain > 3 or soft > 3 or gain>8 or spread>8 or threshold>8 or profile>3: raise ValueError('invalid initial slot')
        if initial[52] > 2 or any(v > 3 for v in initial[53:56]) or any(initial[56:60]) or struct.unpack_from('<I',initial,60)[0] != zlib.crc32(initial[:60]):
            raise ValueError('invalid initial settings/checksum')
    initial = bytes(initial)
    if base & 4095: raise ValueError('runtime base must be page aligned')
    configured = os.environ.get('M10V_LLVM_CLANG')
    candidates = [configured] if configured else [
        '/opt/homebrew/opt/llvm/bin/clang', '/usr/local/opt/llvm/bin/clang', shutil.which('clang')]
    compiler = next((p for p in candidates if p and Path(p).is_file()), None)
    if not compiler: raise RuntimeError('LLVM clang unavailable')
    from scripts.generate_m10v_catalog import generate
    if (ROOT/'native/gr3/m10v_legacy_data.h').read_text()!=generate(): raise ValueError('legacy tables header does not match exact source')
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='m10v-native-library-') as folder:
        folder = Path(folder); obj = folder / 'library.o'
        subprocess.run([compiler, *FLAGS, '-DM10V_INITIAL_STATE_BYTES=' + ','.join(str(v) for v in initial), '-c', str(ROOT / 'native/gr3/m10v_library.c'), '-o', str(obj)],
                       check=True, capture_output=True)
        halo_obj = folder / 'halo.o'
        subprocess.run([compiler, *FLAGS, '-c', str(ROOT / 'native/gr3/halation_core.c'), '-o', str(halo_obj)], check=True, capture_output=True)
        halo, halo_symbols = link_object(halo_obj.read_bytes(), base + 0x100, prefix='m10v_halation')
        core_base = (base + 0x100 + len(halo) + 15) & ~15
        core, symbols = link_object(obj.read_bytes(), core_base, halo_symbols)
        symbols.update(halo_symbols)
        image = bytearray(0x100) + halo + bytes(core_base-base-0x100-len(halo)) + core
        # Single-instruction entry trampolines, before the new C module. Each
        # reproduces the displaced official instruction then returns to +4.
        original = {
            0x00: (0x532c26c0, 0xe1a0c00d), 0x10: (0x532922b4, 0xe351000a),
            0x20: (0x532a985c, 0xe1a0c00d), 0x30: (0x532935dc, 0xe351000a),
            0x40: (0x532a9988, 0xe1a0c00d), 0x50: (0x531ac270, 0xe1a0c00d),
            0x60: (0x531ac24c, 0xe1a0c00d), 0x80: (0x532c2a9c, 0xe1a0c00d),
            0x90: (0x532c2c80, 0xe1a0c00d), 0xa0: (0x531ab914, 0xe1a0c00d),
            0xb0: (0x531ac140, 0xe1a0c00d),
        }
        for offset, (address, word) in original.items():
            delta = address + 4 - (base + offset + 4) - 8
            if delta & 3 or not -(1 << 25) <= delta < 1 << 25: raise ValueError('trampoline branch out of range')
            struct.pack_into('<II', image, offset, word, 0xea000000 | ((delta >> 2) & 0xffffff))
        (out / 'm10v-library-arm.o').write_bytes(obj.read_bytes())
        camera_obj = folder / 'camera.o'
        subprocess.run([compiler, *FLAGS, '-c', str(ROOT / 'native/gr3/m10v_library_camera.c'), '-o', str(camera_obj)],
                       check=True, capture_output=True)
        camera_base = (base + len(image) + 15) & ~15
        camera, camera_symbols = link_object(camera_obj.read_bytes(), camera_base, symbols, 'm10v_camera_library_')
        image += bytes(camera_base - base - len(image)) + camera
        symbols.update(camera_symbols)
        (out / 'm10v-library-camera-arm.o').write_bytes(camera_obj.read_bytes())
        if sd_library:
            subprocess.run(['node','scripts/generate_gr3_sd_contract.mjs','--check'],cwd=ROOT,check=True,capture_output=True)
            for sd_source,sd_prefix in [('m10v_sd_library.c','m10v_sd_'),('m10v_sd_camera.c','m10v_sd_camera_')]:
                sd_obj=folder/(sd_source+'.o')
                subprocess.run([compiler,*FLAGS,'-c',str(ROOT/'native/gr3'/sd_source),'-o',str(sd_obj)],check=True,capture_output=True)
                sd_base=(base+len(image)+15)&~15
                sd_code,sd_symbols=link_object(sd_obj.read_bytes(),sd_base,symbols,sd_prefix)
                image+=bytes(sd_base-base-len(image))+sd_code;symbols.update(sd_symbols)
        debug_flags = [f'-DM10V_DEBUG_MODE={int(debug_mode)}',f'-DM10V_DEBUG_BUILD_ID={debug_build_id}u',f'-DM10V_SD_LIBRARY={int(sd_library)}']
        if debug_mode:
            debug_obj = folder / 'debug.o'
            subprocess.run([compiler,*FLAGS,*debug_flags,'-c',str(ROOT/'native/gr3/m10v_debug.c'),'-o',str(debug_obj)],check=True,capture_output=True)
            debug_base=(base+len(image)+15)&~15
            debug,debug_symbols=link_object(debug_obj.read_bytes(),debug_base,prefix='m10v_debug_')
            image+=bytes(debug_base-base-len(image))+debug;symbols.update(debug_symbols)
        # Link dedicated stock-detail backend against the same camera journal.
        from scripts.build_gr3_native_detail import build_detail, STOCK_TABLE
        detail_obj=folder/'detail.o'
        subprocess.run([compiler,*FLAGS,*debug_flags,'-c',str(ROOT/'native/gr3/m10v_detail.c'),'-o',str(detail_obj)],check=True,capture_output=True)
        detail_base=(base+len(image)+15)&~15
        provisional,detail_symbols=link_object(detail_obj.read_bytes(),detail_base,{**symbols,'m10v_detail_tables':detail_base},'m10v_detail_')
        shims_base=(detail_base+len(provisional)+15)&~15
        shims,detail_report=build_detail(shims_base,{**symbols,**detail_symbols})
        detail,detail_symbols=link_object(detail_obj.read_bytes(),detail_base,{**symbols,'m10v_detail_tables':detail_report['tables']},'m10v_detail_')
        image+=bytes(detail_base-base-len(image))+detail
        image+=bytes(shims_base-base-len(image))+shims
        symbols.update(detail_symbols)
        menu_obj = folder / 'menu.o'
        subprocess.run([compiler, *FLAGS, *debug_flags, f'-DM10V_NATIVE_BASE={base}u', '-c',
                        str(ROOT / 'native/gr3/m10v_library_menu.c'), '-o', str(menu_obj)], check=True, capture_output=True)
        menu_base = (base + len(image) + 15) & ~15
        menu, menu_symbols = link_object(menu_obj.read_bytes(), menu_base, symbols, 'm10v_menu_')
        image += bytes(menu_base - base - len(image)) + menu
        symbols.update(menu_symbols)
        (out / 'm10v-library-menu-arm.o').write_bytes(menu_obj.read_bytes())
        capture_obj = folder / 'capture.o'
        subprocess.run([compiler, *FLAGS, *debug_flags, '-c', str(ROOT / 'native/gr3/m10v_library_capture.c'),
                        '-o', str(capture_obj)], check=True, capture_output=True)
        capture_base = (base + len(image) + 15) & ~15
        capture, capture_symbols = link_object(capture_obj.read_bytes(), capture_base, symbols, 'm10v_capture_')
        image += bytes(capture_base - base - len(image)) + capture
        symbols.update(capture_symbols)
        (out / 'm10v-library-capture-arm.o').write_bytes(capture_obj.read_bytes())
        names = re.findall(r'\{"([^"\n]+)",[-0-9]', (ROOT / 'native/gr3/m10v_library.c').read_text())
        if len(names) != 33 or len(set(names)) != 33: raise ValueError('original catalog names incomplete')
        texts = names[:32] + [f'M10V Slot {i}' for i in range(1, 6)] + [
            'M10V Film Library', 'Save failed. Try again.', 'M10V Library',
            'Choose Film', '颗粒', '柔光', 'Timestamp', 'Choose Slot',
            'Grain Off', 'Grain Weak', 'Grain Medium', 'Grain Strong',
            'Diffusion Off', 'Diffusion Weak', 'Diffusion Medium', 'Diffusion Strong',
            'Timestamp Off', 'Date Only', 'Date and Time', 'Date Format', 'Stamp Corner', 'Stamp Color', 'Back',
            'YYYY.MM.DD', 'DD.MM.YYYY', 'YYYY-MM-DD', 'YY.MM.DD',
            'Top Left', 'Top Right', 'Bottom Left', 'Bottom Right',
            'White', 'Orange', 'Red', 'Yellow', 'Back', 'Done', names[32],
            '800T Halation','光晕强度','扩散范围','高光阈值','Halation Profile',
            *[str(i) for i in range(9)],'Off','Weak','Natural','Strong',
            *[f['name'] for f in json.loads((ROOT/'web/gr3/film-catalog.json').read_text())['looks']]]
        if len(texts) != 125: raise ValueError('private resource inventory differs')
        if sd_library:
            translations={'M10V Film Library':'胶卷库','Save failed. Try again.':'读取或保存失败，请检查存储卡','M10V Library':'胶卷设置',
                'Choose Film':'内置胶卷','Timestamp':'时间戳','Choose Slot':'设置槽位',
                'Grain Off':'颗粒关闭','Grain Weak':'颗粒弱','Grain Medium':'颗粒中','Grain Strong':'颗粒强',
                'Diffusion Off':'柔光关闭','Diffusion Weak':'柔光弱','Diffusion Medium':'柔光中','Diffusion Strong':'柔光强',
                'Timestamp Off':'时间戳关闭','Date Only':'仅日期','Date and Time':'日期和时间','Date Format':'日期格式',
                'Stamp Corner':'显示位置','Stamp Color':'文字颜色','Back':'返回','Done':'完成','Top Left':'左上','Top Right':'右上',
                'Bottom Left':'左下','Bottom Right':'右下','White':'白色','Orange':'橙色','Red':'红色','Yellow':'黄色',
                '800T Halation':'800T 光晕','Halation Profile':'光晕模式','Off':'关闭','Weak':'弱','Natural':'自然','Strong':'强'}
            texts=[translations.get(t,t) for t in texts]+['空','上一页','下一页','胶卷库']
        last_resource=786+len(texts)-1
        resource_base = (base + len(image) + 3) & ~3
        resources = bytearray(4 * len(texts)); descriptors = []
        for index, text in enumerate(texts):
            encoded = (text + '\0').encode('utf-16le')
            record = resource_base + len(resources); descriptors.append(record)
            resources += struct.pack('<BBHI', len(encoded) // 2, 1, 0, record + 8) + encoded
            resources += bytes(-len(resources) & 3)
            struct.pack_into('<I', resources, index * 4, record)
        image += bytes(resource_base - base - len(image)) + resources
        resource_asm = folder / 'resources.S'; resource_obj = folder / 'resources.o'
        resource_asm.write_text('''
            .syntax unified
            .arm
            .text
            .global m10v_resource_primary
            .type m10v_resource_primary,%function
        m10v_resource_primary:
            sub r8,fp,#0xb0
            mov r0,r8
            movw r3,#786
            cmp r7,r3
            blo 1f
            movw r3,#910
            cmp r7,r3
            bhi 1f
            movw r3,#786
            sub r7,r7,r3
            movw r3,:lower16:m10v_string_descriptors
            movt r3,:upper16:m10v_string_descriptors
            ldr r7,[r3,r7,lsl #2]
            ldr pc,=0x53396700
        1:  movw r3,#0x2bac
            movt r3,#0x5500
            ldr r3,[r3,r9,lsl #2]
            ldr r7,[r3,r7,lsl #2]
            ldr pc,=0x53396700
            .global m10v_resource_secondary
            .type m10v_resource_secondary,%function
        m10v_resource_secondary:
            movw r3,#786
            cmp r7,r3
            blo 2f
            movw r3,#910
            cmp r7,r3
            bhi 2f
            movw r3,#786
            sub r12,r7,r3
            movw r3,:lower16:m10v_string_descriptors
            movt r3,:upper16:m10v_string_descriptors
            ldr r3,[r3,r12,lsl #2]
            ldr pc,=0x5339710c
        2:  movw r3,#0x2bac
            movt r3,#0x5500
            ldr r3,[r3,r0,lsl #2]
            ldr r3,[r3,r7,lsl #2]
            ldr pc,=0x5339710c
            .ltorg
        '''.replace('#910',f'#{last_resource}'))
        subprocess.run([compiler, *FLAGS, '-c', str(resource_asm), '-o', str(resource_obj)], check=True, capture_output=True)
        resource_code_base = (base + len(image) + 15) & ~15
        resource_code, resource_symbols = link_object(resource_obj.read_bytes(), resource_code_base,
            {'m10v_string_descriptors': resource_base}, 'm10v_resource_')
        image += bytes(resource_code_base - base - len(image)) + resource_code; symbols.update(resource_symbols)
        chain_asm = folder / 'chain.S'; chain_obj = folder / 'chain.o'
        chain_asm.write_text('''
            .syntax unified
            .arm
            .text
            .global m10v_chain_capture
            .type m10v_chain_capture,%function
        m10v_chain_capture:
            push {r0-r12,lr}
            mrs r0,cpsr
            mov r1,sp
            bic sp,sp,#7
            sub sp,sp,#8
            stm sp,{r0,r1}
            mov r0,r4
            bl m10v_capture_library
            ldm sp,{r0,r1}
            mov sp,r1
            msr cpsr_fs,r0
            pop {r0-r12,lr}
            ldr pc,=0x536abd28
            .ltorg
        ''')
        subprocess.run([compiler, *FLAGS, '-c', str(chain_asm), '-o', str(chain_obj)], check=True, capture_output=True)
        chain_base = (base + len(image) + 15) & ~15
        chain, chain_symbols = link_object(chain_obj.read_bytes(), chain_base, symbols, 'm10v_chain_')
        image += bytes(chain_base - base - len(image)) + chain; symbols.update(chain_symbols)
        # All artwork stays inside the appended RTOS ROM, leaving ICONBIN and
        # its fixed flash partition unchanged. Stock directory entries remain exact.
        icon_table = base + len(image)
        stock_directory = (ROOT/'native/gr3/m10v_stock_icon_directory.bin').read_bytes()
        icon_pixels = (ROOT/'native/gr3/m10v_icons.rgba').read_bytes()
        if len(stock_directory)!=671*4 or len(icon_pixels)!=65*6400: raise ValueError('icon inventory differs')
        icon_descriptors = icon_table + 736*4
        icon_data = icon_descriptors + 65*8
        image += stock_directory + b''.join(struct.pack('<I',icon_descriptors+i*8) for i in range(65))
        image += b''.join(struct.pack('<HHI',40,40,(icon_data+i*6400)//4) for i in range(65))
        image += icon_pixels
        icon_asm=folder/'icons.S';icon_obj=folder/'icons.o'
        icon_asm.write_text("""
            .syntax unified
            .arm
            .text
            .global m10v_icon_pixels
            .type m10v_icon_pixels,%function
        m10v_icon_pixels:
            push {r0,r1}
            mrs r0,cpsr
            ldrh r1,[r5,#0x24]
            movw ip,#671
            cmp r1,ip
            blo 1f
            movw ip,#735
            cmp r1,ip
            bhi 1f
            lsl ip,r6,#2
            b 2f
        1:  add ip,lr,r6,lsl #2
        2:  msr cpsr_fs,r0
            pop {r0,r1}
            ldr pc,=0x5320a838
            .ltorg
        """)
        subprocess.run([compiler,*FLAGS,'-c',str(icon_asm),'-o',str(icon_obj)],check=True,capture_output=True)
        icon_base=(base+len(image)+15)&~15
        icon_code,icon_symbols=link_object(icon_obj.read_bytes(),icon_base,prefix='m10v_icon_')
        image += bytes(icon_base-base-len(image))+icon_code; symbols.update(icon_symbols)
        if len(image)>524288: raise ValueError('M10V code and artwork exceed 512 KiB mapping budget')
    sha = lambda data: hashlib.sha256(data).hexdigest()
    manifest = {'schema': 'm10v-gr3-native-film-runtime/v2', 'base': base, 'symbols': symbols,
                'code_bytes': len(image), 'code_sha256': sha(image), 'film_count': 65, 'slots': 5,
                'sources': {p: sha((ROOT / p).read_bytes()) for p in
                            ('native/gr3/m10v_library.c', 'native/gr3/m10v_library.h',
                             'native/gr3/halation_core.c', 'native/gr3/halation_core.h', 'native/gr3/halation_energy.h',
                             'native/gr3/m10v_detail.c','scripts/build_gr3_native_detail.py','scripts/build_gr3_menu_patches.py',
                             'native/gr3/m10v_legacy_data.h','web/gr3/film-catalog.json','scripts/generate_m10v_catalog.py',
                             'native/gr3/m10v_library_camera.c', 'native/gr3/m10v_library_menu.c',
                             'native/gr3/m10v_library_capture.c',
                             'native/gr3/m10v_debug.c','native/gr3/m10v_debug.h',
                             'scripts/build_gr3_m10v_library.py','scripts/generate_m10v_icons.py',
                             'native/gr3/m10v_icons.rgba','native/gr3/m10v_stock_icon_directory.bin')},
                'compiler': subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                'flags': FLAGS, 'debug_compile_flags': debug_flags, 'firmware_artifact': False, 'camera_tested': False,
                'abi': 'M10V state64 + explicit semiplanar CbCr422 image + date6',
                'dependencies': [], 'scratch_max_bytes': 589824}
    manifest['sd_library']=sd_library
    if sd_library:
        manifest['sources'].update({p:sha((ROOT/p).read_bytes()) for p in ['native/gr3/m10v_sd_library.h','native/gr3/m10v_sd_library.c','native/gr3/m10v_sd_camera.c','native/gr3/m10v_sd_contract.h','node/gr3-sd-film-pack.mjs','scripts/generate_gr3_sd_contract.mjs']})
    manifest['detail']=detail_report
    manifest['debug_mode']=debug_mode
    manifest['debug_log']={'schema':'m10v-gr3-sd-debug/v1','build_id':f'{debug_build_id:08x}',
        'files':['M10VMN0.BIN','M10VMN1.BIN','M10VCP0.BIN','M10VCP1.BIN'],
        'page_bytes':4096,'records_per_channel':63,'guard_address':0x5506821f} if debug_mode else None
    initial_offset = bytes(image).find(initial)
    if initial_offset < 0 or bytes(image).find(initial, initial_offset+1) >= 0: raise ValueError('initial state not uniquely embedded')
    manifest['initial_state_hex'] = initial.hex()
    manifest['initial_state_offset'] = initial_offset
    manifest['resources'] = {'first_id': 786, 'last_id': last_resource, 'table': resource_base,
                              'descriptors': descriptors, 'texts': texts}
    manifest['icons']={'first_id':671,'last_id':735,'width':40,'height':40,'table':icon_table,'descriptors':icon_descriptors,'pixels':icon_data,'sha256':sha(icon_pixels)}
    (out / 'm10v-library-arm.bin').write_bytes(image)
    (out / 'm10v-library-arm.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'builds/gr3-m10v-library')
    parser.add_argument('--base',type=lambda v:int(v,0),default=0x540b6000)
    parser.add_argument('--initial-state-hex')
    parser.add_argument('--sd-library',action='store_true')
    parser.add_argument('--debug',action='store_true')
    parser.add_argument('--debug-build-id',type=lambda v:int(v,0),default=0)
    args = parser.parse_args(); print(json.dumps(build(args.out, base=args.base, initial_state_hex=args.initial_state_hex,debug_mode=args.debug,debug_build_id=args.debug_build_id,sd_library=args.sd_library), indent=2))

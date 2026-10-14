"""Local complete-Look renderer; no network, firmware, or Lightroom operations."""
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/gr4'))
import numpy as np
from gr4_editor.offline_look import inspect_support, render_pixels
from gr4_editor.numeric.xmp import ALPHABET, CRS

def convert(data):
    if not data or len(data)>8*1024*1024 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('XMP 不允许 DOCTYPE/ENTITY，文件必须非空且不超过 8 MiB')
    text=data.decode('utf-16') if data.startswith((b'\xff\xfe',b'\xfe\xff')) else data.decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('XMP 不允许 DOCTYPE/ENTITY')
    tree=ET.fromstring(text)
    # Bound decompression before the upstream renderer decodes any color table.
    for node in tree.iter():
        for key,text in node.attrib.items():
            if not key.startswith(CRS+'Table_'): continue
            if len(text)%5==1:raise ValueError('XMP 颜色表 base85 长度无效')
            binary=bytearray()
            for at in range(0,len(text),5):
                group=text[at:at+5]
                value=sum(ALPHABET.index(c)*85**power for power,c in enumerate(group))
                binary+=struct.pack('<I',value)[:4 if len(group)==5 else len(group)-1]
            if len(binary)<4 or int.from_bytes(binary[:4],'little')>32*1024*1024:
                raise ValueError('XMP 颜色表展开尺寸超限')
            decoder=zlib.decompressobj();raw=decoder.decompress(binary[4:],32*1024*1024+1)
            if len(raw)>32*1024*1024 or not decoder.eof or decoder.unconsumed_tail:
                raise ValueError('XMP 颜色表压缩内容超限或不完整')
    inventory=inspect_support(data)
    if not inventory['supported']:raise ValueError('XMP: '+inventory['reason'])
    size=33
    rgb=np.array([(r,g,b) for b in range(size) for g in range(size) for r in range(size)],dtype=np.float64)/(size-1)
    linear=np.where(rgb<=0.04045,rgb/12.92,((rgb+0.055)/1.055)**2.4)
    rendered=render_pixels(data,linear)
    lines=['TITLE "Local complete XMP Look; approximate sRGB target"',f'LUT_3D_SIZE {size}']
    lines.extend(' '.join(f'{v:.8f}' for v in row) for row in rendered)
    return {'cube':'\n'.join(lines)+'\n','inventory':inventory,'targetModel':'GR III',
            'approximate':True,'baseProfileReconstructed':False,'gridSize':size}

if __name__=='__main__':
    try:print(json.dumps(convert(Path(sys.argv[1]).read_bytes()),ensure_ascii=False))
    except Exception as error:raise SystemExit(str(error))

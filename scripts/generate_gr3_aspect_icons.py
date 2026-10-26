"""Rebuild 60x40 aspect tiles from official GR III icon pixels, no host fonts."""
from pathlib import Path
import hashlib, json, struct, subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def generate():
    from scripts.build_gr3_m10v_library import capture_stock_rtos
    r=capture_stock_rtos();d=(ROOT/'native/gr3/m10v_stock_icon_directory.bin').read_bytes()
    script="import{readFileSync}from'node:fs';import{officialResources}from'./node/gr3-stock-presets.mjs';const{decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));process.stdout.write(d.subarray(s.ICONBIN.offset,s.ICONBIN.offset+s.ICONBIN.size));"
    b=subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT)
    def sprite(id):
        a=struct.unpack_from('<I',d,id*4)[0]-0x53000000;w,h,o=struct.unpack_from('<HHI',r,a)
        return Image.frombytes('RGBA',(w,h),b[o*4:o*4+w*h*4])
    bg=(53,53,54,255)
    def glyph(id,box,size=None):
        src=sprite(id).crop(box)
        # Numbered-key and X glyphs use black instead of tile gray backgrounds.
        if id in (258,609,610):
            src=Image.frombytes('RGBA',src.size,bytes(v for p in [src.getpixel((x,y)) for y in range(src.height) for x in range(src.width)] for v in tuple(c+((255-c)*p[0]+127)//255 for c in bg[:3])+(255,)))
        return src.resize(size,Image.Resampling.LANCZOS) if size else src
    X=glyph(258,(27,14,39,26),(8,16));P=glyph(299,(18,12,29,28),(8,16))
    a=glyph(33,(43,17,51,28),(7,11));n=glyph(33,(31,17,38,28))
    six=glyph(609,(9,5,21,26),(10,16));seven=glyph(610,(9,4,21,25),(10,16));x=glyph(258,(27,14,39,26),(8,9))
    def tile(parts):
        im=sprite(339).copy()
        # Preserve every pixel outside the stock ratio label's content area.
        for yy in range(7,33):
            for xx in range(12,48):im.putpixel((xx,yy),bg)
        width=sum(p.width for p in parts)+len(parts)-1;xx=(60-width)//2
        for p in parts:im.paste(p,(xx,28-p.height));xx+=p.width+1
        return im
    tiles=[tile([X,P,a,n]),tile([six,x,seven])]
    payload=b''.join(im.tobytes() for im in tiles)
    return tiles,payload,{'schema':'m10v-aspect-icons/v1','labels':['XPan','6x7'],'width':60,'height':40,'stock_frame_icon':339,'stock_glyph_icons':[33,258,299,609,610],'rtos_sha256':hashlib.sha256(r).hexdigest(),'iconbin_sha256':hashlib.sha256(b).hexdigest(),'sha256':hashlib.sha256(payload).hexdigest()}
if __name__=='__main__':
    tiles,payload,report=generate()
    (ROOT/'native/gr3/m10v_aspect_icons.rgba').write_bytes(payload)
    (ROOT/'native/gr3/aspect-icons.json').write_text(json.dumps(report,indent=2)+'\n')

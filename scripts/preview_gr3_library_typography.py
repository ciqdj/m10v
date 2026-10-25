"""Layout preview: real ARM card geometry/pixels, approximate host header text.

Caption strips and enabled triangles are the exact pixels used by the camera.
This is an offline preview, not a physical-camera framebuffer capture.
"""
import argparse,json,os,struct,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('M10V_GR3_ORIGINAL_RTOS',str(ROOT/'data/research/gr3/RTOS.bin'))
from tests import test_gr3_settings_view as fixture

def preview(out,font_path):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 fixture.SettingsViewTests.setUpClass();f=fixture.SettingsViewTests()
 films=[33,66,67,68,69,70,71,72,73,74]
 u=f.machine(catalog_ids=dict(enumerate(films)));f.call(u,'create',0x10001000)
 state=bytearray(212)
 for i,film in enumerate(films):struct.pack_into('<H',state,12+8*i,film)
 struct.pack_into('<7I',state,184,2,0,0,4,0,0,0)
 u.mem_write(0x10002000,bytes(state));u.mem_write(0x10000800,b'Portra 160\0')
 u.mem_write(0x10003000,struct.pack('<7I',0,0,0x540b0010,0,0,0,0))
 f.call(u,'draw',0x10001000,0x10002000,0x10003000)
 words=struct.unpack('<56I',u.mem_read(0x10001000,224));heap=words[55]
 image=Image.new('RGBA',(720,480),'#161a18');d=ImageDraw.Draw(image);geometry=[]
 rect=lambda i:struct.unpack('<4I',u.mem_read(words[i]+0x20,16))
 for i,film in enumerate(films):
  x,y,w,h=rect(6+i);selected=u.mem_read(words[6+i]+0xea,1)[0]==6
  d.rectangle((x,y,x+w-1,y+h-1),fill='#ffe100' if selected else '#161a18')
  x,y,w,h=rect(16+i);d.rectangle((x,y,x+w-1,y+h-1),fill='#161a18')
  x,y,w,h=rect(26+i)
  cw,ch,p=struct.unpack('<HHI',u.mem_read(heap+710400+i*8,8))
  image.alpha_composite(Image.frombytes('RGBA',(cw,ch),bytes(u.mem_read(p*4,cw*ch*4))),(x,y))
  geometry.append(dict(film=film,rect=[x,y,w,h],bitmap=[cw,ch],focused=selected))
 for index,text,size in [(2,'胶卷库  已启用 10/10',32),(3,'5  Portra 160',30),(4,'方向键选择  OK启用/停用  MENU返回',28),(52,'1',30)]:
  x,y,w,h=rect(index);d.text((x,y),text,font=ImageFont.truetype(str(font_path),size),fill='#eff7f5')
 image.convert('RGB').save(out/'gr3-library-text.png')
 (out/'geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
 f.call(u,'destroy',0x10001000)
 if f.live:raise RuntimeError('preview leaked native allocations')
 print(out/'gr3-library-text.png')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--font',type=Path,required=True);a=p.parse_args();preview(a.out,a.font)

"""Offline preview from real ARM view geometry and rendered RGBA card buffers.

Runs the existing official-firmware emulator fixture. Text uses a host font;
this is a layout/resource preview, not a camera framebuffer capture.
"""
import argparse,json,struct,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.test_gr3_settings_view import SettingsViewTests
from scripts.m10v_catalog_resources import catalog_texts

def preview(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 SettingsViewTests.setUpClass();fixture=SettingsViewTests()
 u=fixture.machine();fixture.call(u,'create',0x10001000);fixture.state(u)
 films=[34,35,66,33,37]
 for i,film in enumerate(films):u.mem_write(0x10002000+12+i*8,struct.pack('<H',film))
 u.mem_write(0x10000800,b'5207\0')
 fixture.call(u,'draw',0x10001000,0x10002000,0)
 widgets=fixture.widgets(u)
 fonts=['/System/Library/Fonts/Supplemental/Arial Unicode.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
 font=next(p for p in fonts if Path(p).exists())
 image=Image.new('RGBA',(720,480),'black');d=ImageDraw.Draw(image)
 geometry=[]
 for i in range(5):
  x,y,w,h=struct.unpack('<4I',u.mem_read(widgets[6+i]+0x20,16))
  selected=u.mem_read(widgets[6+i]+0xea,1)[0]==6
  d.rectangle((x,y,x+w-1,y+h-1),fill='#ffe100' if selected else '#000000')
  x,y,w,h=struct.unpack('<4I',u.mem_read(widgets[11+i]+0x20,16))
  d.rectangle((x,y,x+w-1,y+h-1),fill='#000000')
  x,y,w,h=struct.unpack('<4I',u.mem_read(widgets[16+i]+0x20,16))
  cw,ch,p=struct.unpack('<HHI',u.mem_read(0x10004000+i*8,8))
  card=Image.frombytes('RGBA',(cw,ch),bytes(u.mem_read(p*4,cw*ch*4)))
  image.alpha_composite(card,(x,y))
  geometry.append({'film':films[i],'rect':[x,y,w,h],'bitmap':[cw,ch],'selected':selected})
 resources=catalog_texts()
 for index,size in [(2,27),(3,28),(4,21)]:
  x,y,w,h=struct.unpack('<4I',u.mem_read(widgets[index]+0x20,16))
  if index==3:
   p=struct.unpack('<I',u.mem_read(widgets[index]+0xf0,4))[0]
   data=bytes(u.mem_read(p,192));end=next(i for i in range(0,len(data),2) if data[i:i+2]==b'\0\0')
   text=data[:end].decode('utf-16le')
  else:
   resource=struct.unpack('<H',u.mem_read(widgets[index]+0xea,2))[0]
   text=resources[resource-786]
  d.text((x,y+4),text,font=ImageFont.truetype(font,size),fill='#eff7f5')
 image.convert('RGB').save(out/'gr3-film-ui-720.png')
 image.resize((1440,960),Image.Resampling.NEAREST).convert('RGB').save(out/'gr3-film-ui.png')
 (out/'geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
 fixture.call(u,'destroy',0x10001000)
 if fixture.live:raise RuntimeError('preview leaked native allocations')
 print(out/'gr3-film-ui.png')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'docs/previews/film-ui')
 preview(parser.parse_args().out)

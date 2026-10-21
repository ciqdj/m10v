"""Deterministic native enum artwork; no system fonts or external art."""
from pathlib import Path
from PIL import Image,ImageDraw
from scripts.generate_m10v_icons import text
ROOT=Path(__file__).resolve().parents[1]
NAMES=('RED','YELLOW','BLUE','GRAY')
COLORS=('#fd0100','#f9d34e','#0100f9','#e0e0e0')

def artwork():
 rows=[]
 for name,color in zip(NAMES,COLORS):
  im=Image.new('RGBA',(64,16));d=ImageDraw.Draw(im)
  d.rectangle((0,0,63,15),fill=color,outline='#ffffff')
  label=Image.new('RGBA',(len(name)*4-1,5));text(ImageDraw.Draw(label),0,0,name,'#ffffff' if name in ('RED','BLUE') else '#000000')
  label=label.resize((label.width*2,10),Image.Resampling.NEAREST)
  im.alpha_composite(label,((64-label.width)//2,3));rows.append(im)
 scale=Image.new('RGBA',(400,12));d=ImageDraw.Draw(scale)
 for i,(name,color) in enumerate(zip(NAMES,COLORS)):
  x=20+120*i;w=len(name)*4-1
  d.rectangle((x-12,0,x+12,3),fill=color,outline='#ffffff')
  text(d,x-w//2,7,name,'#ffffff')
 return rows+[scale]

if __name__=='__main__':
 (ROOT/'native/gr3/m10v_charmera_ui.rgba').write_bytes(b''.join(im.tobytes() for im in artwork()))

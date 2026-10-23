"""Offline LUT comparison from the repository's existing reference photograph."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_gr3_harman_reference import sample_tetrahedral

def generate():
 source=Image.open(ROOT/'web/gr3/film-street-source.png').convert('RGB');source.thumbnail((520,330))
 web=json.loads((ROOT/'web/gr3/style-filters-luts.json').read_text());w,h=source.size
 canvas=Image.new('RGB',(4*(w+24)+24,2*(h+65)+100),'#111817');d=ImageDraw.Draw(canvas)
 font=ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc',18);small=ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc',14)
 d.text((24,14),'M10V · 7 new curated filters',font=font,fill='#edf1ea')
 d.text((24,42),'Offline display-sRGB LUT comparison · not camera-calibrated · live preview may differ',font=small,fill='#a9b6ae')
 rgb=np.asarray(source)/255
 for i,stock in enumerate([None]+web['stocks']):
  x=24+(i%4)*(w+24);y=86+(i//4)*(h+65)
  im=source if stock is None else Image.fromarray(np.rint(sample_tetrahedral(np.array(stock['values']).reshape(15,15,15,3)/255,rgb.reshape(-1,3)).reshape(h,w,3)*255).astype('uint8'))
  canvas.paste(im,(x,y));d.text((x,y+h+9),'Original' if stock is None else str(stock['id'])+' · '+stock['name'],font=font,fill='#edf1ea')
 target=ROOT/'docs/previews/style-filters-20261023.png';target.parent.mkdir(exist_ok=True);canvas.save(target);print(target)
if __name__=='__main__':generate()

"""Original M10V cartridge art. One RGBA source for web and camera, no borrowed assets."""
from pathlib import Path
import re,json,hashlib
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
GLYPHS={'0':['111','101','101','101','111'],'1':['010','110','010','010','111'],'2':['111','001','111','100','111'],'3':['111','001','111','001','111'],'4':['101','101','111','001','001'],'5':['111','100','111','001','111'],'6':['111','100','111','101','111'],'7':['111','001','010','010','010'],'8':['111','101','111','101','111'],'9':['111','101','111','001','111'],'M':['10001','11011','10101','10001','10001'],'V':['101','101','101','101','010'],'T':['111','010','010','010','010'],'E':['111','100','110','100','111'],'G':['111','100','101','101','111'],'P':['110','101','110','100','100'],'H':['101','101','111','101','101'],'D':['110','101','101','101','110'],'C':['111','100','100','100','111'],'F':['111','100','110','100','100'],'L':['100','100','100','100','111']}
# Compact original 3×5 capitals, sized for the camera's 40px sprites.
GLYPHS.update({
 'A':['010','101','111','101','101'],'B':['110','101','110','101','110'],
 'I':['111','010','010','010','111'],'J':['001','001','001','101','010'],
 'K':['101','101','110','101','101'],'N':['101','111','111','111','101'],
 'O':['010','101','101','101','010'],'Q':['010','101','101','111','011'],
 'R':['110','101','110','101','101'],'S':['111','100','111','001','111'],
 'U':['101','101','101','101','111'],'W':['101','101','111','111','101'],
 'X':['101','101','010','101','101'],'Y':['101','101','010','010','010'],
 'Z':['111','001','010','100','111'],'M':['101','111','111','101','101']})
PALETTE=['#728d88','#c78d48','#6a87a6','#b48373','#626977','#b29597','#508b9d','#ba794f','#858761','#aebcb1','#498c92','#b47787','#b2aa90','#9caec1','#9c7a53','#917b61','#899090','#b3b4a9','#66696a','#a99988','#839ba5','#6c967c','#a08baa','#c1a275','#748895','#8eab6a','#bb6655','#c9c6b5','#667fa7','#bca26c','#687469','#bab7a4','#c83737']
def label(name,i):
 # Labels describe existing presets; this does not add or rename any recipe.
 if name=='800T':return 'CINE','800T','#c83737'
 if name=='Gold 200':return 'KODA','200','#d5a844'
 if name.startswith('Ektar '):return 'EKTAR',name.split()[-1],'#c94c47'
 if name=='Pro 400H':return 'FUJI','400H','#669c7a'
 if name.startswith('Portra '):return 'PORTR',name.split()[-1],'#a484ad'
 if name.startswith('V3 500T'):
  # KODAK VISION3 500T stock number, verified against Kodak's product page.
  return '5219','500TN' if name.endswith(' N') else '500T',PALETTE[(i-1)%32]
 if name=='V3 5207':return 'V3','5207',PALETTE[(i-1)%32]
 if name.startswith('Vision3 ') or name.startswith('V3 250D'):
  return 'V3','250DF' if name.endswith(' Flat') else '250D','#c6a450'
 aliases={'Neutral':'NEUTR','Morning':'MORN','Portrait':'PORTR','Autumn':'AUTMN',
          'Bleached':'BLEAC','Silver':'SILVR','Golden':'GOLDN','Superia':'SUPRA',
          'Reversal':'REVRS','Harubeni':'HARUB','Radiant':'RADNT','Kyushu':'KYUSH',
          'Miyabi':'MYABI'}
 words=name.removeprefix('M10V ').split()
 def short(w):return aliases.get(w,re.sub('[^A-Z0-9]','',w.upper())[:5])
 return short(words[0]),short(words[1]) if len(words)>1 else '',PALETTE[(i-1)%32]

def text(d,x,y,s,c):
 for ch in s:
  rows=GLYPHS[ch]
  for yy,row in enumerate(rows):
   for xx,v in enumerate(row):
    if v=='1':d.point((x+xx,y+yy),fill=c)
  x+=len(rows[0])+1

def generate():
 names=re.findall(r'\{"([^"\n]+)",[-0-9]',(ROOT/'native/gr3/m10v_library.c').read_text())
 names += [v['name'] for v in json.loads((ROOT/'web/gr3/film-catalog.json').read_text())['looks']]
 if len(names)!=65:raise ValueError('catalog must contain 65 films')
 # Preserve exact official directory pointers; original descriptors stay in RAM.
 import subprocess,struct
 js="import {readFileSync} from 'node:fs';import {officialResources} from './node/gr3-stock-presets.mjs';const {decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));process.stdout.write(d.subarray(s.RTOS.offset+0x107b540+0x20fc,s.RTOS.offset+0x107b540+0x20fc+671*4));"
 directory=subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT)
 if len(directory)!=2684:raise ValueError('official icon directory invalid')
 (ROOT/'native/gr3/m10v_stock_icon_directory.bin').write_bytes(directory)
 pixels=bytearray();meta=[];sheet=Image.new('RGBA',(10*120,7*130),'#171a18')
 out=ROOT/'web/gr3/film-icons';out.mkdir(exist_ok=True)
 for i,name in enumerate(names,1):
  title,code,color=label(name,i);im=Image.new('RGBA',(40,40));d=ImageDraw.Draw(im)
  d.rounded_rectangle((8,3,31,36),radius=4,fill='#121c20')
  d.rectangle((16,0,22,3),fill='#a6afb0');d.rectangle((17,0,21,1),fill='#e7e8dc')
  d.rounded_rectangle((10,7,31,32),radius=2,fill=color)
  d.rectangle((8,6,10,32),fill='#475253');d.line((9,10,9,29),fill='#697775')
  d.polygon([(11,12),(31,8),(31,18),(11,22)],fill='#f1e9d0')
  title_width=sum(len(GLYPHS[c][0])+1 for c in title)-1
  if title_width>19:raise ValueError('icon title too wide: '+name)
  text(d,21-title_width//2,13,title,'#243133')
  w=sum(len(GLYPHS[c][0])+1 for c in code)-1
  if w>19:raise ValueError('icon code too wide: '+name)
  text(d,21-w//2,25,code,'#fff4dc')
  d.rectangle((11,33,30,35),fill='#2b383b');d.line((12,34,29,34),fill='#88908b')
  d.polygon([(31,14),(35,15),(35,30),(32,32),(32,17)],fill='#303d3b');d.line((34,17,34,27),fill=color)
  rgba=im.tobytes();pixels+=rgba;im.save(out/f'{i:02d}.png',optimize=True)
  meta.append({'id':i,'name':name,'title':title,'code':code,'color':color,'icon_url':f'/gr3/film-icons/{i:02d}.png','sha256':hashlib.sha256(rgba).hexdigest()})
  big=im.resize((120,120),Image.Resampling.NEAREST);sheet.alpha_composite(big,((i-1)%10*120,(i-1)//10*130))
 (ROOT/'native/gr3/m10v_icons.rgba').write_bytes(pixels)
 (out/'catalog.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 sheet.save(ROOT/'docs/previews/m10v-film-icons.png')
 return meta
if __name__=='__main__':generate()

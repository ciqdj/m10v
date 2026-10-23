"""Antialiased square film boxes, using the bundled OFL Noto Sans Bold font."""
import json,re,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.generate_m10v_icons import box_style,box_icon,FONT

def generate():
 names=re.findall(r'\{"([^"\n]+)",[-0-9]',(ROOT/'native/gr3/m10v_library.c').read_text())
 names += [v['name'] for v in json.loads((ROOT/'web/gr3/film-catalog.json').read_text())['looks']]
 names += ['5207','蓝凤凰','哈曼 RED','Portra 160','富士业务用 100','乐凯 C200','CCD Classic','富士 C200','ProImage 100','T-Max 100','Aerochrome','2460','5203']
 if len(names)!=78:raise ValueError('film catalog differs')
 styles=json.loads((ROOT/'web/gr3/style-filters-luts.json').read_text())['stocks']
 specs=[(i,name,None) for i,name in enumerate(names,1)]+[(289,'Kodak Charmera',None),(290,'方块世界',None)]+[(v['id'],v['name'],v) for v in styles]
 rows=['/* Generated square artwork and antialiased Noto Sans glyph coverage. */','static const struct { char brand[12], main[16], sub[16]; uint32_t header,color,ink,accent; } box_cards[]={']
 for i,name,spec in specs:
  brand,title,code,header,paper,ink,accent=box_style(name,i)
  if spec:title,code,paper,ink=spec['title'],spec['code'],spec['color'],'#ffffff'
  colors=','.join('0xff'+c[1:]+'u' for c in (header,paper,ink,accent))
  rows.append(' {"%s","%s","%s",%s},'%(brand,title,code,colors))
 rows+=['};','static const uint8_t smooth_width[95]={']
 font=ImageFont.truetype(str(FONT),14)
 rows.append(','.join(str(round(font.getlength(chr(c)))) for c in range(32,127))+'};')
 rows.append('static const uint8_t smooth_glyph[95][320]={')
 for c in range(32,127):
  im=Image.new('L',(16,20));ImageDraw.Draw(im).text((0,0),chr(c),font=font,fill=255,anchor='lt')
  rows.append('{'+','.join(str(v) for v in im.tobytes())+'},')
 rows+=['};','']
 return '\n'.join(rows)

def custom_icon():return box_icon('Custom LUT',0).tobytes()
if __name__=='__main__':
 (ROOT/'native/gr3/m10v_film_card_data.h').write_text(generate())
 (ROOT/'native/gr3/m10v_custom_icon.rgba').write_bytes(custom_icon())

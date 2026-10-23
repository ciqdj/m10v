"""Antialiased square film boxes, using the bundled OFL Noto Sans Bold font."""
import json,re,sys,base64,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.generate_m10v_icons import box_style,FONT

def canonical_raster():
 """Pinned coverage avoids FreeType/RAQM differences across build hosts."""
 data=json.loads((ROOT/'native/gr3/m10v_film_font_raster.json').read_text())
 if data['schema']!='m10v-film-font-raster/v1' or hashlib.sha256(FONT.read_bytes()).hexdigest()!=data['font_sha256']:raise ValueError('font raster provenance differs')
 glyphs=base64.b64decode(data['glyphs_base64'],validate=True)
 custom=base64.b64decode(data['custom_icon_base64'],validate=True)
 if len(data['widths'])!=95 or any(type(v)is not int or not 0<=v<=16 for v in data['widths']) or len(glyphs)!=95*320 or len(custom)!=6400:raise ValueError('font raster extent differs')
 if hashlib.sha256(glyphs).hexdigest()!=data['glyphs_sha256'] or hashlib.sha256(custom).hexdigest()!=data['custom_icon_sha256']:raise ValueError('font raster digest differs')
 return data['widths'],glyphs,custom

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
 widths,glyphs,_=canonical_raster()
 rows.append(','.join(str(v) for v in widths)+'};')
 rows.append('static const uint8_t smooth_glyph[95][320]={')
 for i in range(95):rows.append('{'+','.join(str(v) for v in glyphs[i*320:(i+1)*320])+'},')
 rows+=['};','']
 return '\n'.join(rows)

def custom_icon():return canonical_raster()[2]
if __name__=='__main__':
 (ROOT/'native/gr3/m10v_film_card_data.h').write_text(generate())
 (ROOT/'native/gr3/m10v_custom_icon.rgba').write_bytes(custom_icon())

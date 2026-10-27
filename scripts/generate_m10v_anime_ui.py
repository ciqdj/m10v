"""Pinned short Chinese FN enum artwork; font is only needed for --bake-font."""
import base64,hashlib,json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
RASTER=ROOT/'native/gr3/anime-ui-raster.json'
NAMES=['关闭','线稿','色块','手绘']
def bake(font_path):
 font_path=Path(font_path);rows=[]
 for label in NAMES:
  im=Image.new('L',(40,16));d=ImageDraw.Draw(im);font=ImageFont.truetype(str(font_path),14)
  box=d.textbbox((0,0),label,font=font)
  d.text(((40-d.textlength(label,font=font))/2,(16-box[3]+box[1])//2-box[1]),label,font=font,fill=255);rows.append(im)
 im=Image.new('L',(400,10));d=ImageDraw.Draw(im);font=ImageFont.truetype(str(font_path),10)
 for i,label in enumerate(NAMES):d.text((20+120*i-d.textlength(label,font=font)/2,-3),label,font=font,fill=255)
 rows.append(im)
 data={'schema':'m10v-anime-ui-raster/v1','caption':'漫画进阶','names':NAMES,'font_sha256':hashlib.sha256(font_path.read_bytes()).hexdigest(),'font_source':'https://github.com/notofonts/noto-cjk/blob/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf','license':'SIL Open Font License 1.1','rows':[{'size':list(im.size),'alpha':base64.b64encode(im.tobytes()).decode(),'sha256':hashlib.sha256(im.tobytes()).hexdigest()} for im in rows]}
 RASTER.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def verify():
 data=json.loads(RASTER.read_text())
 if data['schema']!='m10v-anime-ui-raster/v1' or data['names']!=NAMES or data['caption']!='漫画进阶':raise ValueError('anime FN labels differ')
 for row,size in zip(data['rows'],[(40,16)]*4+[(400,10)]):
  raw=base64.b64decode(row['alpha'],validate=True)
  if row['size']!=list(size) or len(raw)!=size[0]*size[1] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('anime enum raster differs')
 if len(data['rows'])!=5:raise ValueError('anime enum inventory')
 return data
def artwork():
 data=verify();images=[]
 for row in data['rows']:
  im=Image.new('RGBA',tuple(row['size']),(255,255,255,0));im.putalpha(Image.frombytes('L',tuple(row['size']),base64.b64decode(row['alpha'])));images.append(im)
 return images
def generate():
 data=verify();images=artwork();raw=b''.join(im.tobytes() for im in images)
 (ROOT/'native/gr3/m10v_anime_ui.rgba').write_bytes(raw)
 metadata={k:data[k] for k in ['schema','caption','names','font_sha256','font_source','license']}
 metadata.update(value_rect=[50,10,40,40],value_size=[40,16],scale_size=[400,10],value_first=864,scale_icon=868,pixels_sha256=hashlib.sha256(raw).hexdigest(),raster_sha256=hashlib.sha256(RASTER.read_bytes()).hexdigest())
 (ROOT/'native/gr3/anime-ui.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
 return images
if __name__=='__main__':
 if len(sys.argv)==3 and sys.argv[1]=='--bake-font':bake(sys.argv[2])
 generate()

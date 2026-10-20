#!/usr/bin/env python3
"""Render the production C stamp (not a font approximation) into a QA sheet."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_gr3_m10v_library import NativeFilmLibraryTests
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def main():
    NativeFilmLibraryTests.setUpClass()
    case=NativeFilmLibraryTests()
    sheet=Image.new('RGB',(2000,1000),'#252321');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22)
    draw.text((30,20),'PRODUCTION C RENDER  /  6000 x 4000  /  native-size crops',font=font,fill='white')
    for i,name in enumerate([b'Kodak 5207',b'Harman Phoenix',b'CUSTOM ABCDEFGHIJKLMNOP']):
        y,uv=case.stamp_pixels(name=name,planes=True)
        rows,cols=np.where(y!=73)
        left=max(0,int(cols.min())-15)&~1;right=min(y.shape[1],int(cols.max())+16)&~1
        top=max(0,int(rows.min())-15);bottom=int(rows.max())+16
        crop=y[top:bottom,left:right].astype(float)-16
        chroma=uv[top:bottom,left:right].astype(float)
        u=np.repeat(chroma[:,0::2]-128,2,axis=1);v=np.repeat(chroma[:,1::2]-128,2,axis=1)
        rgb=np.stack((1.164*crop+1.596*v,1.164*crop-.392*u-.813*v,1.164*crop+2.017*u),axis=2)
        rgb=np.clip(rgb,0,255).astype(np.uint8)
        panel=Image.fromarray(rgb)
        sheet.paste(panel,(30,90+i*290))
        draw.text((30,65+i*290),name.decode(),font=font,fill='#ccc7c1')
    dest=Path(sys.argv[1]) if len(sys.argv)>1 else Path('builds/gr3-stamp-design/stamp-actual-c.png')
    dest.parent.mkdir(parents=True,exist_ok=True);sheet.save(dest)
    NativeFilmLibraryTests.doClassCleanups()
    print(dest.resolve())
if __name__=='__main__':main()

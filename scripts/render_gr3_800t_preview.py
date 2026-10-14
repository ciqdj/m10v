"""Render the actual native kernel under a declared software YCbCr422 ABI.

JPEG/PNG input only; does not modify EXIF, RAW or firmware. Color rendering is
an approximation of the experimental tables, not the camera's ISP.
"""
import argparse,ctypes as C,io,json,shutil,subprocess,tempfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
class HaloImage(C.Structure):
    _fields_=[('y',C.POINTER(C.c_uint8)),('chroma',C.POINTER(C.c_uint8))]+[(n,C.c_uint32) for n in ('y_bytes','chroma_bytes','width','height','y_stride','chroma_stride','format')]
def render(source,out):
    if source.suffix.lower() not in ('.jpg','.jpeg','.png'):raise ValueError('native reference renderer accepts JPEG/PNG, not DNG thumbnails')
    original=Image.open(source).convert('RGB');original.thumbnail((1500,1500))
    if original.width%2:original=original.crop((0,0,original.width-1,original.height))
    w,h=original.size
    look=json.loads(subprocess.check_output(['node','--input-type=module','-e',f"import {{create800TFilm}} from '{(ROOT/'node/gr3-800t-plan.mjs').as_uri()}'; console.log(JSON.stringify(create800TFilm()));"],text=True))
    rgb=np.asarray(original,dtype=np.float64)
    values=rgb@ (np.asarray(look['matrixQ13']).reshape(3,3)/8192).T
    for k in range(3):values[:,:,k]=np.interp(np.clip(values[:,:,k],0,255),np.arange(256),np.asarray(look['curves'][k])*255/16383)
    rgb=np.uint8(np.clip(np.rint(values@(np.asarray(look['postQ512']).reshape(3,3)/512).T),0,255))
    ycc=np.asarray(Image.fromarray(rgb).convert('YCbCr'))
    y=ycc[:,:,0].copy();chroma=np.empty((h,w),dtype=np.uint8)
    chroma[:,0::2]=((ycc[:,0::2,1].astype(np.uint16)+ycc[:,1::2,1]+1)>>1).astype(np.uint8)
    chroma[:,1::2]=((ycc[:,0::2,2].astype(np.uint16)+ycc[:,1::2,2]+1)>>1).astype(np.uint8)
    step=1
    while (w+step-1)//step>384 or (h+step-1)//step>256:step*=2
    n=(6*((w+step-1)//step)*((h+step-1)//step)+3)&~3
    outputs=[]
    with tempfile.TemporaryDirectory() as t:
        lib=Path(t)/'core.dylib'
        subprocess.run([shutil.which('clang') or 'clang','-O2','-dynamiclib',str(ROOT/'native/gr3/halation_core.c'),'-o',str(lib)],check=True,capture_output=True)
        fn=C.CDLL(str(lib)).m10v_halation;fn.argtypes=[C.POINTER(HaloImage),C.c_uint32,C.POINTER(C.c_uint8),C.c_uint32];fn.restype=C.c_int
        for strength in (1,2):
            yy=y.copy();cc=chroma.copy();scratch=np.empty(n,dtype=np.uint8)
            ptr=lambda a:a.ctypes.data_as(C.POINTER(C.c_uint8))
            image=HaloImage(ptr(yy),ptr(cc),yy.size,cc.size,w,h,w,w,1)
            if fn(C.byref(image),strength,ptr(scratch),n)!=0:raise RuntimeError('native kernel rejected preview')
            result=np.empty((h,w,3),dtype=np.uint8);result[:,:,0]=yy
            result[:,:,1]=np.repeat(cc[:,0::2],2,axis=1);result[:,:,2]=np.repeat(cc[:,1::2],2,axis=1)
            outputs.append(Image.fromarray(result,'YCbCr').convert('RGB'))
    out.mkdir(parents=True,exist_ok=True)
    for name,img in zip(('weak','strong'),outputs):img.save(out/f'800t-native-{name}.png')
    sheet=Image.new('RGB',(3*w,h+36),(16,16,16));draw=ImageDraw.Draw(sheet)
    for i,(label,img) in enumerate(zip(('ORIGINAL','800T WEAK / SOFTWARE REFERENCE','800T STRONG / SOFTWARE REFERENCE'),[original,*outputs])):
        sheet.paste(img,(i*w,36));draw.text((i*w+8,10),label,fill='white')
    sheet.save(out/'800t-native-comparison.jpg',quality=93)
    return {'source':source.name,'previewSize':[w,h],'gridStep':step,'scratchBytes':n,'layout':'explicit_unsigned_cbcr422_software_conversion','cameraOutput':False,'colorBase':look['provenance']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,default=ROOT/'builds/gr3-800t-kernel/preview');a=p.parse_args();print(json.dumps(render(a.source,a.out),ensure_ascii=False,indent=2))

"""Decode the 256-byte M10V8.BIN written by the hardware-trace candidate."""
import json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_gr3_800t_trace import RETURN_STAGES
b=Path(sys.argv[1]).read_bytes()
if len(b)!=256:raise ValueError('M10V8.BIN must be 256 bytes')
r=struct.unpack('<64I',b)
if r[:2]!=(0x5630314d,0x54303038) or r[2] not in (1,2,3):raise ValueError('Unknown trace identity')
stages={i+1:n for i,n in enumerate(RETURN_STAGES)}|{100:'core_returned_and_freed'}
controls={name:(r[47]>>shift)&15 for name,shift in [('gain',0),('radius',4),('threshold',8),('grain',12),('profile',16)]} if r[2]>=2 and r[47]&0x80000000 else None
print(json.dumps({'formatVersion':r[2],'controls':controls,'privateControls':hex(r[5]) if r[2]>=3 else None,'privateRecord':hex(r[6]) if r[2]>=3 else None,'stage':r[3],'reason':stages.get(r[3],'unknown'),'context':hex(r[4]),
 'contextWords':[hex(n) for n in r[8:32]],'descriptorWords':[hex(n) for n in r[32:40]],
 'recipeMode':r[40],'rawSource':hex(r[41]),'rawDimensionsPointer':hex(r[42]),
 'rawDimensions':[r[43]&65535,r[43]>>16],'tone':r[44],'jpegRequested':r[45]&255,
 'rawRequested':r[45]>>8,'jpegCodingParameter':r[46],'previewWords':[hex(n) for n in r[48:56]],
 'core':{'result':r[56],'sampleMaxY':r[57],'brightSamples':r[58],'sampleCount':r[59],
 'beforeCrSum':r[60],'afterCrSum':r[61],'beforeYSum':r[62],'afterYSum':r[63]}},indent=2))

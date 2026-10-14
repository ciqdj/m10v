// Independent accepted-plan compilation. This uses pinned reference resources
// and locally reviewed ARM code, not the firmware writer's patch manifest.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { decodeFrameMap } from './gr3-frames.mjs';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
function pinned(name,digest) {
  const raw=readFileSync(new URL('../.runtime/grlife/reconstruction/firmware_store/templates/'+name,import.meta.url));
  if(sha(raw)!==digest) throw new Error('800T trusted template identity differs: '+name);
  return JSON.parse(raw);
}
function words(values,signed=false) {
  const out=Buffer.alloc(values.length*2);
  values.forEach((value,index)=>signed?out.writeInt16LE(value,index*2):out.writeUInt16LE(value,index*2));
  return out;
}
export function expected800TBytes(official,prepared) {
  const film=pinned('film-v10.json','b0044fcd69515708326785d525087e33cdfb3d0723681444dce4b7fa28f97bc8');
  const base=pinned('urban160-native.json','63effc91b7daaf98959103f987b3cb954f698f4ed2f1e34343a3a3c5b83c48df');
  const lock=JSON.parse(readFileSync(new URL('../native/gr3/800t-code-lock.json',import.meta.url)));
  if(lock.schema!=='m10v-gr3-800t-code-lock/v1') throw new Error('800T code lock invalid');
  for(const [name,digest] of Object.entries(lock.sources)) {
    if(sha(readFileSync(new URL('../'+name,import.meta.url)))!==digest) throw new Error('800T reviewed code source changed: '+name);
  }
  const decoded=Buffer.from(decodeFrameMap(official).decoded);
  const put=(offset,bytes)=>{
    if(!Number.isSafeInteger(offset)||offset<0||offset+bytes.length>decoded.length-4)throw new Error('800T trusted patch exceeds source');
    bytes.copy(decoded,offset);
  };
  const patch=row=>{
    const before=Buffer.from(row.expected_hex,'hex');
    if(!decoded.subarray(row.offset,row.offset+before.length).equals(before)) throw new Error('800T trusted patch preimage differs');
    put(row.offset,Buffer.from(row.replacement_hex,'hex'));
  };
  for(const row of film.rtos_patches) patch(row);
  for(const row of film.icon_patches) {
    const after=Buffer.from(row.replacement_base64,'base64');
    if(sha(decoded.subarray(row.offset,row.offset+after.length))!==row.expected_sha256)throw new Error('800T trusted icon preimage differs');
    put(row.offset,after);
  }
  for(const look of prepared.color_plan.custom||[]) {
    const slot=film.slots[look.mode];
    put(slot.matrix_offset,words(look.matrixQ13,true));put(slot.post_offset,words(look.postQ512,true));
    if(slot.curve_offsets)slot.curve_offsets.forEach((offset,index)=>put(offset,words(look.curves[index])));
    else put(slot.knots_offset,Buffer.concat(look.knots.map(row=>words(row))));
    put(slot.name_offset,Buffer.from(look.name+'\0'.repeat(slot.name_room-look.name.length+1),'utf16le'));
    for(const offset of slot.name_entry_offsets) put(offset,Buffer.from([look.name.length+1]));
    if(look.iconPixelsBase64)put(slot.icon_offset,Buffer.from(look.iconPixelsBase64,'base64'));
  }
  if(prepared.configuration.slot==='bleach') {
    const controls=JSON.parse(readFileSync(new URL('./gr3-800t-controls.json',import.meta.url)));
    if(controls.schema!=='m10v-gr3-800t-camera-controls/v2')throw new Error('800T camera-control contract differs');
    for(const row of lock.menu.patches)patch({offset:0x10870+row.address-0x53000000,
      expected_hex:row.expected,replacement_hex:row.replacement});
  }
  const hooks=JSON.parse(readFileSync(new URL('./gr3-800t-hooks.json',import.meta.url)));
  if(hooks.schema!=='m10v-gr3-800t-timestamp-hooks/v1')throw new Error('800T trusted hook schema differs');
  const stamp=prepared.configuration.timestamp;
  if(stamp)for(const row of hooks.patches)patch(row);
  else patch({offset:0x10870+0x5048e8,expected_hex:'0e9d06eb',replacement_hex:'9fd22eeb'});
  const tail=Buffer.alloc(49152);Buffer.from(base.program_hex,'hex').copy(tail);
  tail.writeUInt32LE(stamp?1:0,base.common_feature_mask_offset);
  if(stamp) {
    const tune=pinned('urban160-timestamp-tune.json','8bb98748a8952aa4c60d0c37c6424572e043dfe5a76498d02a855b8e5c46e8cb');
    for(const row of tune.program_patches) {
      const before=Buffer.from(row.expected_hex,'hex');
      if(!tail.subarray(row.program_offset,row.program_offset+before.length).equals(before))throw new Error('800T timestamp preimage differs');
      Buffer.from(row.replacement_hex,'hex').copy(tail,row.program_offset);
    }
    Buffer.from(tune.code_hex,'hex').copy(tail,tune.program_offset);
  }
  tail.writeUInt32LE(0xeb00071e,0x3380);
  const chain=[0xe92d4010,0xe1a04000,0xeb000004,0xe1a00004,0xe8bd4010,
    ...(stamp?[0xe51ff004,0x540ba254]:[0xe12fff1e])];
  chain.forEach((word,index)=>tail.writeUInt32LE(word,0x5000+index*4));
  const adapter=lock.adapters[prepared.configuration.slot+'/'+prepared.configuration.strength];
  for(const [entry,offset] of [[adapter,0x5020],[lock.kernel,0x5800]]) {
    const code=Buffer.from(entry.hex,'hex');
    if(code.length!==entry.bytes||sha(code)!==entry.sha256)throw new Error('800T trusted machine code differs');
    code.copy(tail,offset);
  }
  if(prepared.configuration.slot==='bleach') {
    const extension=Buffer.from(lock.menu.hex,'hex');
    if(extension.length!==16384||lock.menu.bytes!==extension.length||sha(extension)!==lock.menu.sha256)throw new Error('800T menu extension code differs');
    extension.copy(tail,0x8000);
  }
  return {decoded,tail,tailOffset:base.tail_offset};
}

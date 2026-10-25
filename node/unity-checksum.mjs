// Independently matched to all four official components and original per-model CPU loops.
export function unityWeightedChecksum(payload,initialPosition=0){
  if(!Buffer.isBuffer(payload))throw Error('checksum payload must be bytes');
  if(!Number.isInteger(initialPosition)||initialPosition<0||initialPosition>0xffffffff)throw Error('checksum initial position must be u32');
  let position=initialPosition,weight=2+position%6,sum=0;
  for(const byte of payload){
    sum+=byte*weight;
    position=(position+1)>>>0;
    weight=position===0?2:weight===7?2:weight+1;
  }
  return sum>>>0;
}
export function verifyUnityComponentChecksum(data){
  if(!Buffer.isBuffer(data)||data.length<512)throw Error('component header length is invalid');
  const payload_bytes=data.readUInt32BE(0x164),file_bytes=data.readUInt32BE(0x168);
  if(file_bytes!==data.length||payload_bytes!==data.length-512)throw Error('component declared length differs');
  const initial_position=data.readUInt32BE(0x20),checksum=data.readUInt32BE(0x16c);
  const computed=unityWeightedChecksum(data.subarray(512),initial_position);
  if(computed!==checksum)throw Error('component weighted checksum differs');
  return {checksum,initial_position,payload_bytes,file_bytes,verify_flags:Array.from({length:4},(_,i)=>data.readUInt32BE(0x170+i*4))};
}

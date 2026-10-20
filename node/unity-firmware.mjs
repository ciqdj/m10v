// Strict UNITY framing and identity-locked GR / GR II inventory. No modified writer.
import {createHash} from 'node:crypto';
import {unityProfiles} from './unity-model-profiles.mjs';
const MAGIC=Buffer.from('UNITY FILE V1.10 / RICOH COMPANY');
const sha=b=>createHash('sha256').update(b).digest('hex');
const need=(value,reason)=>{if(!value)throw Error(reason);};

export function xorUnityPayload(data) {
  need(Buffer.isBuffer(data) && data.length % 4 === 0, 'UNITY payload must be word aligned');
  const output = Buffer.allocUnsafe(data.length);
  let key = 0xf8e69612;
  for (let block = 0; block < data.length; block += 512) {
    for (let at = block; at < Math.min(block + 512, data.length); at += 4)
      output.writeUInt32BE((data.readUInt32BE(at) ^ key) >>> 0, at);
    key = (key + 0xbe39b193) >>> 0;
  }
  return output;
}

export function decodeUnity(data, depth = 0) {
  need(Buffer.isBuffer(data) && data.length >= 2048 && data.length <= 64 * 1024 * 1024,
    'UNITY container size is invalid');
  need(depth <= 2, 'UNITY nesting exceeds limit');
  need(data.subarray(0, MAGIC.length).equals(MAGIC), 'UNITY magic differs');
  need(data.readUInt32BE(32) === data.length, 'UNITY declared size differs');
  const count = data.readUInt32BE(36);
  need(count > 0 && count <= 31, 'UNITY record count is invalid');
  const records = [], names = new Set(), reencoded = Buffer.from(data);
  for (let i = 0; i < count; i++) {
    const at = 64 + i * 64, start = data.readUInt32BE(at) * 512, size = data.readUInt32BE(at + 4);
    const nameBytes = data.subarray(at + 8, at + 20), terminator = nameBytes.indexOf(0);
    need(terminator > 0, 'UNITY component name is not terminated');
    const name = nameBytes.subarray(0, terminator).toString('ascii');
    need(/^[a-zA-Z0-9_-]+$/.test(name) && !names.has(name), 'UNITY component name is invalid or duplicated');
    names.add(name);
    need(size > 0 && size % 4 === 0 && start >= 2048 && start + size <= data.length,
      'UNITY component bounds overlap header or exceed container');
    need(records.every(row => start + size <= row.offset || start >= row.offset + row.size),
      'UNITY component bounds overlap another record');
    const type = data[at + 30], encoding = data[at + 31], payload = data.subarray(start, start + size);
    need(encoding === 1 && (type === 1 || type === 0x80), 'UNITY unsupported record encoding');
    const decoded = type === 1 ? xorUnityPayload(payload) : Buffer.from(payload);
    const nested = type === 0x80 ? decodeUnity(decoded, depth + 1) : null;
    (nested ? nested.reencoded : xorUnityPayload(decoded)).copy(reencoded, start);
    records.push({name, offset: start, size, type, encoding, decoded, nested,
      sha256: sha(decoded), encoded_sha256: sha(payload)});
  }
  need(reencoded.equals(data), 'UNITY byte-exact roundtrip failed');
  return {records, reencoded};
}

function official(data, model) {
  const profile=unityProfiles[model];
  need(profile,'unsupported model');
  need(Buffer.isBuffer(data)&&data.length===profile.size,`${profile.model} official size differs`);
  need(sha(data)===profile.sha256,`${profile.model} official identity differs`);
  const container=decodeUnity(data),rows=[];
  function visit(value,parent=null){for(const row of value.records){rows.push({...row,parent});if(row.nested)visit(row.nested,row.name);}}
  visit(container);
  need(rows.length===3&&rows[0].name==='b01firm6'&&rows[1].name===profile.nested&&rows[2].name==='b01firm8'&&rows[2].parent===profile.nested,
    `${profile.model} known component layout differs`);
  for(const name of ['b01firm6','b01firm8']){
    const row=rows.find(r=>r.name===name);
    need(row.sha256===profile.components[name].sha256&&row.size===profile.components[name].size,`${profile.model} component identity differs`);
    need(row.decoded.readUInt16BE(18)===profile.version,`${profile.model} internal version differs`);
    need(row.decoded.readUInt32BE(0x168)===row.size&&row.decoded.readUInt32BE(0x164)===row.size-512,`${profile.model} component length differs`);
  }
  return {profile,rows};
}
function resourceRows(disk,profile){
  const {table,count}=profile.resources,rows=[],names=new Set();
  need(table+(count+1)*64<=disk.length,'resource directory exceeds component');
  for(let i=0;i<count;i++){
    const at=table+i*64,nameBytes=disk.subarray(at,at+32),end=nameBytes.indexOf(0);
    need(end>0,'resource name is not terminated');
    const name=nameBytes.subarray(0,end).toString('ascii');
    need(/^A:\/[a-zA-Z0-9_./-]+$/.test(name)&&!name.includes('..')&&!names.has(name),'resource name is invalid or duplicated');
    names.add(name);
    const declared_offset=disk.readUInt32BE(at+32),size=disk.readUInt32BE(at+36),payload_offset=512+declared_offset;
    need(declared_offset%512===0&&size>0&&payload_offset+size<=table,'resource bounds exceed volume or overlap directory');
    need(rows.every(r=>payload_offset+size<=r.payload_offset||payload_offset>=r.payload_offset+r.size),'resource bounds overlap');
    rows.push({name,table_offset:at,declared_offset,payload_offset,size,sha256:sha(disk.subarray(payload_offset,payload_offset+size))});
  }
  need(disk.subarray(table+count*64,table+count*64+32).equals(Buffer.alloc(32)),'resource directory terminator differs');
  return rows;
}
export function readUnityModelComponent(data,model,name){
  const row=official(data,model).rows.find(r=>r.name===name);need(row,'unknown component');return Buffer.from(row.decoded);
}
export function inspectUnityModel(data,model){
  const {profile,rows}=official(data,model),disk=rows.find(r=>r.name==='b01firm6');
  return {schema:'m10v-model-firmware-inventory/v1',model:profile.model,public_version:profile.public_version,
    internal_version:profile.public_version,sha256:profile.sha256,size:data.length,filename:profile.filename,
    components:rows.map(({decoded,nested,...row})=>row),resources:resourceRows(disk.decoded,profile),
    proof:{identity:true,strict_record_bounds:true,nested_container:true,resource_bounds:true,byte_exact_roundtrip:true,modified_update_checksum:false},
    capabilities:{inspect:{status:'verified_offline',can_read:true},native_film_library:{status:'researching',can_build:false,
      reason:`${profile.model} native menu, capture ABI and modified update checksum require proof`}},hardware_tested:false};
}

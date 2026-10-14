// Independent readback of the pinned GRLife film-bay code and stock-site hooks.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {inspectOfficial} from './firmware.mjs';
import {decodeFrameMap} from './gr3-frames.mjs';
import {auditGr3Candidate} from './gr3-candidate-audit.mjs';
import {localFilmPublicKey} from './gr3-local-film-pack.mjs';
import {filmBayPublicKeyOffset,grlifeFilmPublicKey} from './gr3-local-film-firmware.mjs';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const pinned={bay:'5897d30d64191a032275eddf0c8b97acb0f059bc08fa319480eacf05d65dd14b',
  level:'19a4e323dbfc261b623f05d129d69006a5b6f05e2405172a849bd96f253d177d'};
function load(name,expected){
 const bytes=readFileSync(new URL(`../.runtime/grlife-current/reconstruction/firmware_store/templates/${name}.json`,import.meta.url));
 if(sha(bytes)!==expected)throw new Error(`胶片库审计源 ${name} 摘要不匹配`);
 return JSON.parse(bytes);
}
const need=(ok,message)=>{if(!ok)throw new Error(message);};
function rtosOffset(decoded,sections){
 let at=0;
 for(const row of sections){if(row.name==='RTOS')return at+16;at+=row.size;}
 throw new Error('RTOS section missing');
}
export function auditFilmBay(source,candidate,{level=false,localKey=true}={}){
 const official=inspectOfficial(source),container=auditGr3Candidate(source,candidate);
 need(container.changedSections.length===2&&container.changedSections.includes('RTOS')&&
   container.changedSections.includes('ICONBIN'),'胶片库候选修改了预期之外的分区');
 const original=decodeFrameMap(source,source.readUInt32LE(source.length-8)).decoded;
 const decoded=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8)).decoded;
 const sourceAt=rtosOffset(original,official.sections),candidateAt=rtosOffset(decoded,container.sections);
 const bay=load('urban160-film-bay',pinned.bay);
 need(bay.schema==='grlife-urban160-film-bay/v1'&&bay.verified_offline===true&&bay.test_keys===false&&
   bay.card_path==='GRLIFE/FILMS.GRF'&&bay.pack_format===2,'胶片库发布契约不匹配');
 let code=Buffer.from(bay.code_hex,'hex');
 need(sha(code)===bay.code_sha256,'胶片库代码摘要不匹配');
 if(level){
  const slider=load('urban160-level-slider',pinned.level);
  const call=bay.level_chain,offset=call.code_offset;
  need(code.subarray(offset,offset+4).toString('hex')===call.expected_hex,'水平仪链接前像不匹配');
  const target=Buffer.from(slider.hook_patch.replacement_hex,'hex').readUInt32LE(0);
  const distance=target-(bay.base_va+bay.program_offset+offset+8);
  need(distance%4===0&&distance>=-(1<<25)&&distance<(1<<25),'水平仪链接超出范围');
  code=Buffer.from(code);code.writeUInt32LE((0xeb000000|((distance>>2)&0xffffff))>>>0,offset);
 }
 need(code.subarray(filmBayPublicKeyOffset,filmBayPublicKeyOffset+32).equals(grlifeFilmPublicKey),
   '胶片库上游公钥前像不匹配');
 if(localKey){code=Buffer.from(code);localFilmPublicKey.copy(code,filmBayPublicKeyOffset);}
 const codeOffset=candidateAt+bay.base_va+bay.program_offset-0x53000000;
 need(codeOffset>=candidateAt&&codeOffset+code.length<=candidateAt+container.sections.find(row=>row.name==='RTOS').size-16,
   '胶片库代码超出 RTOS');
 need(decoded.subarray(codeOffset,codeOffset+code.length).equals(code),'胶片库代码回读不一致');
 for(const site of bay.rtos_patches){
  const at=site.va-0x53000000;
  need(original.subarray(sourceAt+at,sourceAt+at+4).toString('hex')===site.stock_hex,
    `胶片库官方前像不匹配：${site.name}`);
  need(decoded.subarray(candidateAt+at,candidateAt+at+4).toString('hex')===site.replacement_hex,
    `胶片库站点回读不匹配：${site.name}`);
 }
 for(const [begin,end] of [[0x620000,0x640000],[0x820000,0x840000],[0x2038,0x203c]])
  need(decoded.subarray(candidateAt+begin,candidateAt+end).equals(original.subarray(sourceAt+begin,sourceAt+end)),
    '胶片库修改了更新器或版本保护区');
 return {source_sha256:official.sha256,candidate_sha256:container.candidateSha256,
  changed_sections:container.changedSections,rtos_growth:container.rtosGrowth,
  bay_code_sha256:sha(code),public_key_sha256:sha(localKey?localFilmPublicKey:grlifeFilmPublicKey),
  verified_stock_sites:bay.rtos_patches.length,
  level_slider_chained:level,pack_format:2,card_path:bay.card_path,
  camera_tested:false,external_pack_issuer_required:!localKey};
}

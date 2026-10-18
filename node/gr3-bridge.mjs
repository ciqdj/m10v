// GR III bridge with photo-evidenced version coverage; hardware verification pending.
import {createHash} from 'node:crypto';
import {inspectOfficial,SHA256} from './firmware.mjs';
import {decodeFrameMap,sum32} from './gr3-frames.mjs';
import {encodeZip} from './gr3-sd-film-export.mjs';
const hash=b=>createHash('sha256').update(b).digest('hex');
const need=(ok,msg)=>{if(!ok)throw Error('GR III bridge: '+msg);};
const VERSION=0x020a211b;
const CANDIDATE_SHA256='f58ae0ec9453024c607391fb42dcd168394adfdea97fdf166d7060b7115c5baf';
const hardwareVerification=()=>({status:'pending',source:'photo_metadata_and_offline_tests',reported_at:'2026-10-18',candidate_sha256:CANDIDATE_SHA256,observed_dsp_version:'2.10.32.27',observed_cpu_version:null,scope:'用户 JPG 与 DNG 的 MakerNote 均记录 DSP 2.10.32.27，高于旧桥接 2.10.22.27。新版修正版本准入范围；CPU 版本未知，完整刷写和恢复仍待实机验证。'});

const sizes=[72,556,516,44640,21816,17520064,3062784,13899776,49152,131072,37440,18354964,36,6595272];
const start=n=>sizes.slice(0,n).reduce((a,s)=>a+s+16,0)+16;
const RTOS=start(5),CPU=start(9),GATE=RTOS+0x6285dc;
function source(b){need(Buffer.isBuffer(b)&&hash(b)===SHA256,'requires exact official GR III 2.10; GR IIIx is not supported');inspectOfficial(b);}
function repair(b){b.writeUInt32LE(0,b.length-4);b.writeUInt32LE(-sum32(b)>>>0,b.length-4);}
function cpuSum(d){let sum=0;for(let p=CPU;p<CPU+131072;p+=4)sum=(sum+d.readUInt32BE(p))>>>0;return sum;}
function outside(a,b,ranges){need(a.length===b.length,'length changed');let p=0;for(const [s,n] of ranges.toSorted((a,b)=>a[0]-b[0])){need(a.subarray(p,s).equals(b.subarray(p,s)),'non-target bytes changed');p=s+n;}need(a.subarray(p).equals(b.subarray(p)),'non-target bytes changed');}
export function prepareGr3Bridge(official){source(official);return {schema:'m10v-gr3-bridge-plan/v1',model:'GR III',package_version:'2.10.33.27',acceptance_limit:'Current DSP and CPU must each be <= 2.10.33.27 under the public updater rules; anniversary versions are unknown.',source_sha256:SHA256,plan_id:hash('m10v-gr3-bridge-v3:'+SHA256+':020a211b:536285dc:e6ffffea'),camera_verified:false,download_available:true,hardware_verification:hardwareVerification(),stage_two:'Install the included official 2.10 package after bridge update completes; then build normal M10V firmware with version adaptation disabled.'};}
export function verifyGr3Bridge(official,candidate){
 source(official);need(Buffer.isBuffer(candidate)&&candidate.length>=152&&candidate.length<=70*1024*1024&&!(candidate.length&3),'invalid candidate size');
 const tail=candidate.length-24,enc=candidate.readUInt32LE(tail+12);
 need(((128+enc+3)&~3)===tail&&candidate.subarray(128+enc,tail).every(x=>x===0),'invalid padding/layout');
 need(sum32(candidate)===0,'outer checksum failed');
 outside(official.subarray(0,128),candidate.subarray(0,128),[[0x38,4],[0x50,4]]);
 outside(official.subarray(-24),candidate.subarray(-24),[[12,4],[20,4]]);
 const a=decodeFrameMap(official).decoded,b=decodeFrameMap(candidate).decoded;
 need(sum32(b)===0&&cpuSum(b)===0,'decoded or CPU checksum failed');
 outside(a,b,[[RTOS+0x2038,4],[GATE,4],[CPU+0x7c,4],[CPU+0x90,4],[b.length-4,4]]);
 need(candidate.readUInt32BE(0x38)===0x020a211b&&candidate.readUInt32BE(0x50)===0x020a211b&&b.readUInt32BE(RTOS+0x2038)===0x020a211b&&b.readUInt32BE(CPU+0x90)===0x020a211b,'version copies differ');
 need(a.subarray(GATE,GATE+4).equals(Buffer.from('042803e3','hex'))&&b.subarray(GATE,GATE+4).equals(Buffer.from('e6ffffea','hex')),'updater branch differs');
 const diffs=[];for(let p=0;p<b.length;p++)if(a[p]!==b[p]){const last=diffs.at(-1);if(last&&last.offset+last.length===p)last.length++;else diffs.push({offset:p,length:1});}
 return {schema:'m10v-gr3-bridge-receipt/v1',model:'GR III',status:'offline_verified',package_version:'2.10.33.27',acceptance_limit:'Current DSP and CPU must each be <= 2.10.33.27 under the public updater rules; anniversary versions are unknown.',source_sha256:SHA256,candidate_sha256:hash(candidate),candidate_bytes:candidate.length,filename:'fwdc239b.bin',camera_verified:false,hardware_verification:hardwareVerification(),
  runtime_versions:{dsp:'2.10.21.27',cpu:'2.10.21.27',scope:'public code sources; not measured on a camera'},
  updater_patch:{address:'0x536285dc',before:'042803e3',after:'e6ffffea',destination:'0x5362857c'},decoded_changes:diffs,
  checks:{outer_sum32:0,decoded_sum32:0,cpu_sum32_be:0,fresh_decode:true,non_target_unchanged:true,section_layout_unchanged:true},
  limitations:['versions_above_2.10.33.27_not_supported','other_service_firmware_variants_not_verified','hardware_recovery_not_proven']};
}
export function buildGr3Bridge(official){
 source(official);const {decoded,frames}=decodeFrameMap(official),target=Buffer.from(decoded);
 need(target.subarray(GATE,GATE+4).equals(Buffer.from('042803e3','hex')),'unexpected gate preimage');
 target.writeUInt32BE(VERSION,RTOS+0x2038);target.writeUInt32BE(VERSION,CPU+0x90);Buffer.from('e6ffffea','hex').copy(target,GATE);
 target.writeUInt32BE(0,CPU+0x7c);target.writeUInt32BE(-cpuSum(target)>>>0,CPU+0x7c);repair(target);
 const chunks=[];for(const f of frames){
  // Backreferences can reach across frames. Changed history invalidates reuse.
  const history=Math.max(0,f.decoded_start-8191);
  if(target.subarray(history,f.decoded_end).equals(decoded.subarray(history,f.decoded_end)))chunks.push(official.subarray(128+f.encoded_start,128+f.encoded_end));
  else for(let p=f.decoded_start;p<f.decoded_end;p+=0x6000){const part=target.subarray(p,Math.min(p+0x6000,f.decoded_end)),h=Buffer.alloc(2);h.writeUInt16BE(0x8000|part.length);chunks.push(h,part);}
 }
 chunks.push(Buffer.alloc(2));const payload=Buffer.concat(chunks),footer=Buffer.from(official.subarray(-24));footer.writeUInt32LE(payload.length,12);
 const candidate=Buffer.concat([official.subarray(0,128),payload,Buffer.alloc(-(128+payload.length)&3),footer]);
 candidate.writeUInt32BE(VERSION,0x38);candidate.writeUInt32BE(VERSION,0x50);repair(candidate);
 const receipt=verifyGr3Bridge(official,candidate);
 need(receipt.candidate_sha256===CANDIDATE_SHA256,'生成结果与新版候选摘要不一致');

 return {candidate,receipt};
}
export const BRIDGE_INSTRUCTIONS=`M10V GR III 固件桥接套件 / 待实机验证
仅适用 GR III（包括同型号 HDF），不适用 GR IIIx、GR IV。基于官方 2.10。
用途：机内 2.10 服务子版本高于公开版本，导致官方/修改固件更新失败。
本包只从 2.10.21.27 增至 2.10.33.27；机内任一组件高于 2.10.33.27 时仍可能拒绝，不能通用解锁未知周年版本。
2026-10-18 用户原图记录 DSP 2.10.32.27，旧版 2.10.22.27 低于此值；新版提升为 2.10.33.27。CPU 版本未知，第一阶段及回刷仍待实机验证，离线通过不代表刷写成功。请准备充足电量，更新中不要断电或操作相机。

1. 先备份照片、设置和官方文件。核对 receipt.json 及 SHA256SUMS。
2. 只将 stage-1-bridge/fwdc239b.bin 复制到 SD 根目录；不要把两个阶段文件同时放入卡根目录。按 GR III 官方固件更新流程进入更新并确认，等待明确的更新完成提示。
3. 第一阶段失败、卡住或异常时停止，不继续第二阶段；记录屏幕原文、阶段和进度。
4. 第一阶段成功并正常重启后，移除卡上的桥接文件，替换为 stage-2-official/fwdc239b.bin。再次按官方流程更新，确认完成并重启。
5. 第二阶段成功后，可使用平台普通功能包；GR III 的旧单包版本适配入口已收起，按普通流程生成即可。第三次更新由已恢复的官方更新器处理。

桥接包安装版本为 2.10.33.27；未改 DSP 运行常量，菜单仍显示 2.10 不代表失败，不要仅根据菜单版本重复刷桥接包。CPU 运行版本预计仍为 2.10.21.27（第三段来自代码常量），尚待实测。
桥接更新器只跳过低版本拒绝；第二阶段官方包会覆盖该补丁。包不包含胶片改动，不应长期停留在桥接阶段。
官方第二阶段包不是 Flash/NAND 备份，无法保证救砖。记录每阶段屏幕提示、能否开机拍摄及新拍原始 JPEG/DNG，反馈时附 receipt.json。
`;
export function exportGr3Bridge(official,input){
 const plan=prepareGr3Bridge(official);
 need(input&&input.accepted_plan_id===plan.plan_id&&input.acknowledge_instructions===true&&Object.keys(input).every(k=>['accepted_plan_id','acknowledge_instructions'].includes(k)),'先预检并确认两阶段桥接使用说明');
 const {candidate,receipt}=buildGr3Bridge(official);
 const files={'stage-1-bridge/fwdc239b.bin':candidate,'stage-2-official/fwdc239b.bin':official,'receipt.json':Buffer.from(JSON.stringify(receipt,null,2)+'\n'),'README.txt':Buffer.from(BRIDGE_INSTRUCTIONS),'hardware-verification.json':Buffer.from(JSON.stringify(hardwareVerification(),null,2)+'\n')};
 files['SHA256SUMS']=Buffer.from(Object.entries(files).map(([n,b])=>`${hash(b)}  ${n}`).join('\n')+'\n');
 return {candidate,receipt,files,zip:encodeZip(files)};
}

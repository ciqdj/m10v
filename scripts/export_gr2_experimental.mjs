#!/usr/bin/env node
// Uses the same source/config binding and generator as the GR II web workbench.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {prepareGr2Native,generateGr2Native} from '../node/gr2-native-library.mjs';
import {readModelOfficial} from '../node/model-firmware.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import {nativeCatalog} from '../node/gr3-native-library.mjs';
import {buildSdFilmPack} from '../node/gr3-sd-film-pack.mjs';
const args=process.argv.slice(2),out=args[0];if(!out)throw Error('Usage: node scripts/export_gr2_experimental.mjs NEW_OUTPUT_DIRECTORY [configuration.json]');
const configuration=args[1]?JSON.parse(await readFile(args[1])):defaultConfiguration(),source=await readModelOfficial('gr2');
await mkdir(path.dirname(path.resolve(out)),{recursive:true});
await mkdir(out,{recursive:false});
const plan=await prepareGr2Native(source,configuration),result=await generateGr2Native(source,configuration,plan.configuration_sha256);
const revision=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),dirty=execFileSync('git',['status','--porcelain'],{encoding:'utf8'}).trim();
const receipt={...result.receipt,revision,dirty:!!dirty,created_at:new Date().toISOString()};
await writeFile(path.join(out,'rg2_v003.frm'),result.candidate);await writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
await writeFile(path.join(out,'configuration.json'),JSON.stringify(plan.configuration,null,2)+'\n');
await mkdir(path.join(out,'SD/M10V'),{recursive:true});const pack=buildSdFilmPack((await nativeCatalog()).films.map(f=>f.id));await writeFile(path.join(out,'SD/M10V/FILMS.M10'),pack);
await writeFile(path.join(out,'README.txt'),`M10V GR II 第一版 · 实验离线候选\n尚未完成真机启动、更新、缓存和拍摄验证；此包不代表正式发布或建议直接刷入。\n目标：GR II 官方 3.00；不是 GR2013、GR III、GR IIIx 或 GR IV。\n已接入：五槽胶卷、原生细节页、SD 胶卷、日期/胶卷名水印、独立 HDF 菜单。\n未完成：配方及其他工具、完整页面对齐；继续研究，不判定底层不支持。\n网页：在对应工作树运行 npm start 后访问 /gr2/。\nSD/M10V 为胶卷资源，将 M10V 与 DCIM 并列；不得覆盖现有其他存档。\n已有有效机内记录优先于网页初始配置。初始 HDF=0，强度在机内 HDF 菜单设置。\n测试记录应覆盖：冷启动、原厂菜单返回、五槽切换、细节保存/重启、无卡/换卡、首张/连拍、RAW+JPEG、回放、时间戳、HDF0..3。\n恢复资料：保留原厂 rg2_v003.frm 与个人卡数据备份；本包不附原厂完整刷写恢复保证，无法启动后的恢复尚待验证。\n不执行相机、SD 或刷写操作；请先核对 receipt.json 的机型、源指纹及摘要。\n固件 SHA-256: ${receipt.candidate_sha256}\nSD FILMS.M10 SHA-256: ${createHash('sha256').update(pack).digest('hex')}\n`);
process.stdout.write(JSON.stringify({out,receipt},null,2)+'\n');

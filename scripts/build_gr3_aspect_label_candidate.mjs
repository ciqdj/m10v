// Local candidate through the same preflight/compiler/composer as web export.
import {mkdir,writeFile,readFile,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {resolve} from 'node:path';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import {buildSdFilmPack,auditSdFilmPack} from '../node/gr3-sd-film-pack.mjs';
import {encodeZip} from '../node/gr3-sd-film-export.mjs';
const run=promisify(execFile),sha=b=>createHash('sha256').update(b).digest('hex');
const name='m10v-gr3-aspect-label-r1-20261026',folder=resolve(process.argv[2]||'builds/'+name);
try{await stat(folder);throw Error('Candidate directory already exists; choose a new directory');}catch(e){if(e.code!=='ENOENT')throw e;}
const configuration=defaultConfiguration();
const options={appended_slots:true,hdf_enabled:true,debug_mode:false,
 extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const source=await readNativeOfficial('gr3'),plan=prepareNative(source,configuration,options);
const result=await generateNative(source,configuration,plan.configuration_sha256,options);
if(!result.manifest.capture_lifecycle?.snapshot?.live_color||!result.manifest.appended_slots||
 !result.manifest.hdf_enabled||!result.receipt.composition?.verified||
 result.receipt.composition.aspect_indicator?.first_id!==855||
 result.manifest.zoom?.min_mm!==28||result.manifest.zoom?.max_mm!==50||result.manifest.debug_mode)
 throw Error('Candidate feature/readback audit failed');
const pack=buildSdFilmPack();auditSdFilmPack(pack);
const json=x=>Buffer.from(JSON.stringify(x,null,2)+'\n'),sources={};
for(const p of Object.keys(result.manifest.sources))sources[p]=await readFile(p);
for(const p of ['LICENSE','THIRD_PARTY_NOTICES.md','third_party/curated-film-luts/LICENSE','third_party/spectral-film-lut/LICENSE',
 'native/gr3/m10v_aspect.c','native/gr3/m10v_aspect_dng.c','native/gr3/m10v_aspect_hooks.S','scripts/gr3_aspect_overlay.py',
 'node/gr3-native-library.mjs','node/gr3-m10v-native-build.mjs','node/gr3-integrated-components.mjs','node/gr3-native-budget.mjs',
 'node/gr3-runtime.mjs','node/gr3-runtime-worker.py','node/gr3-raw-nr.mjs','node/gr3-stock-presets.mjs','node/gr3x-native-port.mjs',
 'node/gr3-candidate-audit.mjs','node/gr3-version-unlock.mjs','node/gr3-store-plan.mjs','web/gr3/native-library-state.mjs',
 'scripts/build_gr3_aspect_label_candidate.mjs','tests/test_gr3_aspect.py','tests/test_gr3_aspect_indicator.py','tests/test_gr3_aspect_dng.py'])sources[p]=await readFile(p);
const provenance={candidate:name,status:'WAITING_FOR_USER_VALIDATION',model:'GR III',firmware:'2.10',
 created_at:new Date().toISOString(),change_scope:'XPan/6x7 native-style live-view labels',
 git_revision:(await run('git',['rev-parse','HEAD'])).stdout.trim(),
 git_branch:(await run('git',['branch','--show-current'])).stdout.trim(),
 git_status:(await run('git',['status','--short'])).stdout.trim().split('\n'),
 source_sha256:plan.source_sha256,runtime_source_sha256:plan.runtime_source_sha256,integration_source_sha256:plan.integration_source_sha256,
 source_files:Object.fromEntries(Object.entries(sources).map(([p,b])=>[p,sha(b)])),
 configuration_sha256:plan.configuration_sha256,bin_sha256:sha(result.candidate),runtime_sha256:sha(result.runtime),
 sd_sha256:sha(pack),camera_tested:false};
const files={'README.txt':await readFile('docs/testing/gr3-aspect-label-20261026.txt'),
 'LICENSE':sources.LICENSE,'THIRD_PARTY_NOTICES.md':sources['THIRD_PARTY_NOTICES.md'],
 'licenses/curated-film-luts.txt':sources['third_party/curated-film-luts/LICENSE'],
 'licenses/spectral-film-lut.txt':sources['third_party/spectral-film-lut/LICENSE'],
 'gr3/fwdc239b.bin':result.candidate,'gr3/receipt.json':json(result.receipt),'gr3/manifest.json':json(result.manifest),
 'gr3/configuration.json':json(plan.configuration),'SD/M10V/FILMS.M10':pack,
 'evidence/runtime.bin':result.runtime,'evidence/provenance.json':json(provenance),'evidence/source-snapshot.zip':encodeZip(sources)};
files.SHA256SUMS=Buffer.from(Object.entries(files).map(([p,b])=>sha(b)+'  '+p).join('\n')+'\n');
await mkdir(folder,{recursive:false});
for(const[p,b]of Object.entries(files)){await mkdir(resolve(folder,p,'..'),{recursive:true});await writeFile(resolve(folder,p),b);}
const zip=encodeZip(files);await writeFile(resolve(folder,name+'.zip'),zip);
await writeFile(resolve(folder,'SHA256SUMS'),files.SHA256SUMS.toString()+sha(zip)+'  '+name+'.zip\n');
console.log(JSON.stringify({folder,zip:resolve(folder,name+'.zip'),bin_sha256:sha(result.candidate),zip_sha256:sha(zip),
 hooks:result.receipt.verified_hooks,status:provenance.status,camera_tested:false},null,2));

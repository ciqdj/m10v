// Uses the existing web preflight/compiler/composer/auditor; no SD/device writes.
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
const name='m10v-gr3-film-timing-r1-20261021';
const folder=resolve(process.argv[2]||'builds/'+name);
try{await stat(folder);throw Error('Candidate directory already exists; choose a new output directory');}catch(e){if(e.code!=='ENOENT')throw e;}
const configuration=defaultConfiguration();
const options={appended_slots:true,hdf_enabled:true,debug_mode:false,
 extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const source=await readNativeOfficial('gr3'),plan=prepareNative(source,configuration,options);
const result=await generateNative(source,configuration,plan.configuration_sha256,options);
const snapshot=result.manifest.capture_lifecycle?.snapshot;
if(!snapshot?.live_color||snapshot.producer_sites?.length!==1||snapshot.producer_sites[0]!==0x5351ea9c||
 !result.manifest.appended_slots||!result.manifest.hdf_enabled||!result.receipt.composition?.verified)
 throw Error('Film submission, live preview, independent slots, HDF or composition audit missing');
const pack=buildSdFilmPack();auditSdFilmPack(pack);
const json=x=>Buffer.from(JSON.stringify(x,null,2)+'\n');
const sources={};for(const p of Object.keys(result.manifest.sources))sources[p]=await readFile(p);
for(const p of ['LICENSE','THIRD_PARTY_NOTICES.md','third_party/curated-film-luts/LICENSE',
 'third_party/spectral-film-lut/LICENSE'])sources[p]=await readFile(p);
for(const p of ['node/gr3-m10v-native-build.mjs','node/gr3-native-library.mjs',
 'scripts/build_gr3_film_timing_candidate.mjs','tests/test_gr3_slot_switch.py',
 'tests/test_gr3_live_color_preview.py','tests/test_gr3_isp_recipe_color.py',
 'tests/test_gr3_delivered_film_timing.py','node/gr3-native-routes.test.mjs'])sources[p]=await readFile(p);
const provenance={candidate:name,status:'WAITING_FOR_USER_VALIDATION',model:'GR III',firmware:'2.10',
 git_revision:(await run('git',['rev-parse','HEAD'])).stdout.trim(),
 git_branch:(await run('git',['branch','--show-current'])).stdout.trim(),
 git_status:(await run('git',['status','--short'])).stdout.trim().split('\n'),
 source_sha256:plan.source_sha256,runtime_source_sha256:plan.runtime_source_sha256,
 source_files:Object.fromEntries(Object.entries(sources).map(([p,b])=>[p,sha(b)])),
 configuration_sha256:plan.configuration_sha256,bin_sha256:sha(result.candidate),
 runtime_sha256:sha(result.runtime),sd_sha256:sha(pack),camera_tested:false};
const files={'README.txt':await readFile('docs/testing/gr3-film-timing-20261021.txt'),
 'LICENSE':sources.LICENSE,'THIRD_PARTY_NOTICES.md':sources['THIRD_PARTY_NOTICES.md'],
 'licenses/curated-film-luts.txt':sources['third_party/curated-film-luts/LICENSE'],
 'licenses/spectral-film-lut.txt':sources['third_party/spectral-film-lut/LICENSE'],
 'gr3/fwdc239b.bin':result.candidate,'gr3/receipt.json':json(result.receipt),
 'gr3/manifest.json':json(result.manifest),'gr3/configuration.json':json(plan.configuration),
 'SD/M10V/FILMS.M10':pack,'evidence/provenance.json':json(provenance),
 'evidence/source-snapshot.zip':encodeZip(sources),
 'evidence/validation.md':await readFile('docs/testing/gr3-film-timing-20261021.md')};
for(const name of ['reservation-reproduction.log','reproduction.log','arm-regression.log',
 'expanded-boundary-tests.log','preservation-regression.log','delivered-bin-tests-final.log',
 'delivered-hdf-tests.log','node-current-source-final.log','native-routes-final.log','server-isolated.log']){
 try{files['evidence/validation-logs/'+name]=await readFile('builds/gr3-film-timing-20261021-baseline/'+name);}
 catch(e){if(e.code!=='ENOENT')throw e;}
}
files['SHA256SUMS']=Buffer.from(Object.entries(files).map(([p,b])=>sha(b)+'  '+p).join('\n')+'\n');
await mkdir(folder,{recursive:false});
for(const[p,b]of Object.entries(files)){await mkdir(resolve(folder,p,'..'),{recursive:true});await writeFile(resolve(folder,p),b);}
await writeFile(resolve(folder,'evidence/runtime.bin'),result.runtime);
const zip=encodeZip(files);await writeFile(resolve(folder,name+'.zip'),zip);
await writeFile(resolve(folder,'SHA256SUMS'),files.SHA256SUMS.toString()+sha(zip)+'  '+name+'.zip\n');
console.log(JSON.stringify({folder,zip:resolve(folder,name+'.zip'),bin_sha256:sha(result.candidate),zip_sha256:sha(zip),
 hooks:result.receipt.verified_hooks,status:provenance.status,camera_tested:false},null,2));

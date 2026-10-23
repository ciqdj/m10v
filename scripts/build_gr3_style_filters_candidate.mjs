// Same preflight/compiler/composer/auditor as the web export. No camera writes.
import {mkdir,writeFile,readFile,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {resolve} from 'node:path';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration,selectNativeFilm} from '../web/gr3/native-library-state.mjs';
import {buildSdFilmPack,auditSdFilmPack} from '../node/gr3-sd-film-pack.mjs';
import {encodeZip} from '../node/gr3-sd-film-export.mjs';
const run=promisify(execFile),sha=b=>createHash('sha256').update(b).digest('hex');
const name='m10v-gr3-style-filters-r3-20261023',folder=resolve(process.argv[2]||'builds/'+name);
try{await stat(folder);throw Error('Candidate directory already exists; choose a new directory');}catch(e){if(e.code!=='ENOENT')throw e;}
let configuration=defaultConfiguration();
for(let i=0;i<5;i++)configuration=selectNativeFilm(configuration,i,291+i);
const options={appended_slots:true,hdf_enabled:true,debug_mode:false,
 extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const source=await readNativeOfficial('gr3'),plan=prepareNative(source,configuration,options);
const result=await generateNative(source,configuration,plan.configuration_sha256,options);
if(!result.manifest.capture_lifecycle?.snapshot?.live_color||!result.manifest.appended_slots||
 !result.manifest.hdf_enabled||!result.receipt.composition?.verified||
 result.receipt.composition.six_by_seven_resource_id===null||
 result.receipt.configuration.slots.some(s=>s.grain||s.soft||s.halo.gain||s.effects.leakGain))
 throw Error('Candidate feature/default/readback audit failed');
const pack=buildSdFilmPack();auditSdFilmPack(pack);
const json=x=>Buffer.from(JSON.stringify(x,null,2)+'\n'),sources={};
for(const p of Object.keys(result.manifest.sources))sources[p]=await readFile(p);
for(const p of ['LICENSE','THIRD_PARTY_NOTICES.md','third_party/curated-film-luts/LICENSE','third_party/spectral-film-lut/LICENSE',
 'native/gr3/m10v_aspect.c','native/gr3/m10v_aspect_dng.c','native/gr3/m10v_aspect_hooks.S','scripts/gr3_aspect_overlay.py',
 'node/gr3-native-library.mjs','node/gr3-m10v-native-build.mjs','node/gr3-integrated-components.mjs','node/gr3-native-budget.mjs',
 'node/gr3-runtime.mjs','node/gr3-runtime-worker.py','node/gr3-raw-nr.mjs','node/gr3-stock-presets.mjs','node/gr3x-native-port.mjs',
 'node/gr3-candidate-audit.mjs','node/gr3-version-unlock.mjs','node/gr3-store-plan.mjs','web/gr3/native-library-state.mjs',
 'scripts/build_gr3_style_filters_candidate.mjs','tests/test_gr3_aspect.py','tests/test_gr3_aspect_dng.py',
 'tests/test_gr3_capture_snapshot.py','tests/test_gr3_native_fast_capture.py','tests/test_gr3_sd_library.py',
 'tests/test_gr3_appended_recipe.py','tests/test_gr3_slot_switch.py','node/gr3-opt-in-effects.test.mjs','node/gr3-sd-film-pack.test.mjs'])sources[p]=await readFile(p);
for(const p of Object.keys(JSON.parse(await readFile('native/gr3/style-filters-reference.json','utf8')).files))sources[p]=await readFile(p);
const provenance={candidate:name,status:'WAITING_FOR_USER_VALIDATION',model:'GR III',firmware:'2.10',
 git_revision:(await run('git',['rev-parse','HEAD'])).stdout.trim(),
 git_branch:(await run('git',['branch','--show-current'])).stdout.trim(),
 git_status:(await run('git',['status','--short'])).stdout.trim().split('\n'),
 source_sha256:plan.source_sha256,runtime_source_sha256:plan.runtime_source_sha256,integration_source_sha256:plan.integration_source_sha256,
 source_files:Object.fromEntries(Object.entries(sources).map(([p,b])=>[p,sha(b)])),
 configuration_sha256:plan.configuration_sha256,bin_sha256:sha(result.candidate),runtime_sha256:sha(result.runtime),
 sd_sha256:sha(pack),camera_tested:false};
const files={'README.txt':await readFile('docs/testing/gr3-style-filters-20261023.txt'),
 'LICENSE':sources.LICENSE,'THIRD_PARTY_NOTICES.md':sources['THIRD_PARTY_NOTICES.md'],
 'licenses/street-monochrome-CC-BY-4.0.txt':sources['third_party/style-filter-luts/street-license'],
 'licenses/style-film-luts-MIT.txt':sources['third_party/style-filter-luts/film-luts-license'],
 'licenses/style-filter-attribution.md':sources['third_party/style-filter-luts/README.md'],
 'preview/style-filters.png':await readFile('docs/previews/style-filters-20261023.png'),
 'evidence/style-filters-research.md':await readFile('docs/research/gr3-style-filters-20261023.md'),
 'licenses/curated-film-luts.txt':sources['third_party/curated-film-luts/LICENSE'],
 'licenses/spectral-film-lut.txt':sources['third_party/spectral-film-lut/LICENSE'],
 'gr3/fwdc239b.bin':result.candidate,'gr3/receipt.json':json(result.receipt),'gr3/manifest.json':json(result.manifest),
 'gr3/configuration.json':json(plan.configuration),'SD/M10V/FILMS.M10':pack,
 'evidence/provenance.json':json(provenance),'evidence/source-snapshot.zip':encodeZip(sources),
 'evidence/validation.md':await readFile('docs/testing/gr3-style-filters-20261023.md')};
files.SHA256SUMS=Buffer.from(Object.entries(files).map(([p,b])=>sha(b)+'  '+p).join('\n')+'\n');
await mkdir(folder,{recursive:false});
for(const[p,b]of Object.entries(files)){await mkdir(resolve(folder,p,'..'),{recursive:true});await writeFile(resolve(folder,p),b);}
await writeFile(resolve(folder,'evidence/runtime.bin'),result.runtime);
const zip=encodeZip(files);await writeFile(resolve(folder,name+'.zip'),zip);
await writeFile(resolve(folder,'SHA256SUMS'),files.SHA256SUMS.toString()+sha(zip)+'  '+name+'.zip\n');
console.log(JSON.stringify({folder,zip:resolve(folder,name+'.zip'),bin_sha256:sha(result.candidate),zip_sha256:sha(zip),
 hooks:result.receipt.verified_hooks,status:provenance.status,camera_tested:false},null,2));

// Local candidate only; same preflight/compiler/composer/readback as web export.
import {mkdir,readFile,writeFile,stat} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import {buildSdFilmPack,auditSdFilmPack} from '../node/gr3-sd-film-pack.mjs';
import {encodeZip} from '../node/gr3-sd-film-export.mjs';
const name='m10v-gr3-ui-r1-20261027',out=resolve(process.argv[2]||'builds/'+name);
try{await stat(out);throw Error('Choose a new output directory');}catch(e){if(e.code!=='ENOENT')throw e;}
const options={appended_slots:true,hdf_enabled:true,debug_mode:false,halation_enabled:true,
 extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const configuration=defaultConfiguration(),official=await readNativeOfficial('gr3');
const plan=prepareNative(official,configuration,options);
const result=await generateNative(official,configuration,plan.configuration_sha256,options);
if(!result.receipt.composition?.verified||!result.manifest.appended_slots?.playback||
 !result.manifest.universal_halation||!result.manifest.hdf_enabled||result.manifest.resources.last_id!==1141)
 throw Error('UI candidate capability/readback failed');
const pack=buildSdFilmPack();auditSdFilmPack(pack);
const sha=b=>createHash('sha256').update(b).digest('hex'),json=x=>Buffer.from(JSON.stringify(x,null,2)+'\n');
const changed=execFileSync('git',['diff','--name-only'],{encoding:'utf8'}).trim().split('\n');
const sources={};
for(const p of new Set([...Object.keys(result.manifest.sources),...changed,
 'node/gr3-settings-menu.mjs','node/gr3-digital-hdf.mjs','node/gr3-m10v-native-build.mjs',
 'scripts/gr3_aspect_overlay.py','scripts/build_gr3_ui_candidate.mjs','docs/testing/gr3-ui-polish-20261027.txt',
 'tests/test_gr3_ui_polish.py','tests/test_gr3_watermark_group.py','tests/test_gr3_watermark_view.py','docs/testing/gr3-ui-polish-20261027.json']))
 if(p)sources[p]=await readFile(p);
const provenance={candidate:name,status:'WAITING_FOR_USER_VALIDATION',model:'GR III',firmware:'2.10',
 base_commit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
 git_status:execFileSync('git',['status','--short'],{encoding:'utf8'}).trim(),options,
 source_files:Object.fromEntries(Object.entries(sources).map(([p,b])=>[p,sha(b)])),
 source_sha256:plan.source_sha256,runtime_source_sha256:plan.runtime_source_sha256,
 integration_source_sha256:plan.integration_source_sha256,configuration_sha256:plan.configuration_sha256,
 bin_sha256:sha(result.candidate),runtime_sha256:sha(result.runtime),sd_sha256:sha(pack),camera_tested:false};
const files={'evidence/validation.json':await readFile('docs/testing/gr3-ui-polish-20261027.json'),'README.txt':await readFile('docs/testing/gr3-ui-polish-20261027.txt'),
 'gr3/fwdc239b.bin':result.candidate,'gr3/receipt.json':json(result.receipt),'gr3/manifest.json':json(result.manifest),
 'gr3/configuration.json':json(plan.configuration),'SD/M10V/FILMS.M10':pack,
 'evidence/provenance.json':json(provenance),'evidence/runtime.bin':result.runtime,
 'evidence/source-snapshot.zip':encodeZip(sources),
 'LICENSE':await readFile('LICENSE'),'THIRD_PARTY_NOTICES.md':await readFile('THIRD_PARTY_NOTICES.md'),
 'licenses/curated-film-luts.txt':await readFile('third_party/curated-film-luts/LICENSE'),
 'licenses/spectral-film-lut.txt':await readFile('third_party/spectral-film-lut/LICENSE')};
for(const file of ['npm-clean-baseline.log','npm-final.log','ui-final.log','current-real-pipeline.log',
 'aspect-final.log','aspect-indicator.log','gr3x-build.log','node-settings-final.log',
 'python-ui-baseline.log','pipeline-clean-baseline.log','pipeline-regression.log'])
 files['evidence/checks/'+file]=await readFile('builds/gr3-ui-20261027/evidence/'+file);
files.SHA256SUMS=Buffer.from(Object.entries(files).map(([p,b])=>sha(b)+'  '+p).join('\n')+'\n');
await mkdir(out,{recursive:false});
for(const[p,b]of Object.entries(files)){await mkdir(dirname(resolve(out,p)),{recursive:true});await writeFile(resolve(out,p),b);}
const zip=encodeZip(files);await writeFile(resolve(out,name+'.zip'),zip);
await writeFile(resolve(out,'SHA256SUMS'),files.SHA256SUMS.toString()+sha(zip)+'  '+name+'.zip\n');
console.log(JSON.stringify({out,bin_sha256:sha(result.candidate),zip_sha256:sha(zip),camera_tested:false},null,2));

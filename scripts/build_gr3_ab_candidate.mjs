// Reproducible GR III A/B candidate. HDF is a feature, even at strength zero.
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import {encodeZip} from '../node/gr3-sd-film-export.mjs';
import {buildSdFilmPack,auditSdFilmPack} from '../node/gr3-sd-film-pack.mjs';

const compare=process.argv.includes('--compare');
if(!compare)throw Error('Current sources implement stage-two A/B. Use --compare; earlier read-only candidates remain archived.');
const folder=resolve(process.argv[2]||'builds/gr3-ab-no-live-ui-20261021');
const configuration=defaultConfiguration();
configuration.slots[0].film=69;configuration.slots[1].film=75;
const options={hdf_enabled:true,debug_mode:true,
 extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const source=await readNativeOfficial('gr3');
const plan=prepareNative(source,configuration,options);
const result=await generateNative(source,configuration,plan.configuration_sha256,options);
if(!result.receipt.digital_hdf||!result.manifest.hdf_enabled||
 result.manifest.hdf_menu.route!==0x0200f102||
 result.manifest.settings_menu.ab_host?.stage!=='compare'||
 result.manifest.settings_menu.ab_host?.direct_pair!==true||
 result.manifest.settings_menu.ab_host?.live_ui!==false)
 throw Error('A/B or HDF missing from delivered candidate');
const pack=buildSdFilmPack();auditSdFilmPack(pack);
const readme=await readFile('docs/testing/gr3-ab-no-live-ui-20261021.txt');
const rows={
 'gr3/fwdc239b.bin':result.candidate,
 'gr3/receipt.json':Buffer.from(JSON.stringify(result.receipt,null,2)),
 'gr3/manifest.json':Buffer.from(JSON.stringify(result.manifest,null,2)),
 'README.txt':readme,'SD/M10V/FILMS.M10':pack};
await mkdir(`${folder}/gr3`,{recursive:true});
await mkdir(`${folder}/SD/M10V`,{recursive:true});
for(const [name,bytes] of Object.entries(rows))await writeFile(`${folder}/${name}`,bytes);
await writeFile(`${folder}/gr3/manifest.json`,JSON.stringify(result.manifest,null,2));
await writeFile(`${folder}/gr3/runtime.bin`,result.runtime);
await writeFile(`${folder}/m10v-gr3-ab-no-live-ui.zip`,encodeZip(rows));
console.log(JSON.stringify({folder,sha256:result.receipt.candidate_sha256,
 hooks:result.receipt.verified_hooks,hdf:result.receipt.digital_hdf,
 camera_tested:result.receipt.camera_tested},null,2));

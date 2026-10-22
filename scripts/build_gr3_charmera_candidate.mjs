// Same audited native build as the workbench, with preserved HDF/extension features.
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration,selectNativeFilm} from '../web/gr3/native-library-state.mjs';
import {buildSdFilmPack,auditSdFilmPack} from '../node/gr3-sd-film-pack.mjs';
import {encodeZip} from '../node/gr3-sd-film-export.mjs';
const folder=resolve(process.argv[2]||'builds/m10v-charmera-gr3-20261021-c03');
await mkdir(folder,{recursive:false});
let configuration=defaultConfiguration();
for(let i=0;i<4;i++){configuration=selectNativeFilm(configuration,i,289);configuration.slots[i].effects.charmeraColor=i;}
configuration=selectNativeFilm(configuration,4,33);
const options={hdf_enabled:true,debug_mode:false,extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const original=await readNativeOfficial('gr3'),plan=prepareNative(original,configuration,options);
const result=await generateNative(original,configuration,plan.configuration_sha256,options);
if(!result.manifest.hdf_enabled||result.receipt.sd_film_library.supported_films!==48||!result.manifest.detail.variant_ids.charmera.includes(29))throw Error('Charmera/HDF capability missing');
const pack=buildSdFilmPack(),audit=auditSdFilmPack(pack);
const json=v=>Buffer.from(JSON.stringify(v,null,2)+'\n');
const provenance={candidate:'m10v-charmera-gr3-20261021-c03',stage:'RELEASE_AUTHORIZED_CAMERA_UNTESTED',model:'GR III',public_firmware:'2.10',
 git_revision:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),git_status:execFileSync('git',['status','--short'],{encoding:'utf8'}),
 source_fingerprints:result.manifest.sources,configuration_sha256:plan.configuration_sha256,options,camera_tested:false};
const rows={'fw/fwdc239b.bin':result.candidate,'SD/M10V/FILMS.M10':pack,'evidence/runtime.bin':result.runtime,
 'evidence/manifest.json':json(result.manifest),'evidence/receipt.json':json(result.receipt),'evidence/configuration.json':json(plan.configuration),
 'evidence/provenance.json':json(provenance),'evidence/sd-audit.json':json(audit),'README.txt':await readFile('docs/testing/gr3-charmera-fix-20261021.txt')};
const hashes=Object.fromEntries(Object.entries(rows).map(([name,bytes])=>[name,createHash('sha256').update(bytes).digest('hex')]));rows['SHA256.json']=json(hashes);
for(const [name,bytes]of Object.entries(rows)){await mkdir(resolve(folder,name,'..'),{recursive:true});await writeFile(resolve(folder,name),bytes);}
const zip=encodeZip(rows),zipPath=resolve(folder,'m10v-charmera-gr3-20261021-c03.zip');await writeFile(zipPath,zip);
console.log(JSON.stringify({folder,zip:zipPath,zip_sha256:createHash('sha256').update(zip).digest('hex'),firmware_sha256:hashes['fw/fwdc239b.bin'],pack_sha256:hashes['SD/M10V/FILMS.M10'],verified_hooks:result.receipt.verified_hooks,stage:provenance.stage},null,2));

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {nativeCatalog} from './gr3-native-library.mjs';
import {buildSdFilmPack,auditSdFilmPack,sdFilmRecord} from './gr3-sd-film-pack.mjs';
const names=['Tri-X 400','Ilford Delta 100','Ilford Pan 400','Rollei Infrared 400','Ilford SFX 200','Fomapan 400','CatLABS X Film 80'];
test('D76 adds the seven exact requested identities after T-Max and preserves all groups',async()=>{
 const c=await nativeCatalog();assert.equal(c.film_count,37);
 assert.deepEqual(c.films.filter(f=>f.group==='D76').map(f=>f.name),['T-Max 100',...names]);
 for(let i=0;i<7;i++){const f=c.films.find(f=>f.id===299+i);assert.equal(f.name,names[i]);assert.equal(f.approximation,true);assert.equal(f.film_calibrated,false);assert.ok(f.reference&&f.official&&f.icon_url);}
 const pack=buildSdFilmPack();assert.equal(auditSdFilmPack(pack).count,37);
 for(let i=0;i<7;i++)assert.equal(sdFilmRecord(299+i).subarray(16,40).toString('ascii').split('\0')[0],names[i]);
});
test('all D76 LUTs are distinct monochrome with monotone neutral ramps',()=>{
 const w=JSON.parse(readFileSync(new URL('../web/gr3/d76-luts.json',import.meta.url)));
 assert.deepEqual(w.stocks.map(s=>s.name),names);const seen=new Set();
 for(const s of w.stocks){assert.equal(s.values.length,10125);let last=-1;
  for(let i=0;i<s.values.length;i+=3)assert.ok(s.values[i]===s.values[i+1]&&s.values[i]===s.values[i+2]);
  for(let i=0;i<15;i++){const v=s.values[((i*15+i)*15+i)*3];assert.ok(v>=last);last=v;}
  seen.add(JSON.stringify(s.values));assert.equal(s.official_lut,false);
 }assert.equal(seen.size,7);
});

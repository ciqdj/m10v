import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {Gr4Runtime} from './gr4-runtime.mjs';
const sample=new URL('../bin/fwdc248b-gr4-officical.bin',import.meta.url);
test('GR IV local official sample enters the real editor with source-derived filters',{skip:!existsSync(sample)},async()=>{
  const folder=await mkdtemp(path.join(os.tmpdir(),'m10v-gr4-local-'));
  try{
    const runtime=new Gr4Runtime(folder);
    assert.equal(typeof runtime.importOfficial,'function','GR IV local sample import is not implemented');
    const project=await runtime.importOfficial();
    assert.equal(project.input.sha256,'a2f664dfca034059eb0fd6e18ab08684c326b4a034d85c164dad7e1ec9b5655f');
    assert.ok(project.filters.length>=14);
    assert.ok(project.filters.some(v=>v.name&&!v.name.startsWith('Style')));
    assert.equal(project.hardware,'not_tested');
  }finally{await rm(folder,{recursive:true,force:true});}
});

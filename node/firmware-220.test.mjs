import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {inspectOfficial,readOfficialSection} from './firmware.mjs';
import {inspectModelFirmware} from './model-firmware.mjs';
const fixture=process.env.M10V_GR3_220_FIXTURE;
test('official GR III 2.20 imports with its own identity and section sizes',{skip:!fixture||!existsSync(fixture)},async()=>{
 const data=readFileSync(fixture),report=inspectOfficial(data);
 assert.equal(report.public_version,'2.20');assert.equal(report.internal_version,'2.20.20.28');
 assert.equal(report.sections.length,14);assert.equal(readOfficialSection(data,'RTOS').length,17520384);
 assert.equal((await inspectModelFirmware(data)).workspace_url,'/gr3/');
 const changed=Buffer.from(data);changed[200]^=1;assert.throws(()=>inspectOfficial(changed),/identity/);
});

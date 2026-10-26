import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {inspectOfficial,readOfficialSection} from './firmware.mjs';
import {inspectModelFirmware} from './model-firmware.mjs';
import {decodeFrameMap,repackWithTarget,sum32} from './gr3-frames.mjs';
const fixture=process.env.M10V_GR3_220_FIXTURE;
test('official GR III 2.20 imports with its own identity and section sizes',{skip:!fixture||!existsSync(fixture)},async()=>{
 const data=readFileSync(fixture),report=inspectOfficial(data);
 assert.equal(report.public_version,'2.20');assert.equal(report.internal_version,'2.20.20.28');
 assert.equal(report.sections.length,14);assert.equal(readOfficialSection(data,'RTOS').length,17520384);
 assert.equal((await inspectModelFirmware(data)).workspace_url,'/gr3/');
 const changed=Buffer.from(data);changed[200]^=1;assert.throws(()=>inspectOfficial(changed),/identity/);
});
test('2.20 frame replay uses its own decoded length and preserves untouched bytes',{skip:!fixture||!existsSync(fixture)},()=>{
 const data=readFileSync(fixture),{decoded}=decodeFrameMap(data);
 assert.equal(decoded.length,59798532);
 assert.ok(repackWithTarget(data,decoded).candidate.equals(data));
 const target=Buffer.from(decoded);target[40_000_000]^=1;
 target.writeUInt32LE(0,target.length-4);target.writeUInt32LE(-sum32(target)>>>0,target.length-4);
 const {candidate}=repackWithTarget(data,target);
 assert.equal(candidate.readUInt32LE(candidate.length-8),59798532);
 assert.equal(sum32(candidate),0);
 assert.ok(decodeFrameMap(candidate).decoded.equals(target));
 assert.throws(()=>decodeFrameMap(data,59718388),/frame sizes/);
 assert.throws(()=>repackWithTarget(data,target.subarray(0,-4)),/target length/);
});

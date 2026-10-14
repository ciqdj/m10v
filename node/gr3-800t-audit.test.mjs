import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { audit800TCandidate } from './gr3-800t-audit.mjs';
import { decodeFrameMap,sum32 } from './gr3-frames.mjs';
import { prepare800T,build800T } from './gr3-800t-build.mjs';
const source = new URL('../fwdc239b.bin', import.meta.url);
const candidate = new URL('../builds/gr3-800t-reverse/injection/800t-research.bin', import.meta.url);
const expected = new URL('../builds/gr3-800t-reverse/injection/800t-research.expected.json', import.meta.url);
test('independent 800T decode compares all modules and rejects expected-code changes',
  { skip: ![source, candidate, expected].every(existsSync) }, () => {
    const official = readFileSync(source), bytes = readFileSync(candidate);
    const plan = JSON.parse(readFileSync(expected));
    const report = audit800TCandidate(official, bytes, plan);
    assert.equal(report.exactExpectedPayloads, true); assert.equal(report.cameraTested, false);
    const altered = structuredClone(plan);
    altered.tail_hex = 'ff' + altered.tail_hex.slice(2);
    assert.throws(() => audit800TCandidate(official, bytes, altered), /unexpected bytes in RTOS/);
    assert.throws(() => audit800TCandidate(official, bytes, { ...plan, source_sha256: '0'.repeat(64) }), /identity/);
    const outside = structuredClone(plan);
    outside.patches.push({ offset: 0, expected_hex: '00', replacement_hex: '01' });
    assert.throws(() => audit800TCandidate(official, bytes, outside), /permitted payloads/);
  });
test('accepted-plan audit rejects a wrong branch even when writer expectation agrees',
 {skip:!existsSync(source)},async()=>{
  // Compile the current writer instead of binding the current code lock to
  // an ignored historical research binary from an earlier kernel revision.
  const official=readFileSync(source),selection={strength:'strong',timestamp:true};
  const preflight=prepare800T(official,selection);
  const result=await build800T(official,selection,preflight.configuration_sha256);
  const bytes=result.candidate;
  const plan=JSON.parse(readFileSync(new URL('../builds/gr3-800t-output/'+
    result.audit.candidateSha256+'.expected.json',import.meta.url)));
  assert.equal(audit800TCandidate(official,bytes,plan,preflight).acceptedPlanBound,true);
  const decoded=decodeFrameMap(bytes,bytes.readUInt32LE(bytes.length-8)).decoded;
  const changed=structuredClone(plan),tail=Buffer.from(plan.tail_hex,'hex');
  tail[0x3380]^=1;changed.tail_hex=tail.toString('hex');
  decoded[0x10870+plan.tail_offset+0x3380]^=1;
  decoded.writeUInt32LE(0,decoded.length-4);decoded.writeUInt32LE(-sum32(decoded)>>>0,decoded.length-4);
  const frames=[];
  for(let i=0;i<decoded.length;i+=0x6000){const slice=decoded.subarray(i,i+0x6000),prefix=Buffer.alloc(2);prefix.writeUInt16BE(0x8000|slice.length);frames.push(prefix,slice);}
  frames.push(Buffer.alloc(2));const payload=Buffer.concat(frames),footer=Buffer.from(bytes.subarray(-24));
  footer.writeUInt32LE(payload.length,12);footer.writeUInt32LE(0,20);
  const wrong=Buffer.concat([bytes.subarray(0,128),payload,Buffer.alloc(-(128+payload.length)&3),footer]);
  wrong.writeUInt32LE(-sum32(wrong)>>>0,wrong.length-4);
  assert.equal(audit800TCandidate(official,wrong,changed).exactExpectedPayloads,true);
  assert.throws(()=>audit800TCandidate(official,wrong,changed,preflight),/independently compiled accepted plan/);
 });

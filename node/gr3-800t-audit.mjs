// Decode independently of the Python container writer and compare every byte
// with the locally constructed expected plan. A supplied plan is not proof of
// camera safety; callers must retain their own preparation and expectation.
import { createHash } from 'node:crypto';
import { inspectOfficial, SHA256 } from './firmware.mjs';
import { decodeFrameMap } from './gr3-frames.mjs';
import { auditGr3Candidate } from './gr3-candidate-audit.mjs';
import { expected800TBytes } from './gr3-800t-expected.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const fail = message => { throw new Error(`800T independent audit: ${message}`); };
function hex(value) {
  if (typeof value !== 'string' || !/^(?:[a-f0-9]{2})+$/.test(value)) fail('invalid expected bytes');
  return Buffer.from(value, 'hex');
}

export function audit800TCandidate(official, candidate, expectation, prepared=null) {
  const source = inspectOfficial(official);
  if (expectation?.schema !== 'm10v-gr3-800t-expected-bytes/v1' ||
      expectation.source_sha256 !== SHA256 ||
      !/^[a-f0-9]{64}$/.test(expectation.configuration_sha256 || '')) fail('expected plan identity differs');
  const structural = auditGr3Candidate(official, candidate);
  const original = decodeFrameMap(official).decoded;
  const actual = decodeFrameMap(candidate, structural.decodedBytes).decoded;
  const expected = Buffer.from(original);
  let position = 0;
  const ranges = new Map(source.sections.map(row => {
    const start = position; position += row.size;
    return [row.name, { start, end: position }];
  }));
  if (!Array.isArray(expectation.patches) || expectation.patches.length > 10000) fail('invalid patch list');
  const occupied = [];
  for (const patch of expectation.patches) {
    const before = hex(patch.expected_hex), after = hex(patch.replacement_hex);
    const start = patch.offset, end = start + before.length;
    if (!Number.isSafeInteger(start) || before.length !== after.length ||
        !['RTOS', 'ICONBIN'].some(name => start >= ranges.get(name).start + 16 && end <= ranges.get(name).end))
      fail('patch outside permitted payloads');
    if (occupied.some(([left, right]) => start < right && left < end)) fail('overlapping expected patches');
    if (!original.subarray(start, end).equals(before)) fail('expected patch preimage differs');
    occupied.push([start, end]); after.copy(expected, start);
  }
  const tail = hex(expectation.tail_hex), rtos = ranges.get('RTOS');
  const oldSize = rtos.end - rtos.start - 16, tailOffset = expectation.tail_offset;
  if (!Number.isSafeInteger(tailOffset) || tailOffset < oldSize || tailOffset > oldSize + 4096 ||
      !(prepared?tail.length===49152:[24576,32768,49152].includes(tail.length)) ||
      tailOffset + tail.length - oldSize !== structural.rtosGrowth)
    fail('append placement differs');
  if(prepared) {
    if(prepared.configuration_sha256!==expectation.configuration_sha256||prepared.source_sha256!==SHA256)
      fail('accepted configuration differs');
    const trusted=expected800TBytes(official,prepared);
    if(!trusted.decoded.equals(expected)||!trusted.tail.equals(tail)||trusted.tailOffset!==tailOffset)
      fail('writer bytes differ from independently compiled accepted plan');
  }
  let actualPosition = 0;
  for (const row of source.sections) {
    const range = ranges.get(row.name);
    let block = expected.subarray(range.start, range.end);
    if (row.name === 'RTOS') {
      block = Buffer.concat([block, Buffer.alloc(tailOffset - oldSize), tail]);
      block.writeUInt32LE(block.length - 16, 12);
    }
    if (!actual.subarray(actualPosition, actualPosition + block.length).equals(block))
      fail(`unexpected bytes in ${row.name}`);
    actualPosition += block.length;
  }
  if (actualPosition + 4 !== actual.length) fail('decoded extent differs');
  return { schema: 'm10v-gr3-800t-independent-audit/v1', ...structural,
    configurationSha256: expectation.configuration_sha256,
    expectedProgramSha256: sha(tail), patchCount: occupied.length,
    exactExpectedPayloads: true, acceptedPlanBound:Boolean(prepared), cameraTested: false };
}

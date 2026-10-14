// Independent trace-package compilation; never reads the writer's expectation.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {inspectOfficial} from '../node/firmware.mjs';
import {decodeFrameMap} from '../node/gr3-frames.mjs';
import {auditGr3Candidate} from '../node/gr3-candidate-audit.mjs';
import {expected800TBytes} from '../node/gr3-800t-expected.mjs';
const [sourcePath,candidatePath,preparedPath,outPath]=process.argv.slice(2);
const official=readFileSync(sourcePath),candidate=readFileSync(candidatePath),prepared=JSON.parse(readFileSync(preparedPath));
const sha=x=>createHash('sha256').update(x).digest('hex');
const structural=auditGr3Candidate(official,candidate),profile=inspectOfficial(official);
const trusted=expected800TBytes(official,prepared),tail=Buffer.alloc(49152);trusted.tail.copy(tail);
const logger=readFileSync(new URL('../builds/gr3-800t-independent-menu/logger-arm.bin',import.meta.url));
const adapter=readFileSync(new URL('../builds/gr3-800t-independent-menu/adapter-arm.bin',import.meta.url));
assert.equal(sha(logger),'a3215116ea3f828097159473200c7e76e16a5202122cb29752da8818f798d476');
assert.equal(sha(adapter),'2266e3dcc98688b908b43b0b73d63921a6c34ca88535cf6f18169f006374e4fa');
assert.ok(logger.length<=1024&&adapter.length<=4096);
// BL at 540bb008 goes to 540bcc00; native core begins at 540bb800.
tail.writeUInt32LE(0xeb0006fc,0x5008);logger.copy(tail,0x6800);adapter.copy(tail,0x6c00);
const actual=Buffer.from(decodeFrameMap(candidate,structural.decodedBytes).decoded);
let sourceAt=0,actualAt=0;
for(const row of profile.sections){
 let block=trusted.decoded.subarray(sourceAt,sourceAt+row.size);sourceAt+=row.size;
 if(row.name==='RTOS'){
  block=Buffer.concat([block,Buffer.alloc(trusted.tailOffset-(row.size-16)),tail]);
  block.writeUInt32LE(block.length-16,12);
 }
 assert.ok(actual.subarray(actualAt,actualAt+block.length).equals(block),'unexpected bytes in '+row.name);actualAt+=block.length;
}
assert.equal(actualAt+4,actual.length);
const report={schema:'m10v-800t-hardware-trace-audit/v3',...structural,exactExpectedPayloads:true,
 configurationSha256:prepared.configuration_sha256,loggerSha256:sha(logger),adapterSha256:sha(adapter),
 executableMapping:'existing identity-mapped 0x54000000 section; added code below 0x540c2000',
 cameraTested:false,status:'HARDWARE_TRACE_REQUIRED'};
if(outPath)writeFileSync(outPath,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));

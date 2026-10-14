import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync,readdirSync} from 'node:fs';import os from 'node:os';
import {runGr3Runtime} from './gr3-runtime.mjs';import {createStorePlan} from './gr3-store-plan.mjs';
test('aborted firmware request terminates its child and cleans the owned temporary folder',async()=>{
 const before=new Set(readdirSync(os.tmpdir()).filter(n=>n.startsWith('m10v-gr3-build-')));
 const controller=new AbortController(),source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
 const at=Date.now();setTimeout(()=>controller.abort(),500);
 await assert.rejects(()=>runGr3Runtime(source,createStorePlan({variant:'street',features:['film']}),'build',undefined,{signal:controller.signal}),/取消|abort/i);
 assert.ok(Date.now()-at<5000,'cancel must not wait for full build');
 assert.deepEqual(readdirSync(os.tmpdir()).filter(n=>n.startsWith('m10v-gr3-build-')&&!before.has(n)),[]);
});

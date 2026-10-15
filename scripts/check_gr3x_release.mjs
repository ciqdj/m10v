// Keep the GR III-only detail adapter out of the GR IIIx release path.
import assert from 'node:assert/strict';
import {readNativeOfficial,prepareNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import {inspectOfficial} from '../node/firmware.mjs';
const source=await readNativeOfficial('gr3x'),report=inspectOfficial(source);
assert.equal(report.model,'GR IIIx');
assert.throws(()=>prepareNative(source,defaultConfiguration()),/GR IIIx 原生导出尚未支持/);
console.log(JSON.stringify({model:report.model,source_sha256:report.sha256,native_export:'blocked',reason:'GR III-only stock detail addresses; no GR IIIx native firmware generated'}));

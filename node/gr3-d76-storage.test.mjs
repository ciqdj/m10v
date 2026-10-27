import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {auditSdFilmPack,sdCrc} from './gr3-sd-film-pack.mjs';

test('lossless ROM storage change keeps authentic user-validated RC1 library readable',()=>{
 const pack=gunzipSync(readFileSync(new URL('../tests/fixtures/gr3-anime-e6-rc1-films.m10.gz',import.meta.url)));
 assert.equal(auditSdFilmPack(pack).count,44);
 const copy=Buffer.from(pack),record=copy.subarray(4096,4096+12288);
 record[100]^=1;record.writeUInt32LE(sdCrc(record.subarray(0,-4)),12284);
 copy.writeUInt32LE(record.readUInt32LE(12284),68);copy.writeUInt32LE(sdCrc(copy.subarray(0,4092)),4092);
 assert.throws(()=>auditSdFilmPack(copy),/校验|不兼容/);
});

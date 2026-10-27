import test from 'node:test';
import assert from 'node:assert/strict';
import {fullLibraryRequest} from '../web/gr3/full-library.mjs';
test('full library uses the exported model and all catalog films, independent of initial selected slots',()=>{
 const catalog=[{id:33},{id:34},{id:68}];
 const r=fullLibraryRequest('gr3x',catalog);
 assert.equal(r.url,'/api/gr3/sd-library/export');
 assert.deepEqual(r.body,{model:'gr3x',ids:[33,34,68]});
 assert.equal(fullLibraryRequest('gr4',catalog).url,'/api/gr4/native-library/sd-export');
 assert.throws(()=>fullLibraryRequest('gr2',catalog),/机型/);
 assert.throws(()=>fullLibraryRequest('gr3',[]),/目录/);
});

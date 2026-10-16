import test from 'node:test';
import assert from 'node:assert/strict';
import {groupedFilmOptions} from '../web/gr3/film-picker.mjs';

test('appended curated films stay together without changing IDs or within-group order',()=>{
 const option=(id,group)=>({value:String(id),dataset:{group}});
 const input=[option(33,'M10V精选'),option(34,'内置胶片'),option(35,'内置胶片'),option(66,'M10V精选'),option(67,'M10V精选'),option(68,'M10V精选')];
 const output=groupedFilmOptions(input);
 assert.deepEqual(output.map(v=>v.value),['33','66','67','68','34','35']);
 assert.deepEqual(input.map(v=>v.value),['33','34','35','66','67','68']);
 assert.equal(output[1],input[3]);
});

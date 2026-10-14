import test from 'node:test';import assert from 'node:assert/strict';
import * as editor from '../web/gr3/editor-state.mjs';
test('drag edits form one undo transaction and stale async completion is rejected',()=>{
 const store=editor.createEditorState({value:0});store.begin();store.update({value:1});store.update({value:2});store.commit();
 assert.equal(store.snapshot().config.value,2);const revision=store.snapshot().revision;
 store.undo();assert.equal(store.snapshot().config.value,0);assert.equal(store.isCurrent(revision),false);
 store.redo();assert.equal(store.snapshot().config.value,2);
});
test('snapshots cannot mutate live configuration',()=>{
 const store=editor.createEditorState({items:[1]});const s=store.snapshot();s.config.items.push(2);
 assert.deepEqual(store.snapshot().config.items,[1]);
});
test('restoring a saved draft clears old undo history',()=>{
 const store=editor.createEditorState({value:0});store.update({value:1});store.restore({value:9});store.undo();
 assert.equal(store.snapshot().config.value,9);assert.equal(store.snapshot().canUndo,false);
});
test('old image imports cannot restore edits after reset or a newer import',()=>{
 const gate=editor.createImportGate();const first=gate.start('slot2');gate.invalidate();assert.equal(gate.current(first),false);
 const next=gate.start('slot2'),latest=gate.start('slot2');assert.equal(gate.current(next),false);assert.equal(gate.current(latest),true);
});

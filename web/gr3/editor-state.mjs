export function createEditorState(initial){
 let config=structuredClone(initial),revision=0,transaction=null;const undo=[],redo=[];
 const snapshot=()=>({config:structuredClone(config),revision,canUndo:undo.length>0,canRedo:redo.length>0});
 return {snapshot,isCurrent:r=>r===revision,
  restore(next){config=structuredClone(next);revision++;undo.length=0;redo.length=0;transaction=null;},
  begin(){transaction??=structuredClone(config);},
  update(next){if(!transaction){undo.push(structuredClone(config));redo.length=0;}config=structuredClone(next);revision++;},
  commit(){if(transaction){if(JSON.stringify(transaction)!==JSON.stringify(config)){undo.push(transaction);redo.length=0;}transaction=null;}},
  undo(){if(undo.length){redo.push(config);config=undo.pop();revision++;transaction=null;}},
  redo(){if(redo.length){undo.push(config);config=redo.pop();revision++;transaction=null;}},
 };
}
export function createImportGate(){
 let epoch=0;const keys=new Map();
 return {start(key){const revision=(keys.get(key)||0)+1;keys.set(key,revision);return {key,revision,epoch};},
   current(token){return token.epoch===epoch&&keys.get(token.key)===token.revision;},
   invalidate(){epoch++;keys.clear();}};
}

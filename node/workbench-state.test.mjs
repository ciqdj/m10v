import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeWorkbenchDraft,preserveLegacyDraft} from '../web/gr3/workbench-state.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
test('custom film drafts migrate supported selections and block unresolved slots without custom tools',()=>{
 const old={profile:'custom',features:['film','recipes','presets','aspect','rawNr'],filmIds:['supported','lut-old'],filmTexture:{supported:{grain:2,hdf:1}},recipes:[{slotId:'builtin-15'}],rawNr:{mode:'threshold',iso:6400}};
 const result=normalizeWorkbenchDraft(old,[{id:67,legacy_id:'supported'}]);
 assert.equal(result.profile,'native');assert.deepEqual(result.features,['film','aspect','rawNr']);
 assert.deepEqual(result.recipes,[]);assert.deepEqual(result.stockPresets,[]);
 assert.equal(result.nativeConfiguration.slots[0].film,67);assert.equal(result.nativeConfiguration.slots[0].grain,2);assert.equal(result.nativeConfiguration.slots[0].soft,0);
 assert.deepEqual(result.unresolvedSlots,[{slot:1,id:'lut-old'}]);assert.deepEqual(result.rawNr,{mode:'threshold',iso:6400});
 assert.equal(old.recipes.length,1);
});
test('native draft and history preserve per-slot effects while enforcing compatible features',()=>{
 const config=defaultConfiguration();config.slots[2].effects.leakGain=7;config.stamp=2;
 const result=normalizeWorkbenchDraft({profile:'native',features:['film','timestamp','level','recipes'],nativeConfiguration:config});
 assert.equal(result.nativeConfiguration.slots[2].effects.leakGain,7);assert.equal(result.nativeConfiguration.stamp,2);
 assert.deepEqual(result.features,['film','timestamp','level']);
 assert.equal(normalizeWorkbenchDraft({features:[]},[],config).nativeConfiguration.stamp,0);
});
test('legacy backup retains the exact first draft before future saves',()=>{
 const data=new Map();const storage={getItem:key=>data.get(key)??null,setItem:(key,value)=>data.set(key,value)};
 const draft={profile:'custom',features:['recipes']};
 preserveLegacyDraft(storage,'draft','original',draft);preserveLegacyDraft(storage,'draft','later',draft);
 assert.equal(storage.getItem('draft-legacy-backup'),'original');
 preserveLegacyDraft(storage,'new','native',{profile:'native',features:['film']});assert.equal(storage.getItem('new-legacy-backup'),null);
});

test('legacy undo snapshots cannot restore custom recipe or preset modes',()=>{
 const result=normalizeWorkbenchDraft({profile:'custom',features:['recipes','presets','negativeGrain'],recipes:[{slotId:'builtin-15'}]});
 assert.equal(result.profile,'native');assert.deepEqual(result.features,['film','negativeGrain']);assert.deepEqual(result.recipes,[]);
});

test('HDF-only native drafts preserve independence through restore and undo normalization',()=>{
 const config=defaultConfiguration();config.hdf=2;
 const result=normalizeWorkbenchDraft({profile:'native',features:['digitalHdf','aspect'],nativeConfiguration:config});
 assert.deepEqual(result.features,['digitalHdf','aspect']);assert.equal(result.nativeConfiguration.hdf,2);
 assert.equal(result.nativeConfiguration.slots[0].soft,0);
 const restored=normalizeWorkbenchDraft(result);assert.deepEqual(restored.features,result.features);
 assert.equal(restored.nativeConfiguration.hdf,2);
});

test('combined HDF and film drafts retain film and preserve global HDF separately',()=>{
 const config=defaultConfiguration();config.hdf=3;
 const result=normalizeWorkbenchDraft({profile:'native',features:['film','digitalHdf'],nativeConfiguration:config});
 assert.deepEqual(result.features,['film','digitalHdf']);assert.equal(result.nativeConfiguration.hdf,3);
});

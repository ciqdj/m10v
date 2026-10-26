// Uploaded originals remain immutable. Patches only target a verified per-model
// build baseline, never an unported firmware's addresses.
import {inspectOfficial} from './firmware.mjs';
import {readModelOfficial} from './model-firmware.mjs';

export async function resolveBuildSource(uploaded) {
 const imported=inspectOfficial(uploaded);
 const model=imported.model==='GR III'?'gr3':'gr3x';
 const source=await readModelOfficial(model),baseline=inspectOfficial(source);
 if(baseline.model!==imported.model)throw Error('构建基线与上传包机型不一致');
 return {source,report:{...imported,build_source:{
  model:baseline.model,public_version:baseline.public_version,internal_version:baseline.internal_version,
  sha256:baseline.sha256,imported_sha256:imported.sha256,
  imported_public_version:imported.public_version,imported_internal_version:imported.internal_version,
  normalized:baseline.sha256!==imported.sha256,
 }}};
}

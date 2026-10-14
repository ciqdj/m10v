import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { inspect800TEvidence } from './gr3-800t-evidence.mjs';
import { normalize800T,create800TFilm } from './gr3-800t-plan.mjs';
import { createFilmPlan } from './gr3-film-plan.mjs';
import { run800TBuild } from './gr3-800t-runtime.mjs';
const defaultFilms=['ektar100','gold200','pro400h','portra400','vision3-250d'];
const modes=['vivid','retro','hdr','cross','bleach'];
export function prepare800T(official,selection) {
  const configuration=normalize800T(selection);
  const evidence=inspect800TEvidence(official);
  const film=create800TFilm();const ids=[...defaultFilms];ids[modes.indexOf(configuration.slot)]=film.id;
  const color_plan=createFilmPlan(ids,[film]);
  if (color_plan.custom.find((row)=>row.name==='800T')?.mode!==configuration.slot)
    throw new Error('800T slot allocation differs from the requested slot');
  const configuration_sha256=createHash('sha256').update(JSON.stringify({
    schema:'m10v-gr3-800t-plan/v1',source:evidence.sourceSha256,configuration,color_plan,
    implementation:'native-halation/v6-dedicated-camera-controls',provenance:film.provenance,
    sources:['native/gr3/halation_core.c','native/gr3/halation_core.h','native/gr3/halation_camera.c',
      'native/gr3/menu_controls.c','native/gr3/halation_controls.h','scripts/build_gr3_menu_controls.py','scripts/build_gr3_menu_patches.py',
      'node/gr3-800t-worker.py','scripts/build_gr3_halation.py','scripts/build_gr3_camera_adapter.py',
      'node/gr3-800t-contract.json','node/gr3-800t-hooks.json','node/gr3-800t-controls.json','native/gr3/800t-code-lock.json',
      'node/gr3-800t-expected.mjs','node/gr3-800t-audit.mjs'].map(name=>[name,createHash('sha256')
        .update(readFileSync(new URL('../'+name,import.meta.url))).digest('hex')]),
  })).digest('hex');
  return {schema:'m10v-gr3-800t-preparation/v1',ready:evidence.firmwareReady,configuration,configuration_sha256,
    source_sha256:evidence.sourceSha256,color_plan,color_provenance:film.provenance,
    kernel:{implementation:'native C + ARM',layout:'semiplanar_CbCr422_unsigned128',camera_layout_proved:true},
    blockers:evidence.unresolved,evidence,camera_tested:false,physical_validation_required:true,
    dng_preview_may_share_jpeg_effect:true,filename:'fwdc239b.bin'};
}
export async function build800T(official,selection,acceptedConfigurationSha256) {
  const prepared=prepare800T(official,selection);
  if (!prepared.ready) {
    const error=new Error(`800T 暂不能生成刷机包：${prepared.blockers.map((row)=>row.message).join('；')}`);
    error.code='M10V_800T_EVIDENCE_REQUIRED';error.blockers=prepared.blockers;throw error;
  }
  if (acceptedConfigurationSha256!==prepared.configuration_sha256) throw new Error('800T 方案已变化，请重新预检');
  return run800TBuild(official,prepared);
}

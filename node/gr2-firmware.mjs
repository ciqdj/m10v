// Compatibility exports for the GR II 3.00 inspector.
import {unityProfiles} from './unity-model-profiles.mjs';
import {inspectUnityModel,readUnityModelComponent} from './unity-firmware.mjs';
export {xorUnityPayload,decodeUnity} from './unity-firmware.mjs';
export const GR2_SHA256=unityProfiles.gr2.sha256;
export const GR2_SIZE=unityProfiles.gr2.size;
export const inspectGr2=data=>inspectUnityModel(data,'gr2');
export const readGr2Component=(data,name)=>readUnityModelComponent(data,'gr2',name);

import {unityProfiles} from './unity-model-profiles.mjs';
import {inspectUnityModel,readUnityModelComponent} from './unity-firmware.mjs';
export const GR1_SHA256=unityProfiles.gr1.sha256;
export const GR1_SIZE=unityProfiles.gr1.size;
export const inspectGr1=data=>inspectUnityModel(data,'gr1');
export const readGr1Component=(data,name)=>readUnityModelComponent(data,'gr1',name);

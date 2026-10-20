// One catalogue and one five-slot contract for simulation and in-camera library.
export const defaultEffects=()=>({grainSize:1,leakGain:0,leakPosition:0,leakSpread:4,leakVariation:0,filmExposure:0});
export const defaultHalo=()=>({gain:3,spread:3,threshold:5,profile:2});
export const defaultConfiguration=()=>({slots:Array.from({length:5},(_,i)=>({film:i===4?33:34+i,grain:0,soft:0,halo:defaultHalo(),effects:defaultEffects()})),stamp:0,format:0,corner:0,color:0,filmNameStamp:false,hdf:0});
export function normalizeConfiguration(value=defaultConfiguration()){
 const exact=(obj,keys)=>obj&&typeof obj==='object'&&!Array.isArray(obj)&&Object.keys(obj).sort().join('|')===[...keys].sort().join('|');
 const int=(n,min,max)=>Number.isInteger(n)&&n>=min&&n<=max;
 if(!(exact(value,['slots','stamp','format','corner','color'])||exact(value,['slots','stamp','format','corner','color','hdf'])||exact(value,['slots','stamp','format','corner','color','filmNameStamp'])||exact(value,['slots','stamp','format','corner','color','filmNameStamp','hdf']))||!Array.isArray(value.slots)||value.slots.length!==5)throw Error('需要完整的五槽配置');
 const hdf=value.hdf===undefined?0:value.hdf;if(!int(hdf,0,3))throw Error('HDF 模拟档位无效');
 const slots=value.slots.map(s=>{
  if(!(exact(s,['film','grain','soft','halo'])||exact(s,['film','grain','soft'])||exact(s,['film','grain','soft','halo','effects']))||!int(s.film,1,72)||!int(s.grain,0,3)||!int(s.soft,0,3))throw Error('胶卷或质感档位无效');
  const h=s.halo??defaultHalo();if(!exact(h,['gain','spread','threshold','profile'])||!int(h.gain,0,8)||!int(h.spread,0,8)||!int(h.threshold,0,8)||!int(h.profile,0,3))throw Error('胶卷光晕参数无效');
  const inputEffects=s.effects??defaultEffects(),oldKeys=['grainSize','leakGain','leakPosition','leakSpread','leakVariation'];
  if(!(exact(inputEffects,oldKeys)||exact(inputEffects,[...oldKeys,'filmExposure'])))throw Error('胶卷质感参数无效');
  const e={...inputEffects,filmExposure:exact(inputEffects,oldKeys)?0:inputEffects.filmExposure};if(!int(e.filmExposure,0,2)||(s.film!==68&&e.filmExposure!==0)||!int(e.grainSize,0,2)||!int(e.leakGain,0,8)||!int(e.leakPosition,0,5)||!int(e.leakSpread,0,8)||!int(e.leakVariation,0,1))throw Error('胶卷质感参数无效');
  return {film:s.film,grain:s.grain,soft:0,halo:{gain:h.profile===0?0:h.gain,spread:h.spread,threshold:h.threshold,profile:h.profile},effects:{...e}};
 });
 if(!int(value.stamp,0,2)||!int(value.format,0,3)||!int(value.corner,0,3)||!int(value.color,0,3)||(value.filmNameStamp!==undefined&&typeof value.filmNameStamp!=='boolean'))throw Error('时间戳配置无效');
 return {slots,stamp:value.stamp,format:value.format,corner:value.corner,color:value.color,filmNameStamp:value.filmNameStamp??false,hdf};
}
export function migrateSimulationSelection(ids,texture,catalog,current=defaultConfiguration()){
 const configuration=normalizeConfiguration(current),unresolved=[];
 ids.slice(0,5).forEach((id,index)=>{
  const entry=catalog.find(f=>f.legacy_id===id);
  if(!entry){unresolved.push({slot:index,id});return;}
  configuration.slots[index].film=entry.id;
  if(entry.id!==68)configuration.slots[index].effects.filmExposure=0;
  configuration.slots[index].grain=texture?.[id]?.grain??0;
  configuration.slots[index].soft=0;
 });
 return {configuration:normalizeConfiguration(configuration),unresolved};
}

// Optional camera features share the native export; no implicit draft conversion.
export const rawNrThresholds=[400,800,1600,3200,5000,6400,8000,10000,12800];
export function normalizeRawNr(value={mode:'stock'}){
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!['mode','iso'].includes(k))||!['stock','off','threshold'].includes(value.mode)||
  (value.mode==='threshold'?!rawNrThresholds.includes(value.iso):value.iso!==undefined))throw Error('RAW 降噪配置或 ISO 阈值无效');
 return value.mode==='threshold'?{mode:value.mode,iso:value.iso}:{mode:value.mode};
}
export const defaultExtensions=()=>({aspect:false,level:false,negativeGrain:false,rawNr:{mode:'stock'}});
export function normalizeExtensions(value=defaultExtensions()){
 const keys=['aspect','level','negativeGrain'];
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>![...keys,'rawNr'].includes(k))||keys.some(k=>typeof value[k]!=='boolean'))throw Error('附加功能配置必须包含画幅、水平仪和负片颗粒开关');
 return {aspect:value.aspect,level:value.level,negativeGrain:value.negativeGrain,rawNr:normalizeRawNr(value.rawNr)};
}
export function activeExtensions(value){
 const e=normalizeExtensions(value);return ['aspect','level','negativeGrain'].filter(k=>e[k]).concat(e.rawNr.mode==='stock'?[]:['rawNr']);
}
export function withNativeLibrary(features){
 const allowed=['film','digitalHdf','timestamp','aspect','level','negativeGrain','rawNr'];
 if(!Array.isArray(features)||features.some(id=>!allowed.includes(id)))throw Error('胶卷库可组合时间戳、画幅、水平仪、负片颗粒和 RAW 降噪；请先移除其他配方或工具');
 const selected=new Set(['film',...features]);return allowed.filter(id=>selected.has(id));
}

export function nativeSelection(features,configuration,model){
 const compatible=features;
 return {features:withNativeLibrary(compatible),configuration:{...configuration,stamp:compatible.includes('timestamp')?(configuration.stamp||1):0,filmNameStamp:compatible.includes('timestamp')?(configuration.filmNameStamp??false):false}};
}

export function selectNativeFilm(value,slot,film){
 const c=normalizeConfiguration(value);if(!Number.isInteger(slot)||slot<0||slot>4)throw Error('槽位无效');
 const s=c.slots[slot];if(s.film!==film&&film===66){s.grain=1;s.soft=0;s.halo={gain:0,spread:3,threshold:5,profile:1};s.effects=defaultEffects();}
 if(s.film!==film&&film===67){s.grain=1;s.soft=0;s.halo={gain:2,spread:3,threshold:5,profile:2};s.effects={...defaultEffects(),grainSize:0};}
 if(s.film!==film&&film===68){s.grain=2;s.soft=0;s.halo={gain:0,spread:3,threshold:5,profile:2};s.effects=defaultEffects();}
 if(s.film!==film&&film>=69){s.grain=film===72?0:film===71?2:1;s.soft=0;s.halo={gain:0,spread:3,threshold:5,profile:2};s.effects={...defaultEffects(),grainSize:film===71?1:0};}
 if(film!==68)s.effects.filmExposure=0;
 s.film=film;return normalizeConfiguration(c);
}

export function resetNativeTexture(value,slot){
 const c=normalizeConfiguration(value);if(!Number.isInteger(slot)||slot<0||slot>4)throw Error("槽位无效");
 const s=c.slots[slot];s.grain=s.film===72?0:[68,71].includes(s.film)?2:s.film>=66?1:0;s.soft=0;s.effects={...defaultEffects(),grainSize:[67,69,70,72].includes(s.film)?0:1,filmExposure:s.effects.filmExposure};return c;
}

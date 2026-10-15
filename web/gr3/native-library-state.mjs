// One catalogue and one five-slot contract for simulation and in-camera library.
export const defaultHalo=()=>({gain:3,spread:3,threshold:5,profile:2});
export const defaultConfiguration=()=>({slots:Array.from({length:5},(_,i)=>({film:i===4?33:i+1,grain:0,soft:0,halo:defaultHalo()})),stamp:0,format:0,corner:0,color:0});
export function normalizeConfiguration(value=defaultConfiguration()){
 const exact=(obj,keys)=>obj&&typeof obj==='object'&&!Array.isArray(obj)&&Object.keys(obj).sort().join('|')===[...keys].sort().join('|');
 const int=(n,min,max)=>Number.isInteger(n)&&n>=min&&n<=max;
 if(!exact(value,['slots','stamp','format','corner','color'])||!Array.isArray(value.slots)||value.slots.length!==5)throw Error('需要完整的五槽配置');
 const slots=value.slots.map(s=>{
  if(!(exact(s,['film','grain','soft','halo'])||exact(s,['film','grain','soft']))||!int(s.film,1,65)||!int(s.grain,0,3)||!int(s.soft,0,3))throw Error('胶卷或质感档位无效');
  const h=s.halo??defaultHalo();if(!exact(h,['gain','spread','threshold','profile'])||!int(h.gain,0,8)||!int(h.spread,0,8)||!int(h.threshold,0,8)||!int(h.profile,0,3))throw Error('800T 光晕参数无效');
  return {film:s.film,grain:s.grain,soft:s.soft,halo:{gain:h.gain,spread:h.spread,threshold:h.threshold,profile:h.profile}};
 });
 if(!int(value.stamp,0,2)||!int(value.format,0,3)||!int(value.corner,0,3)||!int(value.color,0,3))throw Error('时间戳配置无效');
 return {slots,stamp:value.stamp,format:value.format,corner:value.corner,color:value.color};
}
export function migrateSimulationSelection(ids,texture,catalog,current=defaultConfiguration()){
 const configuration=normalizeConfiguration(current),unresolved=[];
 ids.slice(0,5).forEach((id,index)=>{
  const entry=catalog.find(f=>f.legacy_id===id);
  if(!entry){unresolved.push({slot:index,id});return;}
  configuration.slots[index].film=entry.id;
  configuration.slots[index].grain=texture?.[id]?.grain??0;
  configuration.slots[index].soft=texture?.[id]?.hdf??0;
 });
 return {configuration:normalizeConfiguration(configuration),unresolved};
}

// Optional camera features share the native export; no implicit draft conversion.
export const defaultExtensions=()=>({aspect:false,level:false,negativeGrain:false});
export function normalizeExtensions(value=defaultExtensions()){
 const keys=['aspect','level','negativeGrain'];
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join('|')!==keys.sort().join('|')||keys.some(k=>typeof value[k]!=='boolean'))throw Error('附加功能配置必须包含画幅、水平仪和负片颗粒开关');
 return {aspect:value.aspect,level:value.level,negativeGrain:value.negativeGrain};
}
export function withNativeLibrary(features){
 const allowed=['film','timestamp','aspect','level','negativeGrain'];
 if(!Array.isArray(features)||features.some(id=>!allowed.includes(id)))throw Error('胶卷库可组合时间戳、画幅、水平仪和负片颗粒；请先移除其他配方或工具');
 const selected=new Set(['film',...features]);return allowed.filter(id=>selected.has(id));
}

export function nativeSelection(features,configuration,model){
 const compatible=model==='gr3x'?features.filter(id=>['film','timestamp'].includes(id)):features;
 return {features:withNativeLibrary(compatible),configuration:{...configuration,stamp:compatible.includes('timestamp')?(configuration.stamp||1):0}};
}

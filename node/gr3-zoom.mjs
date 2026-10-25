// Independent GR III focal hook/readback contract.
const need=(ok,message)=>{if(!ok)throw Error('custom focal: '+message);};
const branch=(a,b,link=false)=>{
 const d=b-a-8;need(Number.isInteger(b)&&d%4===0&&d>=-(2**25)&&d<2**25,'branch range');
 return ((link?0xeb000000:0xea000000)|((d>>2)&0xffffff))>>>0;
};
export function zoomPatches(runtime,m){
 if(!m.sd_library||m.film_library_enabled===false)return [];
 const z=m.zoom;
 need(typeof z?.enabled==='boolean','explicit enabled contract missing');
 if(!z.enabled)return [];
 need(z?.schema==='m10v-gr3-zoom/v1'&&z.slots===2&&z.min_mm===28&&z.max_mm===50,'module contract missing');
 need(z.title_id===1024&&z.focal_first_id===1031,'resource allocation differs');
 need(z.aspect===(m.base>=0x540be000),'aspect fallback contract differs');
 need(Number.isInteger(z.base)&&Number.isInteger(z.bytes)&&z.bytes>0&&z.base>=m.base&&z.base+z.bytes<=m.base+runtime.length,'module bounds');
 const seed=z.seed;
 need(seed===null||(typeof seed?.id==='string'&&/^[0-9a-f]{16}$/.test(seed.id)&&seed.id!=='0000000000000000'&&Array.isArray(seed.slots)&&seed.slots.length===2&&seed.slots.every(mm=>Number.isInteger(mm)&&mm>=28&&mm<=50)),'invalid seed');
 const lo=seed?parseInt(seed.id.slice(0,8),16):0,hi=seed?parseInt(seed.id.slice(8),16):0;
 const at=z.seed_parameters-m.base;
 need(Number.isInteger(at)&&at>=0&&at+24<=runtime.length,'seed parameter bounds');
 [0x31575a4d,lo,hi,~(0x31575a4d^lo^hi)>>>0,...(seed?seed.slots:[35,50])].forEach((n,i)=>need(runtime.readUInt32LE(at+i*4)===(n>>>0),'seed parameter readback differs'));
 need(z.debug_trace===m.debug_mode,'trace mode differs');
 const inventory=[...hooks,...(z.debug_trace?[[0x536b93d0,0xe1a0c00d,'m10v_zoom_assert_trace',false]]:[])];
 const patches=inventory.map(([address,expected,name,link])=>{
  const target=m.symbols[name];
  need(z.symbols[name]===target&&target>=z.base&&target<z.base+z.bytes,'hook outside module');
  return {address,expected,replacement:branch(address,target,link),name};
 });
 need(z.patches.length===patches.length&&patches.every((p,i)=>['address','expected','replacement'].every(k=>p[k]===z.patches[i][k])),'hook inventory differs');
 need(m.resources.texts[238]==='裁切焦距','editor title missing');
 for(let mm=28;mm<=100;mm++)need(m.resources.texts[245+mm-28]===mm+'mm','numeric focal caption differs');
 return patches;
}
export const zoomSources=["native/gr3/m10v_zoom_icon.c","native/gr3/m10v_zoom.c", "native/gr3/m10v_zoom_camera.c", "native/gr3/m10v_zoom_menu.c", "native/gr3/m10v_zoom_live.c", "native/gr3/m10v_zoom_live.S", "native/gr3/m10v_zoom_capture.c", "native/gr3/m10v_zoom_capture_adapters.c", "native/gr3/m10v_zoom_capture_hooks.S", "native/gr3/m10v_zoom.h", "native/gr3/m10v_zoom_camera.h", "native/gr3/m10v_zoom_menu.h", "native/gr3/m10v_zoom_capture.h", "scripts/build_gr3_zoom.py", "node/gr3-zoom.mjs"];
const hooks=[[0x5320a7b8,0xe24dd06c,"m10v_zoom_icon_draw_frame",false],[0x5320a9b4,0xe51b2030,"m10v_zoom_icon_draw_done",false],[0x5324526c,0xe5903004,"m10v_zoom_guard_front",false],[0x5354a7bc,0xe30f3020,"m10v_zoom_guard_back",false],[1394306032, 3785408525, "m10v_zoom_set", false], [1394216456, 3785408525, "m10v_zoom_set", false], [1394311972, 3809030612, "m10v_zoom_selected", false], [1394217552, 3785408525, "m10v_zoom_selected", false], [1394766264, 3785408525, "m10v_zoom_cycle", false], [1394178308, 3942927191, "m10v_zoom_label_live", true], [1394298456, 3942897154, "m10v_zoom_label_menu", true], [1394226344, 3942915182, "m10v_zoom_label_adj", true], [1399466544, 3990846200, "m10v_zoom_capture_resolution_hook", false], [1398819608, 3851431964, "m10v_zoom_capture_marker_write", false], [1398534140, 3785408525, "m10v_zoom_capture_marker_read", false], [1398548380, 3785408525, "m10v_zoom_capture_marker_summary", false], [1395144448, 3785408525, "m10v_zoom_capture_raw_count", false], [1395144588, 3785408525, "m10v_zoom_capture_raw_value", false], [1395303600, 3785408525, "m10v_zoom_capture_icon_hook", false], [1395304040, 3785408525, "m10v_zoom_capture_caption_hook", false], [1398728848, 3785408525, "m10v_zoom_capture_replay_rect", false]];

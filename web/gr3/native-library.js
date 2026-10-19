import {normalizeVersionUnlock,assertVersionUnlockReceipt} from './version-unlock-state.mjs';
import {enhanceFilmSelect} from './film-picker.mjs';
import {defaultConfiguration,normalizeConfiguration,selectNativeFilm,resetNativeTexture} from './native-library-state.mjs';
export function mountNativeLibrary(root=document,{model='gr3',onChange=()=>{},onEditStart=()=>{},onEditCommit=()=>{}}={}) {
const catalogApi=model==='gr4'?'/api/gr4/native-library/catalog':'/api/gr3/native-library/catalog';
const storageKey=model==='gr4'?'m10v-gr4-native-library-v1':'m10v-native-library-v1';
const $=s=>root.querySelector(s),levels=['关闭','弱','中','强'];
let configuration=defaultConfiguration(),active=0,films=[],project=null,token='',busy=false,abort=null,urls=[],unresolved=[],sourceModel=model;
try{const saved=localStorage.getItem(storageKey);if(saved)configuration=normalizeConfiguration(JSON.parse(saved));}catch{}
// Retired M10V sketches migrate by slot; their numeric IDs remain firmware-compatible.
configuration.slots.forEach((s,i)=>{if(s.film<33)s.film=[34,35,36,37,33][i];});
const message=(text,error=false)=>{$('#progress').textContent=text;$('#progress').dataset.error=String(error);};
function invalidate(meta={}){onChange(normalizeConfiguration(configuration),meta);for(const u of urls)URL.revokeObjectURL(u);urls=[];$('#downloads').hidden=true;message('');try{localStorage.setItem(storageKey,JSON.stringify(configuration));}catch{}}
function versionUnlockSnapshot(){
 if(sourceModel!=='gr3x')return normalizeVersionUnlock({enabled:false},sourceModel);
 const enabled=$('#native-version-unlock').checked;
 const option=$('#native-version-known').checked?{enabled,dsp:$('#native-version-dsp').value,cpu:$('#native-version-cpu').value}:{enabled,mode:'dsp-package-only'};
 return normalizeVersionUnlock(option,sourceModel);
}
function renderVersionUnlock(){
 if($('#native-bridge-guide'))$('#native-bridge-guide').hidden=sourceModel!=='gr3';
 const supported=sourceModel==='gr3x',toggle=$('#native-version-unlock'),known=$('#native-version-known');
 $('#native-version-unlock-option').hidden=!supported;if(!supported){toggle.checked=false;known.checked=false;}
 toggle.disabled=busy||!supported;$('#native-version-unlock-fields').hidden=!toggle.checked;
 known.disabled=busy||!supported||!toggle.checked;
 const advanced=supported&&toggle.checked&&known.checked;$('#native-version-known-fields').hidden=!advanced;
 for(const key of ['dsp','cpu']){$('#native-version-'+key).disabled=busy||!advanced;$('#native-version-'+key).required=advanced;$('#native-version-'+key).placeholder=(sourceModel==='gr3x'?'1.60':'2.10')+'.x.x';}
 let error='';try{versionUnlockSnapshot();}catch(e){error=e.message;}
 $('#native-version-error').textContent=error;return !error;
}
function segment(selector,labels,value,change){const node=$(selector);node.replaceChildren(...labels.map((text,i)=>{const b=document.createElement('button');b.type='button';b.dataset.focus=selector.slice(1)+'-'+i;b.textContent=text;b.setAttribute('aria-pressed',String(i===value));b.disabled=busy;b.onclick=()=>{change(i);invalidate();render();};return b;}));}
function render(){
 const focused=document.activeElement?.dataset?.focus;
 const slotNode=$('#slots');slotNode.replaceChildren(...configuration.slots.map((s,i)=>{const b=document.createElement('button');b.type='button';b.dataset.focus='slot-'+i;b.className='slot';b.disabled=busy;b.setAttribute('aria-pressed',String(i===active));const n=document.createElement('small');n.textContent=`槽位 ${i+1}`;const t=document.createElement('strong');t.textContent=unresolved.find(v=>v.slot===i)?'需重选 · '+unresolved.find(v=>v.slot===i).id:films.find(f=>f.id===s.film)?.name||'载入中';const e=document.createElement('em');e.textContent=`颗粒 ${levels[s.grain]} · 漏光 ${s.effects.leakGain||"关"}`;const art=filmIcon(films.find(f=>f.id===s.film));b.append(n,art,t,e);b.onclick=()=>{active=i;const status=$('#film-selection-status');if(status)status.textContent='';render();};return b;}));
 segment('#grain',levels,configuration.slots[active].grain,v=>configuration.slots[active].grain=v);

 const film=configuration.slots[active].film;
 const label=$('#active-slot-label');if(label)label.textContent=`槽位 ${active+1} · ${films.find(f=>f.id===film)?.name||'载入中'}`;
 $('#halo-controls').hidden=![33,67].includes(film);
 $('#red-controls').hidden=film!==68;
 $('#halo-controls .label').textContent=(film===67?'蓝凤凰':'800T')+' 光晕 · 当前槽位';
 const effects=configuration.slots[active].effects;
 for(const k of ['grainSize','leakGain','leakPosition','leakSpread','leakVariation','filmExposure']){$('#effect-'+k).value=String(effects[k]);$('#effect-'+k).disabled=busy||(k==='filmExposure'&&film!==68);}
 $('#reset-texture').disabled=busy;
 const halo=configuration.slots[active].halo;
 for(const k of ['gain','spread','threshold']){$('#halo-'+k).value=String(halo[k]);$('#halo-'+k+'-value').textContent=halo[k]+'/8';$('#halo-'+k).disabled=busy;}
 segment('#stamp',['关闭','日期','日期 + 时间'],configuration.stamp,v=>configuration.stamp=v);
 for(const k of ['format','corner','color']){$('#'+k).value=String(configuration[k]);$('#'+k).disabled=busy||!configuration.stamp;}
 $('#native-debug-mode').disabled=busy;
 const unlockValid=renderVersionUnlock();
 renderFilms();$('#build').disabled=busy||!project||!unlockValid;$('#local-source').disabled=busy||!$('#local-source').dataset.available;$('#official-file').disabled=busy;$('#search').disabled=busy;
 if(focused)root.querySelector(`[data-focus="${focused}"]`)?.focus({preventScroll:true});
}
function filmIcon(f){const img=document.createElement('img');img.className='film-icon';img.width=40;img.height=40;img.alt='';img.decoding='async';if(f?.icon_url)img.src=f.icon_url;else img.hidden=true;return img;}
function renderFilms(){const q=$('#search').value.toLowerCase().trim(),selected=configuration.slots[active].film;let count=0;
 $('#catalog').replaceChildren(...films.filter(f=>f.name.toLowerCase().includes(q)&&(!$('#film-group').value||f.group===$('#film-group').value)).map(f=>{count++;const b=document.createElement('button');b.type='button';b.dataset.focus='film-'+f.id;b.className='film';b.disabled=busy;b.setAttribute('aria-pressed',String(f.id===selected));b.setAttribute('aria-label',`装入 ${f.name} 到槽位 ${active+1}`);const strong=document.createElement('strong');strong.textContent=f.name;b.append(filmIcon(f),strong);if(f.id===selected){const check=document.createElement('span');check.className='check';check.textContent='✓';b.append(check);}b.onclick=()=>{configuration=selectNativeFilm(configuration,active,f.id);invalidate({filmSlot:active});render();const status=$('#film-selection-status');if(status)status.textContent=`已将 ${f.name} 装入槽位 ${active+1}，参数仅作用于此槽位。`;};return b;}));$('#empty').hidden=count!==0;
}
async function jsonResponse(r){const data=await r.json();if(!r.ok)throw Error(data.error||`请求失败 ${r.status}`);return data;}
function post(url,value,signal){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-M10V-Token':token},body:JSON.stringify(value),signal});}
function setBusy(value){busy=value;$('#cancel').hidden=!value||!abort;render();}
async function importSource(file){setBusy(true);message('正在核对官方固件…');try{const result=file?await jsonResponse(await fetch('/api/import',{method:'POST',headers:{'X-M10V-Token':token},body:file})):await jsonResponse(await post('/api/gr3/native-library/import-official',{}));project=result.project_id;sourceModel=result.model==='GR IIIx'?'gr3x':'gr3';$('#source-status').textContent=`✓ 官方包已核验 · ${sourceModel==='gr3x'?'GR IIIx 1.60':'GR III 2.10'}`;message('官方包已就绪，可生成实机测试候选。');}catch(e){project=null;$('#source-status').textContent='官方包未通过核验';message(e.message,true);}finally{setBusy(false);}}
for(const k of ['format','corner','color'])$('#'+k).onchange=()=>{configuration[k]=Number($('#'+k).value);invalidate();render();};
for(const k of ['gain','spread','threshold']){$('#halo-'+k).onpointerdown=onEditStart;$('#halo-'+k).onkeydown=onEditStart;$('#halo-'+k).onpointerup=onEditCommit;$('#halo-'+k).onkeyup=onEditCommit;$('#halo-'+k).onchange=onEditCommit;}
for(const k of ['gain','spread','threshold'])$('#halo-'+k).oninput=()=>{configuration.slots[active].halo[k]=Number($('#halo-'+k).value);$('#halo-'+k+'-value').textContent=$('#halo-'+k).value+'/8';invalidate();};
for(const k of ['grainSize','leakGain','leakPosition','leakSpread','leakVariation','filmExposure'])$('#effect-'+k).onchange=()=>{configuration.slots[active].effects[k]=Number($('#effect-'+k).value);invalidate();render();};
$('#reset-texture').onclick=()=>{configuration=resetNativeTexture(configuration,active);invalidate();render();};
$('#film-group').onchange=renderFilms;
$('#search').oninput=renderFilms;$('#local-source').onclick=()=>importSource();$('#official-file').onchange=e=>{const f=e.target.files[0];if(f)importSource(f);e.target.value='';};
$('#cancel').onclick=()=>abort?.abort();
$('#native-debug-mode').onchange=()=>invalidate();
$('#native-version-unlock').onchange=()=>{invalidate();render();};
$('#native-version-known').onchange=()=>{invalidate();render();};
for(const key of ['dsp','cpu'])$('#native-version-'+key).oninput=()=>{invalidate();render();};
$('#build').onclick=async()=>{
 if(busy||!project)return;let version_unlock;try{version_unlock=versionUnlockSnapshot();}catch(e){message(e.message,true);return;}invalidate();abort=new AbortController();setBusy(true);const snapshot=normalizeConfiguration(configuration),debug_mode=$('#native-debug-mode').checked;
 try{message('1 / 3 · 校验五槽配置与官方基线…');const plan=await jsonResponse(await post(`/api/projects/${project}/native-library/prepare`,{configuration:snapshot,debug_mode,version_unlock},abort.signal));
 message('2 / 3 · 编译 ARM 模块、接入机内菜单和 JPEG 路径…');
 const response=await post(`/api/projects/${project}/native-library/build`,{configuration:snapshot,debug_mode,version_unlock,accepted_configuration_sha256:plan.configuration_sha256},abort.signal);
 if(!response.ok){await jsonResponse(response);throw Error('构建失败');}
 message('3 / 3 · 核对下载摘要…');const blob=await response.blob();const encoded=response.headers.get('X-M10V-Native-Receipt');if(!encoded)throw Error('缺少构建校验记录');
 const receipt=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))));
 assertVersionUnlockReceipt(receipt.version_unlock,version_unlock,sourceModel);
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer())),v=>v.toString(16).padStart(2,'0')).join('');
 if(receipt.debug_mode!==debug_mode||digest!==receipt.candidate_sha256||JSON.stringify(receipt.configuration)!==JSON.stringify(snapshot))throw Error('固件摘要或配置回读不一致');
 const binUrl=URL.createObjectURL(blob),recordUrl=URL.createObjectURL(new Blob([JSON.stringify(receipt,null,2)+'\n'],{type:'application/json'}));urls=[binUrl,recordUrl];
 $('#bin-link').href=binUrl;$('#bin-link').download=sourceModel==='gr3x'?'fwdc243b.bin':'fwdc239b.bin';$('#receipt-link').href=recordUrl;$('#receipt-link').download='M10V-build-receipt.json';$('#downloads').hidden=false;
 message(`候选已生成 · ${(blob.size/1024/1024).toFixed(1)} MB · ${receipt.verified_hooks} 处挂钩、${receipt.icon_count} 个图标回读通过。${debug_mode?'调试已开启，复现后请复制 SD 卡根目录的 M10VMN0/1.BIN、M10VCP0/1.BIN。':''}相机结果待验证。`);$('#bin-link').click();
 }catch(e){message(e.name==='AbortError'?'已取消构建；没有导出固件。':e.message,true);}finally{abort=null;setBusy(false);}
};
(async()=>{try{const [status,catalog]=await Promise.all([fetch('/api/status').then(jsonResponse),fetch(catalogApi).then(jsonResponse)]);token=status.session_token;films=catalog.films;for(const group of [...new Set(films.map(f=>f.group))]){const option=document.createElement('option');option.value=group;option.textContent=group;option.dataset.icon=films.find(f=>f.group===group)?.icon_url;$('#film-group').append(option);}enhanceFilmSelect($('#film-group'),{caption:'胶卷分类',searchable:false});$('#local-source').dataset.available=catalog.local_source_available?'1':'';$('#source-status').textContent=catalog.local_source_available?'已找到目录中的官方包，请选择使用。':'请选择对应的官方固件包。';render();}catch(e){message(e.message,true);$('#source-status').textContent='服务暂不可用，请刷新页面。';}})();render();

return {getConfiguration:()=>normalizeConfiguration(configuration),setFilm:(id,slot=active)=>{active=slot;configuration=selectNativeFilm(configuration,slot,id);invalidate({filmSlot:slot});render();},setConfiguration:value=>{configuration=normalizeConfiguration(value);invalidate();render();},setHdf:value=>{configuration=normalizeConfiguration({...configuration,hdf:value});invalidate({globalHdf:true});render();},setUnresolved:value=>{if(JSON.stringify(unresolved)!==JSON.stringify(value)){unresolved=value;render();}}};
}
if(location.pathname.endsWith('/native-library.html'))mountNativeLibrary();

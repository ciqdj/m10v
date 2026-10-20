const $=id=>document.getElementById(id);
let token='',busy=false;
const ready=fetch('/api/status').then(r=>r.json()).then(value=>{token=value.session_token;});
function row(values){const tr=document.createElement('tr');for(const value of values){const td=document.createElement('td');td.textContent=String(value);tr.append(td);}return tr;}
async function inspect(local=false){
  if(busy)return;
  const file=$('firmware').files[0];if(!local&&!file)return;
  busy=true;$('report').hidden=true;$('local').disabled=true;$('firmware').disabled=true;$('notice').textContent='正在校验固件内容…';
  try{
    await ready;
    const response=await fetch(local?'/api/platform/inspect-official':'/api/platform/inspect',{
      method:'POST',headers:{'X-M10V-Token':token},body:local?JSON.stringify({model:'gr2'}):await file.arrayBuffer()});
    const result=await response.json();if(!response.ok)throw new Error(result.error);
    if(result.model!=='GR II')throw new Error(`已识别 ${result.model}，请使用对应机型工作台；当前工作台仅支持 GR II。`);
    $('identity').textContent=`${result.model} · ${result.public_version}`;
    $('hash').textContent=`SHA-256 ${result.sha256}`;
    $('proof').textContent=(result.proof.byte_exact_roundtrip?'官方身份与原样往返检查通过。':'官方固件身份检查通过。')+(result.proof.modified_update_checksum?'更新校验通过（已与原厂 CPU 对照）。':'')+'离线检查不代表实机验收。';
    $('components').replaceChildren(...(result.components||result.sections||[]).map(v=>row([v.name,v.size||v.payload_bytes,v.sha256])));
    $('resources').replaceChildren(...(result.resources||[]).map(v=>row([v.name,'0x'+v.payload_offset.toString(16),v.size])));
    $('resource-count').textContent=`${(result.resources||[]).length} 项资源`;
    $('report').hidden=false;$('notice').textContent='GR II 解析完成。加载链、菜单与成像等原生功能继续逆向中。';
  }catch(error){$('notice').textContent=error.message;}
  finally{busy=false;$('local').disabled=false;$('firmware').disabled=false;}
}
$('local').addEventListener('click',()=>inspect(true));$('firmware').addEventListener('change',()=>inspect());

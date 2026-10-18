const model=location.pathname.startsWith('/gr4')?'gr4':'gr3';
const $=id=>document.getElementById(id);
const selected=new Set();let films=[],token='',busy=false;
function status(text,error=false){$('sd-status').textContent=text;$('sd-status').dataset.error=String(error);}
function update(){
 $('sd-count').textContent=`已选 ${selected.size} / ${films.length} 款 · ${(4096+selected.size*12288)/1024} KiB`;
 $('sd-download').disabled=busy||!selected.size;
 for(const input of document.querySelectorAll('#sd-films input')){input.checked=selected.has(Number(input.value));input.disabled=busy;}
 $('sd-all').disabled=busy||!films.length;$('sd-none').disabled=busy||!films.length;
}
$('sd-all').onclick=()=>{films.forEach(f=>selected.add(f.id));update();};
$('sd-none').onclick=()=>{selected.clear();update();};
$('sd-download').onclick=async()=>{
 busy=true;update();status('正在打包并校验胶卷…');
 try{
  const response=await fetch(model==='gr4'?'/api/gr4/native-library/sd-export':'/api/gr3/sd-library/export',{method:'POST',headers:{'Content-Type':'application/json','X-M10V-Token':token},body:JSON.stringify({model,ids:films.filter(f=>selected.has(f.id)).map(f=>f.id)})});
  if(!response.ok)throw Error((await response.json()).error||'下载失败');
  const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download='M10V-SD-films.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
  status('已生成下载文件。请按下方说明复制到 SD 卡。');
 }catch(e){status(e.message,true);}finally{busy=false;update();}
};
try{
 const responses=await Promise.all([fetch('/api/status'),fetch('/api/'+model+'/native-library/catalog')]);
 if(responses.some(r=>!r.ok))throw Error('胶卷目录读取失败，请刷新重试');
 const [session,catalog]=await Promise.all(responses.map(r=>r.json()));token=session.session_token;films=catalog.films;
 if(!token||!Array.isArray(films)||!films.length)throw Error('胶卷目录不可用');
 const groups=new Map();for(const film of films){selected.add(film.id);const group=film.group||'胶卷';if(!groups.has(group))groups.set(group,[]);groups.get(group).push(film);}
 for(const [name,rows] of groups){
  const section=document.createElement('fieldset'),legend=document.createElement('legend'),grid=document.createElement('div');legend.textContent=`${name} · ${rows.length} 款`;grid.className='sd-grid';section.append(legend,grid);
  for(const f of rows){const label=document.createElement('label'),check=document.createElement('input'),icon=document.createElement('img'),text=document.createElement('span');
   label.className='sd-film';check.type='checkbox';check.value=f.id;check.checked=true;check.onchange=()=>{check.checked?selected.add(f.id):selected.delete(f.id);update();};icon.src=f.icon_url;icon.alt='';icon.width=40;icon.height=40;text.textContent=f.name;label.append(check,icon,text);grid.append(label);}
  $('sd-films').append(section);
 }
 $('sd-films').setAttribute('aria-busy','false');update();status('可全选或多选，不改变固件工作台的五槽配置。');
}catch(e){$('sd-films').setAttribute('aria-busy','false');$('sd-count').textContent='目录暂不可用';status(e.message,true);}

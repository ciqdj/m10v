import {normalizeConfiguration,zoomSummary} from './native-library-state.mjs';

// Shared by the imaging plan and the standalone library editor.
export function renderZoomControls(root,configuration,model,onChange,busy=false){
 if(!root)return;
 root.hidden=model!=='gr3';root.replaceChildren();if(root.hidden)return;
 const doc=root.ownerDocument,make=(tag,text)=>{const n=doc.createElement(tag);if(text)n.textContent=text;return n;};
 const heading=make('h3','裁切焦距 · 两档');
 const label=make('label'),toggle=make('input');toggle.type='checkbox';toggle.checked=configuration.zoom.write;toggle.disabled=busy;
 toggle.setAttribute('aria-label','下次固件更新写入裁切焦距');
 label.append(toggle,' 下次固件更新写入这两档焦距');
 toggle.onchange=()=>onChange(normalizeConfiguration({...configuration,zoom:{...configuration.zoom,write:toggle.checked}}));
 const fields=make('div');fields.className='stamp-fields';
 configuration.zoom.slots.forEach((mm,index)=>{
  const field=make('label',`第 ${index+1} 档（mm）`),input=make('input');input.type='number';input.min='28';input.max='100';input.step='1';input.value=String(mm);input.required=true;input.disabled=busy||!configuration.zoom.write;
  input.setAttribute('aria-label',`裁切焦距第 ${index+1} 档（mm）`);
  input.oninput=()=>input.setCustomValidity('');
  input.onchange=()=>{
   const value=Number(input.value);
   if(input.value.trim()===''||!Number.isInteger(value)||value<28||value>100){input.setCustomValidity('请输入 28–100 的整数焦距');input.reportValidity();return;}
   input.setCustomValidity('');const slots=[...configuration.zoom.slots];slots[index]=value;
   onChange(normalizeConfiguration({...configuration,zoom:{...configuration.zoom,slots}}));
  };
  field.append(input);fields.append(field);
 });
 const hint=make('p','默认不写入，保留机内设置。勾选后，下次安装此固件时写入一次；之后在机内的修改会保留。两档均可按 1 mm 调整，不能增加或删除。');hint.className='hint';
 const summary=make('p',zoomSummary(configuration));summary.className='hint';summary.setAttribute('aria-live','polite');
 root.append(heading,label,fields,hint,summary);
}

export function validateZoomControls(root){
 const invalid=root?.querySelector('input:invalid');
 if(invalid){invalid.reportValidity();throw Error('请输入 28–100 的整数裁切焦距');}
}

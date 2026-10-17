// A fresh opt-in for each page session; device versions are never guessed.
export function normalizeVersionUnlock(input={enabled:false},model='gr3') {
 if(!input||typeof input.enabled!=='boolean')throw Error('请选择是否突破版本锁');
 if(!input.enabled)return Object.freeze({enabled:false});
 if(!['gr3','gr3x'].includes(model))throw Error('版本适配机型无效');
 const line=model==='gr3x'?[1,60]:[2,10];
 if(input.mode==='dsp-package-only')return Object.freeze({enabled:true,mode:'dsp-package-only'});
 if(input.mode!==undefined)throw Error('版本适配模式无效');
 const version=(value,label)=>{
  if(typeof value!=='string'||!/^\d{1,3}(\.\d{1,3}){3}$/.test(value))throw Error(`${label} 需填写完整四段版本号`);
  const parts=value.split('.').map(Number);
  if(parts.some(n=>n>255)||parts[0]!==line[0]||parts[1]!==line[1])throw Error(`${label} 每段须为0–255整数，且必须属于${line.join('.')}版本线`);
  return parts.join('.');
 };
 return Object.freeze({enabled:true,dsp:version(input.dsp,'DSP'),cpu:version(input.cpu,'CPU')});
}
export function assertVersionUnlockReceipt(receipt,snapshot,model='gr3') {
 const expected=normalizeVersionUnlock(snapshot,model);
 if(!receipt||receipt.enabled!==expected.enabled)throw Error('版本锁设置回读不一致');
 if(!expected.enabled)return;
 if(expected.mode==='dsp-package-only'){
  if(receipt.mode!==expected.mode)throw Error('DSP包头适配模式回读不一致');
  if(receipt.checks?.cpu_payload_unchanged!==true)throw Error('CPU载荷保持不变的回读校验缺失');
  return;
 }
 if(receipt.mode!=='observed-versions')throw Error('已知版本适配模式回读不一致');
 const current=receipt.current_versions;
 if(!current||current.dsp!==expected.dsp||current.cpu!==expected.cpu)throw Error('DSP / CPU 版本回读与本次输入不一致');
}

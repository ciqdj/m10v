import {readFileSync,existsSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const statuses=new Set(['researching','verified_offline','hardware_verified','proven_unavailable']);
const need=(ok,reason)=>{if(!ok)throw Error(reason);};
export function checkParity(ledger,{complete=false}={}){
  need(ledger?.schema==='m10v-unity-parity/v1','invalid parity schema');
  const required=ledger.baseline?.required_ids;
  need(Array.isArray(required)&&required.length>0&&new Set(required).size===required.length,'invalid baseline IDs');
  need(Array.isArray(ledger.features),'invalid feature rows');
  const ids=ledger.features.map(f=>f.id);
  need(new Set(ids).size===ids.length,'duplicate feature IDs');
  need(required.every(id=>ids.includes(id)),'missing baseline feature');
  need(ids.every(id=>required.includes(id)),'unknown baseline feature');
  const summary={features:ids.length,researching:0,verified_offline:0,hardware_verified:0,proven_unavailable:0};
  function files(values,label,nonempty=false){
    need(Array.isArray(values)&&(!nonempty||values.length>0),`missing ${label}`);
    for(const value of values){
      need(typeof value==='string'&&value.length>0&&!path.isAbsolute(value)&&!value.split(/[\\/]/).includes('..'),`invalid ${label} path`);
      need(existsSync(path.join(root,value)),`missing ${label} file: ${value}`);
    }
  }
  for(const feature of ledger.features){
    files(feature.baseline_files,'baseline',true);
    for(const model of ['gr1','gr2']){
      const state=feature.models?.[model];
      need(state&&statuses.has(state.status),`invalid ${model}/${feature.id} status`);
      summary[state.status]++;
      files(state.implementation_files,'implementation',['verified_offline','hardware_verified'].includes(state.status));
      files(state.evidence_files,'evidence',state.status!=='researching');
      need(Array.isArray(state.automated_checks)&&state.automated_checks.every(x=>typeof x==='string'&&x.trim()),'invalid automated checks');
      need(Array.isArray(state.browser_evidence),'invalid browser evidence');
      if(['verified_offline','hardware_verified'].includes(state.status))need(state.automated_checks.length>0,'missing automated checks');
      need(['pending','passed','not_applicable'].includes(state.hardware_status),'invalid hardware status');
      if(state.status==='hardware_verified')need(state.hardware_status==='passed','missing hardware acceptance');
      if(state.status==='proven_unavailable')need(typeof state.limitation==='string'&&state.limitation.trim().length>0,'missing limitation evidence');
      if(complete)need(state.status==='proven_unavailable'||state.status==='hardware_verified',`incomplete: ${model}/${feature.id} (${state.status})`);
    }
  }
  return summary;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{
    const ledger=JSON.parse(readFileSync(path.join(root,'docs/testing/gr1-gr2-parity.json'),'utf8'));
    console.log(JSON.stringify(checkParity(ledger,{complete:process.argv.includes('--complete')})));
  }catch(error){console.error(error.message);process.exitCode=1;}
}

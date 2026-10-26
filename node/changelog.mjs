import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const labels={current:'最新更新',deployment:'已发布',documented:'历史更新',source:'早期记录'};
const sectionLabels={added:'新增',fixed:'修复',improved:'优化'};
export function validateChangelog(data){
 need(data?.schema==='m10v-changelog/v1'&&Array.isArray(data.releases)&&data.releases.length>0,'更新日志格式无效');
 const versions=new Set();let previous='9999-99-99';
 data.releases.forEach((r,i)=>{
  need(/^\d{4}\.\d{2}\.\d{2}\.\d+$/.test(r.version)&&!versions.has(r.version),'更新日志版本重复或无效');versions.add(r.version);
  need(/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&Number.isFinite(Date.parse(r.date))&&new Date(r.date).toISOString().slice(0,10)===r.date&&r.date<=previous,'更新日志日期无效或未倒序');previous=r.date;
  need(typeof r.title==='string'&&r.title.trim()&&Array.isArray(r.changes)&&r.changes.length>0&&r.changes.every(v=>typeof v==='string'&&v.trim()),'更新日志缺少标题或改动');
  if(r.sections!==undefined){
   const types=new Set();
   need(Array.isArray(r.sections)&&r.sections.length>0,'更新日志分组无效');
   for(const section of r.sections){
    need(section&&Object.hasOwn(sectionLabels,section.type)&&!types.has(section.type),'更新日志分类无效或重复');types.add(section.type);
    need(Array.isArray(section.items)&&section.items.length>0&&section.items.every(v=>typeof v==='string'&&v.trim()),'更新日志分类缺少内容');
   }
   need(JSON.stringify(r.sections.flatMap(s=>s.items))===JSON.stringify(r.changes),'更新日志分组与改动不一致');
  }
  need(r.notice===undefined||(typeof r.notice==='string'&&r.notice.trim()),'更新日志提示无效');
  need(Object.hasOwn(labels,r.evidence)&&(i===0?r.evidence==='current':r.evidence!=='current'),'更新日志证据类型无效');
  need(i===0?r.commit===null:/^[a-f0-9]{40}$/.test(r.commit),'历史更新缺少完整提交');
  need(i===0?r.evidence_url===null:typeof r.evidence_url==='string'&&/^https:\/\/github\.com\/zhaoo\/m10v\/(?:actions\/runs\/\d+|commit\/[a-f0-9]{40}|blob\/[a-f0-9]{40}\/[a-zA-Z0-9_./-]+)$/.test(r.evidence_url),'更新日志证据链接无效');
 });return data;
}
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function renderReleases(data){
 validateChangelog(data);
 const list=items=>`<ul>${items.map(v=>`<li>${escape(v)}</li>`).join('')}</ul>`;
 return data.releases.map(r=>{
  const content=r.sections?r.sections.map(s=>`<section class="release-group"><h3>${sectionLabels[s.type]}</h3>${list(s.items)}</section>`).join(''):list(r.changes);
  return `<article class="release" id="release-${r.version}"><div class="release-meta"><time datetime="${r.date}">${r.date}</time><span class="release-version">${r.version}</span><span class="release-evidence">${labels[r.evidence]}</span></div><div class="release-body"><h2>${escape(r.title)}</h2>${content}${r.notice?`<p class="release-notice">${escape(r.notice)}</p>`:''}</div></article>`;
 }).join('\n');
}
export function readChangelog(){return validateChangelog(JSON.parse(readFileSync(new URL('../web/changelog.json',import.meta.url),'utf8')));}
export function renderChangelog(){return readFileSync(new URL('../web/changelog.html',import.meta.url),'utf8').replace('<!-- RELEASES -->',renderReleases(readChangelog()));}
export function checkReleaseChangelog(repo,base){
 need(/^[a-f0-9]{40}$/.test(base),'release base must be a full commit SHA');
 const git=(...args)=>execFileSync('git',args,{cwd:repo,encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
 git('cat-file','-e',base+'^{commit}');
 const changed=git('diff','--name-only',base,'--','web/changelog.json');
 need(changed.split('\n').includes('web/changelog.json'),'本次发布必须更新 web/changelog.json');
 const next=validateChangelog(JSON.parse(readFileSync(path.join(repo,'web/changelog.json'),'utf8')));
 let old;
 try{old=JSON.parse(git('show',base+':web/changelog.json'));}catch(error){if(git('ls-tree','--name-only',base,'web/changelog.json'))throw error;}
 need(!old||old.releases[0].version!==next.releases[0].version,'必须新增一条新发布记录，不能只修改旧记录');
 if(old)for(const r of old.releases)need(next.releases.some(n=>n.version===r.version),'不能删除历史发布记录');
 return next.releases[0];
}

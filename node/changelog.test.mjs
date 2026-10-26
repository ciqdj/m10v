import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,mkdir,rm,readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import {createServer} from './server.mjs';

test('release history is available without JavaScript and linked from product pages',async()=>{
 const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}`;
 try{
  for(const route of ['/changelog','/changelog/']){
   const r=await fetch(base+route);assert.equal(r.status,200);
   assert.match(r.headers.get('content-type'),/text\/html/);
   const html=await r.text();assert.ok(html.startsWith('<!doctype html>'));assert.match(html,/<a href="\/gr3\/">/);assert.match(html,/更新日志/);assert.match(html,/800T/);
   assert.match(html,/<h3>优化<\/h3>/);assert.doesNotMatch(html,/c3d54fe|历史源码回补|查看发布状态|查看记录 ↗/);assert.doesNotMatch(html,/<!-- RELEASES -->/);
  }
  for(const route of ['/','/guide/','/gr3/','/gr4/','/gr2/'])assert.match(await(await fetch(base+route)).text(),/href="\/changelog\/"/);
 }finally{await new Promise(r=>server.close(r));}
});

test('history validates evidence and escapes display text',async()=>{
 const {validateChangelog,renderReleases}=await import('./changelog.mjs');
 const data=JSON.parse(await readFile(new URL('../web/changelog.json',import.meta.url),'utf8'));
 validateChangelog(data);
 const bad=structuredClone(data);bad.releases[0].title='<script>alert(1)</script>';
 assert.match(renderReleases(bad),/&lt;script&gt;/);assert.doesNotMatch(renderReleases(bad),/<script>/);
 for(const mutate of [d=>d.releases[1].version=d.releases[0].version,d=>d.releases[0].changes=[],d=>d.releases[1].evidence='current',d=>d.releases[0].date='2026-02-30',d=>d.releases[1].evidence_url='javascript:alert(1)']){
  const v=structuredClone(data);mutate(v);assert.throws(()=>validateChangelog(v));
 }
});

test('release guard rejects missing or reused notes and accepts a new release',async()=>{
 const {checkReleaseChangelog}=await import('./changelog.mjs');
 const repo=await mkdtemp(path.join(os.tmpdir(),'m10v-changelog-'));
 const git=(...args)=>execFileSync('git',args,{cwd:repo,encoding:'utf8'}).trim();
 const save=async d=>writeFile(path.join(repo,'web/changelog.json'),JSON.stringify(d));
 const first={schema:'m10v-changelog/v1',releases:[{version:'2026.10.16.1',date:'2026-10-16',title:'首次记录',changes:['改动'],commit:null,evidence:'current',evidence_url:null}]};
 try{
  await mkdir(path.join(repo,'web'));git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
  await save(first);git('add','.');git('commit','-qm','first');const base=git('rev-parse','HEAD');
  assert.throws(()=>checkReleaseChangelog(repo,base),/changelog|更新日志/);
  const reused=structuredClone(first);reused.releases[0].title='只修改旧记录';await save(reused);
  assert.throws(()=>checkReleaseChangelog(repo,base),/新发布记录/);
  const next=structuredClone(first);next.releases[0]={...next.releases[0],commit:base,evidence:'deployment',evidence_url:'https://github.com/zhaoo/m10v/actions/runs/1'};
  next.releases.unshift({...first.releases[0],version:'2026.10.16.2'});await save(next);
  assert.equal(checkReleaseChangelog(repo,base).version,'2026.10.16.2');
  await save({...next,releases:[next.releases[0]]});assert.throws(()=>checkReleaseChangelog(repo,base),/历史发布记录/);
  assert.throws(()=>checkReleaseChangelog(repo,'main; echo nope'),/base/);
 }finally{await rm(repo,{recursive:true,force:true});}
});


test('customer sections keep categories, notices and escaping without exposing internal evidence', async()=>{
 const {validateChangelog,renderReleases,readChangelog}=await import('./changelog.mjs');
 const data=readChangelog();
 data.releases=[{...data.releases[0], title:'简明更新',changes:['支持新功能','修复 <误触>','改善速度'], sections:[{type:'added',items:['支持新功能']},{type:'fixed',items:['修复 <误触>']},{type:'improved',items:['改善速度']}],notice:'仅 GR III <测试版>'}];
 const html=renderReleases(data);
 assert.match(html,/<h3>新增<\/h3>/);assert.match(html,/<h3>修复<\/h3>/);assert.match(html,/<h3>优化<\/h3>/);
 assert.match(html,/修复 &lt;误触&gt;/);assert.match(html,/仅 GR III &lt;测试版&gt;/);
 assert.doesNotMatch(html,/actions\/runs|commit\//);
 for(const mutate of [d=>d.releases[0].sections[0].type='unknown',d=>d.releases[0].sections[0].items=[],d=>d.releases[0].sections.push(d.releases[0].sections[0]),d=>d.releases[0].sections[0].items=['文案不一致'],d=>d.releases[0].notice=42]){
  const invalid=structuredClone(data);mutate(invalid);assert.throws(()=>validateChangelog(invalid));
 }
 const legacy=structuredClone(data);delete legacy.releases[0].sections;
 assert.match(renderReleases(legacy),/支持新功能/);
});

import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const source = path.join(root, 'vendor', 'gr4', 'web');
const target = path.join(root, 'web', 'gr4');
await rm(target, { recursive: true, force: true });
await mkdir(target, { recursive: true });
await cp(source, target, { recursive: true });

const htmlPath = path.join(target, 'index.html');
let html = await readFile(htmlPath, 'utf8');
html = html.replace('<title>固件编辑器</title>', '<title>m10v · GR IV 编辑器</title>')
  .replace('<link rel="stylesheet" href="/styles.css">', '<link rel="stylesheet" href="/shared/product.css">\n  <link rel="stylesheet" href="/gr4/styles.css">')
  .replace(/<header class="topbar">[\s\S]*?<\/header>/,
    `<header class="product-topbar">
    <a class="product-brand" href="/"><strong>m10v</strong><span>GR 固件工作台</span></a>
    <nav class="model-switch" aria-label="切换机型"><a href="/gr3/">GR III</a><a class="active" href="/gr4/">GR IV</a></nav>
    <div class="product-actions"><span class="local-state">仅在本机运行</span><details id="more-menu" class="more-menu"><summary class="button quiet">项目</summary><div class="more-actions"><button id="open-setup" class="button quiet" type="button">设置</button><button id="open-drafts" class="button quiet" type="button">已保存项目</button><button id="import-project" class="button quiet" type="button">导入项目</button><button id="export-project" class="button quiet" type="button" disabled>导出编辑备份</button><button id="download-original" class="button quiet" type="button" disabled>备份原始固件</button><button id="refresh-status" class="button quiet" type="button">刷新状态</button></div></details></div>
  </header>`)
  .replace('<main id="editor-workspace" class="workspace">', '<main id="editor-workspace" class="workspace product-workspace">')
  .replace('<aside class="sidebar panel">', '<aside class="sidebar panel product-panel">')
  .replace('<section class="editor panel"', '<section class="editor panel product-panel"')
  .replaceAll('class="source-summary panel"', 'class="source-summary panel product-panel"')
  .replaceAll('class="build-panel panel"', 'class="build-panel panel product-panel"')
  .replaceAll('class="history-summary panel"', 'class="history-summary panel product-panel"')
  .replace('支持刷回低版本固件', '允许低版本固件')
  .replace(/<p id="risk-detail"[\s\S]*?<\/p>/,
    '<p id="risk-detail" class="field-help">生成的文件不会自动写入相机。请在继续前确认版本、备份和恢复条件。</p>')
  .replace(/<p class="field-help export-free-notice">[\s\S]*?<\/p>/, '')
  .replace(/<div class="inline-actions"><a id="risk-terms-link"[\s\S]*?<\/div><div class="inline-actions">/,
    '<div class="inline-actions">')
  .replace(/\s*<dialog id="support-dialog"[\s\S]*?<\/dialog>/, '')
  .replaceAll('href="/styles.css"', 'href="/gr4/styles.css"')
  .replaceAll('src="/app.js"', 'src="/gr4/app.js"')
  .replaceAll('src="/calibration-ui.js"', 'src="/gr4/calibration-ui.js"')
  .replaceAll('href="/terms.html"', 'href="/gr4/terms.html"')
  .replaceAll('src="/assets/', 'src="/gr4/assets/');
await writeFile(htmlPath, html);

const appPath = path.join(target, 'app.js');
let app = await readFile(appPath, 'utf8');
app = app.replace('const $ = (id) => document.getElementById(id);',
  'const $ = (id) => document.getElementById(id);\nlet sessionToken = "";')
  .replace('const RECENT_DRAFT_KEY = "firmware-editor-demo-recent-draft";',
    'const RECENT_DRAFT_KEY = "m10v-gr4-recent-project";')
  .replace(/function openSupport\(\) \{[^}]+\}/, 'function openSupport() {}')
  .replace(/  const support = element\("div"[\s\S]*?target\.append\(support\);\n/, '')
  .replace(/  \$\("risk-summary"\)\.textContent = "[^"]+";/,
    '  $("risk-summary").textContent = "该操作会生成固件文件，但不会自动写入相机。请确认版本、备份和恢复条件后继续。";')
  .replace('$("save-project").disabled = !project.can_generate; $("export-project").disabled = false;',
    '$("save-project").disabled = !project.can_generate; $("export-project").disabled = false; $("download-original").disabled = !project.input?.sha256;')
  .replaceAll('/api/', '/api/gr4/')
  .replaceAll('"/terms.html"', '"/gr4/terms.html"')
  .replace('headers: { "Content-Type": raw ? "application/octet-stream" : "application/json" },',
    'headers: { "Content-Type": raw ? "application/octet-stream" : "application/json", "X-M10V-Token": sessionToken },')
  .replace('state.status, state.settings] = await Promise.all',
    'state.status, state.settings] = await Promise.all')
  .replace('const records = state.status.projects || [];',
    'sessionToken = state.status.session_token || sessionToken;\n  const records = state.status.projects || [];');
app += '\n$("download-original").onclick = () => { if (!state.project?.input?.sha256) return; location.href = "/api/gr4/original?sha256=" + encodeURIComponent(state.project.input.sha256); };\n';
await writeFile(appPath, app);

const cssPath = path.join(target, 'styles.css');
let css = await readFile(cssPath, 'utf8');
css += `
body{background:var(--product-bg);color:var(--product-ink)}
.product-topbar .button.quiet{color:#d7dad6}.product-topbar .button.quiet:hover{background:#323532;color:#fff}
.workspace.product-workspace{display:grid;grid-template-columns:248px minmax(420px,1fr) 286px;gap:18px;max-width:1560px;margin:0 auto;padding:24px clamp(18px,3vw,42px) 40px}
.panel.product-panel{border-color:var(--product-line);border-radius:var(--product-radius);background:var(--product-paper);box-shadow:var(--product-shadow)}
.function-nav{padding:10px;gap:4px}.function-button{border-radius:7px;padding:11px 12px}.function-button.active{border-color:transparent;background:#e7e5de}
.button{border-radius:7px}.button.primary{background:#252826;border-color:#252826}.button.primary:hover:not(:disabled){background:#3a3e3b;border-color:#3a3e3b}
.source-summary,.build-panel,.history-summary{padding:20px}.editor{padding:26px 28px}.filter-section{padding:18px 10px}.source-summary h2,.build-panel h2,.history-summary h2{font-size:12px}
@media(max-width:1040px){.workspace.product-workspace{grid-template-columns:210px minmax(0,1fr)}.firmware-rail{grid-column:1/-1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:720px){.workspace.product-workspace{display:block;padding:14px}.workspace.product-workspace>*+*{margin-top:14px}.sidebar{min-height:auto}.function-nav{display:flex;overflow-x:auto}.function-button{flex:0 0 auto}.firmware-rail{display:grid;grid-template-columns:1fr}.editor{padding:21px 18px}}
`;
await writeFile(cssPath, css);
console.log('Built namespaced GR IV web module');

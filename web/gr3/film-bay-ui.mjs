const builtIn = new Set(['ektar100', 'gold200', 'pro400h', 'portra400', 'vision3-250d']);
let picked;

function node(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

export function renderFilmBayDetail(target, { looks, request, download, iconCanvas }) {
  const optional = looks.filter((look) => !builtIn.has(look.id) && !look.id.startsWith('lut-'));
  if (!picked) picked = new Set(optional.map((look) => look.id));
  picked = new Set([...picked].filter((id) => optional.some((look) => look.id === id)));
  const workflow = node('div', '', 'bay-workflow');
  const intro = node('p', '固件内置五卷胶片。挑选其它胶卷，离线生成通用 FILMS.GRF，再到相机菜单把它装进五个仓位。', 'bay-intro');
  const choose = node('section', '', 'bay-step');
  choose.append(node('span', '01 / 挑选胶卷', 'bay-kicker'),
    node('h4', '建立随身胶卷库'),
    node('p', '内置五卷始终保留；其余胶卷可自由选择。文件在本机生成，无需输入机身码。'));
  const actions = node('div', '', 'bay-pick-actions');
  const all = node('button', '全选', 'outline'); all.type = 'button';
  const none = node('button', '只保留内置', 'outline'); none.type = 'button';
  actions.append(all, none); choose.append(actions);
  const groups = node('div', '', 'bay-groups');
  const boxes = [];
  for (const groupName of [...new Set(looks.filter((look) => !look.id.startsWith('lut-')).map((look) => look.group))]) {
    const groupLooks = looks.filter((look) => look.group === groupName && !look.id.startsWith('lut-'));
    const block = document.createElement('details'); block.className = 'bay-group';
    block.open = groupName === '内置胶片';
    block.append(node('summary', `${groupName} · ${groupLooks.length} 卷`));
    const grid = node('div', '', 'bay-film-grid');
    for (const look of groupLooks) {
      const fixed = builtIn.has(look.id);
      const card = node('label', '', 'bay-film-item' + (fixed ? ' fixed' : ''));
      const box = document.createElement('input'); box.type = 'checkbox';
      box.checked = fixed || picked.has(look.id); box.disabled = fixed; box.value = look.id;
      if (!fixed) boxes.push(box);
      card.append(box, iconCanvas(look.iconPixelsBase64), node('span', look.name));
      if (fixed) card.append(node('small', '内置'));
      grid.append(card);
    }
    block.append(grid); groups.append(block);
  }
  choose.append(groups);
  const issue = node('section', '', 'bay-step bay-issue');
  issue.append(node('span', '02 / 本地生成', 'bay-kicker'), node('h4', '下载 FILMS.GRF'));
  const summary = node('p', '', 'bay-summary');
  const button = node('button', '生成并下载 FILMS.GRF', 'primary'); button.type = 'button';
  const status = node('p', '', 'bay-result'); status.setAttribute('role', 'status');
  issue.append(summary, node('p', '文件由 m10v 在本机编码并签名，须配合本页构建的胶片库固件使用。固件和文件已做离线回读，GR III 实机换片仍待验证。', 'bay-disclosure'),
    button, status);
  const install = node('section', '', 'bay-step bay-install');
  install.append(node('span', '03 / 机内切换', 'bay-kicker'), node('h4', '复制到 SD 卡并装入仓位'),
    node('p', '将 FILMS.GRF 放入 SD 卡根目录的 GRLIFE 文件夹。刷入同一版本的 m10v 胶片库固件后，在相机中打开「胶卷 → 换胶卷」，选择仓位，使用 ADJ 切换分组并按 OK 装入。'));
  workflow.append(intro, choose, issue, install); target.append(workflow);

  const update = () => {
    const count = 5 + picked.size;
    summary.textContent = `内置 5 卷 · 另选 ${picked.size} 卷 · 共 ${count} 卷 · 约 ${Math.round((1 + 2 * count) * 8192 / 1024)} KB`;
  };
  for (const box of boxes) box.addEventListener('change', () => {
    box.checked ? picked.add(box.value) : picked.delete(box.value);
    status.textContent = ''; update();
  });
  all.addEventListener('click', () => {
    for (const box of boxes) box.checked = true;
    picked = new Set(optional.map((look) => look.id)); status.textContent = ''; update();
  });
  none.addEventListener('click', () => {
    for (const box of boxes) box.checked = false;
    picked.clear(); status.textContent = ''; update();
  });
  button.addEventListener('click', async () => {
    button.disabled = true; button.textContent = '正在生成…';
    status.textContent = '正在本机编码胶片记录并校验文件。'; status.classList.remove('error');
    try {
      const films = optional.filter((look) => picked.has(look.id)).map((look) => look.id);
      const response = await request('/api/gr3/film-bay/pack', {method:'POST',
        headers:{'Content-Type':'application/json'},body:JSON.stringify({films})});
      await download(response, 'FILMS.GRF');
      status.textContent = 'FILMS.GRF 已下载。请复制到 SD 卡的 GRLIFE 文件夹。';
    } catch (error) {
      status.textContent = error.message === 'not found'
        ? '当前服务进程尚未加载胶片库下载功能。请重新启动 m10v 并刷新页面后重试。'
        : error.message || '本地生成失败。';
      status.classList.add('error');
    } finally {button.disabled = false;button.textContent = '生成并下载 FILMS.GRF';}
  });
  update();
}

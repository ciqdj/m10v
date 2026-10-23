/** The same navigation contract is used by every public page and model desk. */
export function navigationItems(pathname = '/') {
  const path = pathname.replace(/\/index\.html$/, '/');
  const model = path.startsWith('/gr4') ? 'gr4' : 'gr3';
  const sd = /\/sd-library(?:\.html)?\/?$/.test(path);
  return [
    ['gr3', '/gr3/', 'GR III / IIIx'], ['gr4', '/gr4/', 'GR IV'],
    ['gr2', '/gr2/', 'GR II'], ['sd', path.startsWith('/gr2') ? '/gr2/#sd' : `/${model}/sd-library.html`, 'SD 胶卷'],
    ['guide', '/guide/', '说明'], ['changelog', '/changelog/', '更新日志'],
  ].map(([id, href, label]) => ({id, href, label, active: id === 'sd' ? sd : !sd && (id === 'gr3' ? path.startsWith('/gr3') : id === 'gr4' ? path.startsWith('/gr4') : id === 'gr2' ? path.startsWith('/gr2') : path.startsWith(`/${id}`))}));
}
export function renderNavigation(pathname = '/') {
  return `<nav class="site-navigation" aria-label="主导航">${navigationItems(pathname).map(item => `<a href="${item.href}"${item.active ? ' class="current" aria-current="page"' : ''}>${item.label}</a>`).join('')}<a class="navigation-github" href="https://github.com/zhaoo/m10v" target="_blank" rel="noopener noreferrer" aria-label="GitHub 项目，新窗口打开">GitHub ↗</a></nav>`;
}
export function mountNavigation() {
  const header = document.querySelector('body > header');
  if (!header) return;
  const brand = header.querySelector('.m10v-brand');
  const status = header.querySelector('#studio-model-status');
  const menu = header.querySelector('#more-menu');
  if (!brand) return;
  brand.setAttribute('href', '/');
  const brandName = brand.querySelector('.m10v-brand-name');
  if (brandName) brandName.innerHTML = '<b>m10v</b><span class="brand-dot">·</span>GR固件工作台';
  header.classList.add('site-header');
  header.replaceChildren(brand);
  header.insertAdjacentHTML('beforeend', renderNavigation(location.pathname));
  if (status) {status.className = 'navigation-source-status'; status.removeAttribute('aria-current'); header.append(status);}
  if (menu) header.append(menu);
}
if (typeof document !== 'undefined') mountNavigation();

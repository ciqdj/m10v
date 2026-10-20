# Ubuntu 宝塔运维

## 目标与连接

新主机 `47.96.158.25`，阿里云杭州轻量、Ubuntu 24.04 x86_64、2 核 2 GB、40 GB 磁盘。域名 `m10v.izhaoo.com`。旧主机 `114.55.142.234` 保留作迁移回退，不再接收新版本。

管理入口使用专用本机密钥，不依赖会过期的 Workbench 分享链接：

```sh
ssh -i ~/.ssh/m10v_admin_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=~/.ssh/m10v_known_hosts admin@47.96.158.25
```

admin 可使用 sudo。服务器 Ed25519 指纹应为 `SHA256:14wdxfbNTDj0zIp43y0RGv7O+beA1qYEvbIJnrVQ9Qw`，由用户从 Workbench 提供，已与 SSH 握手比对。主机重装或指纹变化时重新核验。私钥、面板密码不写入技能、Git 或日志。

## 运行布局

- 宝塔仅管理 Nginx、站点与证书；无需 PHP/MySQL/FTP。
- 源码 `/www/wwwroot/m10v`，Git main，源码对 www 可读；data 对 www 可写。
- systemd `m10v` 以 www 运行，只监听 `127.0.0.1:3000`。
- Node 24 LTS（初始化时 24.22.0）放在 `/opt/m10v-node`，固定入口 `/usr/local/bin/m10v-node`；Python 为项目 `.venv`。
- Ubuntu 依赖：`git python3 python3-venv clang lld build-essential`；venv 包 `pillow numpy capstone unicorn`。
- 完整发布的 GR III 扩展组合和 GR IV 定制需要锁定的 `.runtime/grlife-current`。初始化必须运行 `node scripts/sync-grlife-runtime.mjs --current`，或传输已核验缓存并以 www 验证 `runtimeAvailable()` 为 true；保持 manifest 与逐文件 SHA-256 校验。缓存默认权限为 600/700，需要仅对该目录改为文件 644、目录 755。缺失会导致发布回退，不能跳过组合构建。
- 三个官方输入分别为 `bin/fwdc239b-gr3-official.bin`、`bin/fwdc243b-gr3x-official.bin`、`bin/fwdc248b-gr4-officical.bin`。它们不在 Git，重建服务器时单独安全传输并核对完整 SHA-256。
- 2 GB 节点保留至少 1 GB swap（当前宝塔已配置 1 GB），并对服务及发布构建设置 `NODE_OPTIONS=--max-old-space-size=128`。这是 JS 堆限制，Buffer、Python、编译器仍需额外内存。
- 主机 `vm.swappiness=60`。2026-10-20 核实原配置为 0，网站处理与部署构建并发时出现内核 global OOM、swap 使用仍为 0；已在 `/etc/sysctl.conf.before-m10v-swap-20261020` 备份并改为 60。重建时同时检查 `sysctl vm.swappiness`、`swapon --show` 与实际 swap 使用，不能只看已分配的 swap 总量。构建采用 `MemoryHigh=600M`、`MemoryMax=700M`、`MemorySwapMax=384M`，仍保留超时、整组停止及回滚。
- Nginx 使用仓库 `deploy/nginx-location.conf`：300 秒超时、16k 响应头缓冲、`proxy_buffers 4 16k`、`proxy_busy_buffers_size 32k`，避免约 7 KB 审计头超过默认缓冲。先 `nginx -t`，再 reload。Nginx 由宝塔官方极速安装器安装，当前 1.28.3。
- 宝塔新建站点的默认图片、JS/CSS 本地缓存 location 会截获代理静态资源并返回 404。只移除这两类缓存规则，保留敏感文件及 ACME 规则，并分别验证 studio.js、styles.css、logo.png 返回 200。

## HTTPS 与面板

站点证书由 Certbot DNS-01 签发，文件在 `/etc/letsencrypt/live/m10v.izhaoo.com/`；Nginx 与宝塔读取 `/www/server/panel/vhost/cert/m10v.izhaoo.com/` 的受保护副本。部署 hook `/etc/letsencrypt/renewal-hooks/deploy/m10v-copy-cert.sh` 在续期后复制并检查、重载 Nginx。私钥仅 root 可读。2026-10-19 初始证书有效至 2027-01-16；每次检查应以实际 `openssl x509 -dates` 为准。

当前 DNS 验证需要人工更新 TXT，不能因 Certbot 默认 timer 已启用就报告自动续期已打通。备案完成且公网 HTTP 验证可达后，改为 webroot 并实际验证：

```sh
sudo certbot reconfigure --cert-name m10v.izhaoo.com --webroot -w /www/wwwroot/m10v-site
sudo certbot renew --dry-run
```

Nginx 的 ACME 验证 location 与网站根目录必须保留。当前 TLS 1.2/1.3、HTTP/2 与 HTTP→HTTPS 跳转已配置；验证不得使用 `-k` 忽略证书。服务器内部验证使用 `curl --resolve m10v.izhaoo.com:443:127.0.0.1 https://m10v.izhaoo.com/`。

宝塔使用 HTTPS IP 证书，入口为 `https://47.96.158.25:8888` 加 `admin_path.pl` 中的安全路径。8888 只对管理员访问 IP 放行，3000 不向公网开放。宝塔会过滤 curl 等爬虫 UA，登录页返回 404 时先用实际浏览器或完整浏览器 UA 验证，不能关闭面板安全入口、IP限制或爬虫过滤来通过检查。

## 自动发布

GitHub 仓库 `zhaoo/m10v` 的 main 推送触发 `Deploy Baota`；develop 不重复触发。

- `M10V_DEPLOY_HOST` 仓库变量为新 IP。
- `M10V_DEPLOY_KNOWN_HOSTS` 只包含核验过的新服务器主机公钥。
- `M10V_DEPLOY_SSH_KEY` Secret 为专用发布私钥，与本机管理密钥分离。
- root 的发布公钥绑定 `restrict,command="/usr/local/lib/m10v-deploy/receive-ssh.sh"`。仅接受 `deploy <完整SHA>` 和最大 24 MiB Git bundle；不能执行交互 Shell。
- root 持有 receive-ssh.sh、update-server.sh；日志 `/var/log/m10v-deploy-ssh.log`。修改仓库副本后先安装新的 root 副本，再发布。
- 先完成 changelog 及本地检查，原子推送 main/develop；等待对应 SHA 的 Actions 成功，并读取 `DEPLOY_OK`。实际构建 GR III、GR IIIx、GR IV，不能跳过机型保护。

## 排障与验证

`systemctl status m10v`、`journalctl -u m10v` 检查后端；宝塔 Nginx 配置在 `/www/server/panel/vhost/nginx/`。面板安全入口可通过 `sudo cat /www/server/panel/data/admin_path.pl` 查询。用户名及密码由用户持有，不写入此文件。修改密码后 `bt default` 可能仍显示失效的初始密码，不能把它当作当前密码。

应用能访问但保存失败时，检查站点 error.log 的 upstream timeout / too big header，以及 `free -m`、`vmstat`、Node RSS/Swap。不要仅延长超时。完整验收应经 HTTPS 代理执行导入、预检、构建和下载，并核对下载文件 SHA-256 与 `X-M10V-Native-Receipt` 中的 candidate_sha256。

大陆节点备案完成前，阿里云可能返回 `Non-compliance ICP Filing` 或在 TLS 握手阶段重置连接。服务器 loopback HTTPS 验证通过不能代表公网已恢复；换证书或改 TLS 套件不能解除备案拦截。分别报告服务部署、DNS 指向、证书校验、公网可用性。

回退优先使用发布脚本失败恢复；手工回退前核对干净工作区，保留 bin/data/.venv。DNS 切回旧 IP 需要重新核对旧站点状态，不能把大陆备案拦截当作可回退修复。

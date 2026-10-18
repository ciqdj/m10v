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
- 三个官方输入分别为 `bin/fwdc239b-gr3-official.bin`、`bin/fwdc243b-gr3x-official.bin`、`bin/fwdc248b-gr4-officical.bin`。它们不在 Git，重建服务器时单独安全传输并核对完整 SHA-256。
- 2 GB 节点保留 2 GB swap，并对服务及发布构建设置 `NODE_OPTIONS=--max-old-space-size=128`。这是 JS 堆限制，Buffer、Python、编译器仍需额外内存。
- Nginx 使用仓库 `deploy/nginx-location.conf`：300 秒超时、16k 响应头缓冲、`proxy_buffers 4 16k`、`proxy_busy_buffers_size 32k`，避免约 7 KB 审计头超过默认缓冲。先 `nginx -t`，再 reload。Nginx 由宝塔官方极速安装器安装，当前 1.28.3。
- 宝塔新建站点的默认图片、JS/CSS 本地缓存 location 会截获代理静态资源并返回 404。只移除这两类缓存规则，保留敏感文件及 ACME 规则，并分别验证 studio.js、styles.css、logo.png 返回 200。

## 自动发布

GitHub 仓库 `zhaoo/m10v` 的 main 推送触发 `Deploy Baota`；develop 不重复触发。

- `M10V_DEPLOY_HOST` 仓库变量为新 IP。
- `M10V_DEPLOY_KNOWN_HOSTS` 只包含核验过的新服务器主机公钥。
- `M10V_DEPLOY_SSH_KEY` Secret 为专用发布私钥，与本机管理密钥分离。
- root 的发布公钥绑定 `restrict,command="/usr/local/lib/m10v-deploy/receive-ssh.sh"`。仅接受 `deploy <完整SHA>` 和最大 24 MiB Git bundle；不能执行交互 Shell。
- root 持有 receive-ssh.sh、update-server.sh；日志 `/var/log/m10v-deploy-ssh.log`。修改仓库副本后先安装新的 root 副本，再发布。
- 先完成 changelog 及本地检查，原子推送 main/develop；等待对应 SHA 的 Actions 成功，并读取 `DEPLOY_OK`。实际构建 GR III、GR IIIx、GR IV，不能跳过机型保护。

## 排障与验证

`systemctl status m10v`、`journalctl -u m10v` 检查后端；宝塔 Nginx 配置在 `/www/server/panel/vhost/nginx/`。面板入口与登录信息由服务器管理员运行 `sudo bt default` 获取，不写入此文件。

应用能访问但保存失败时，检查站点 error.log 的 upstream timeout / too big header，以及 `free -m`、`vmstat`、Node RSS/Swap。不要仅延长超时。完整验收应经 HTTPS 代理执行导入、预检、构建和下载，并核对下载文件 SHA-256 与 `X-M10V-Native-Receipt` 中的 candidate_sha256。

大陆节点备案完成前，阿里云可能返回 `Non-compliance ICP Filing` 或在 TLS 握手阶段重置连接。服务器 loopback HTTPS 验证通过不能代表公网已恢复；换证书或改 TLS 套件不能解除备案拦截。分别报告服务部署、DNS 指向、证书校验、公网可用性。

回退优先使用发布脚本失败恢复；手工回退前核对干净工作区，保留 bin/data/.venv。DNS 切回旧 IP 需要重新核对旧站点状态，不能把大陆备案拦截当作可回退修复。

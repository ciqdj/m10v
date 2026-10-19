# 宝塔部署 · m10v.izhaoo.com

支持 Ubuntu 24.04 和 Alibaba Cloud Linux 3。宝塔管理 Nginx／证书，systemd 守护 Node；也可使用宝塔 Node 项目或附带的 PM2 模板。两种进程管理方式任选一种，不要重复启动同一端口。先用 `cat /etc/os-release` 核对实际系统。

当前生产节点：Ubuntu 24.04，`47.96.158.25`；运维连接与迁移排障见 [Ubuntu 宝塔运维](../skills/m10v-baota-publish/references/ubuntu-server.md)。

## 1. 域名与网络

为 `m10v.izhaoo.com` 添加指向服务器公网 IP 的 A 记录。阿里云安全组和服务器防火墙放行 80、443。应用端口 3000 仅监听 127.0.0.1，不需要对公网放行。

若使用中国内地节点，需要按阿里云要求完成备案：[阿里云备案指南](https://help.aliyun.com/zh/icp-filing/basic-icp-service/getting-started/quick-start-for-icp-filing-for-personal-websites)。

## 2. 安装与下载

在宝塔软件商店安装 Nginx，使用 Node.js 版本管理器或已有 PM2 管理器安装 Node 24 LTS，并将它设为命令行版本。这两个管理器互斥，不要为此卸载已有的管理器。终端执行以下命令（需要管理员权限）：

```bash
node -v
sudo apt update
sudo apt install -y git python3 python3-venv clang llvm lld build-essential
```

Alibaba Cloud Linux 3 使用官方系统源安装编译工具；在宝塔软件商店安装「python环境管理器」，再安装 Python 3.12，保留系统 Python：

```bash
sudo dnf install -y git clang llvm lld
```

下载项目，再创建独立虚拟环境。Ubuntu 可以直接使用 `python3`；宝塔 Python 环境使用管理器显示的解释器绝对路径替换它：

```bash
sudo git clone --branch main https://github.com/zhaoo/m10v.git /www/wwwroot/m10v
cd /www/wwwroot/m10v
python3 -m venv .venv
.venv/bin/python -m pip install pillow numpy capstone unicorn
mkdir -p bin data
```

首次上线无需恢复未开放的 GR IV 校准 DNG。完整发布会构建 GR III 扩展组合包及 GR IV 定制能力，必须安装已锁定的兼容运行时：

```bash
node scripts/sync-grlife-runtime.mjs --current
```

脚本对上游 manifest 和每个文件校验 SHA-256，上游版本变化时停止，不能关闭校验。也可从已验证主机安全传输 `.runtime/grlife-current` 后以 www 调用 `runtimeAvailable()` 复核。缓存脚本生成的目录和文件默认仅所有者可读，安装后只对该运行时目录设置目录 755、文件 644，保证 www 可读取；不把运行时源码提交到 Git。

将三份本机已有官方 BIN 上传至（GR IV 同样用于发布构建检查）：

```text
/www/wwwroot/m10v/bin/fwdc239b-gr3-official.bin
/www/wwwroot/m10v/bin/fwdc243b-gr3x-official.bin
/www/wwwroot/m10v/bin/fwdc248b-gr4-officical.bin
```

在服务器生成历史读取别名（第一次执行时）：

```bash
ln -s bin/fwdc239b-gr3-official.bin fwdc239b-offical.bin
ln -s fwdc239b-offical.bin fwdc239b.bin
```

## 3. 启动 Node 后端

### 推荐：systemd

确认宝塔创建的 `www` 用户存在，并创建稳定的 Node 启动链接。源代码只需对 www 可读，data 目录需要可写：

```bash
id www
M10V_NODE_PATH=$(command -v node)
sudo ln -s "$M10V_NODE_PATH" /usr/local/bin/m10v-node
sudo chown -R www:www /www/wwwroot/m10v/data
sudo cp deploy/m10v.service /etc/systemd/system/m10v.service
sudo systemctl daemon-reload
sudo systemctl enable --now m10v
sudo systemctl status m10v --no-pager
curl -fsS http://127.0.0.1:3000/ -o /dev/null -w '%{http_code}\n'
```

若 `/usr/local/bin/m10v-node` 已存在，先检查 `readlink`，不要盲目覆盖。Node 升级或目录移动后需要检查该链接仍然有效。Node 后端默认不直接暴露公网。

查看日志：

```bash
sudo journalctl -u m10v -n 80 --no-pager
```

### 使用宝塔 Node 项目时

项目目录 `/www/wwwroot/m10v`，启动文件 `node/server.mjs`，端口 `3000`，运行用户 `www`。在该项目的环境变量设置以下值；不同宝塔版本的位置有差异，不支持设置环境变量时使用上面的 systemd 方案。

```text
M10V_PORT=3000
NODE_OPTIONS=--max-old-space-size=128
M10V_PUBLIC_ORIGIN=https://m10v.izhaoo.com
M10V_NO_BROWSER=1
M10V_LLVM_CLANG=/usr/bin/clang
M10V_PYTHON=/www/wwwroot/m10v/.venv/bin/python
```

也提供了 `ecosystem.config.cjs` 供已使用 PM2 的环境参考。保持单进程，不要配置 cluster 多实例；当前构建互斥和会话令牌为进程级。

GR IV 同时需要 LLVM 的 `llvm-objcopy`、`llvm-nm` 和 LLD 的 `ld.lld`，仅安装 clang 无法生成固件。安装后在站点目录以服务用户运行 `runuser -u www -- env M10V_LLVM_CLANG=/usr/bin/clang M10V_PYTHON="$PWD/.venv/bin/python" /usr/local/bin/m10v-node scripts/check_gr4_release.mjs`，完成实际编译、封包及回读检查。

## 4. 配置宝塔站点

1. 添加静态站点 `m10v.izhaoo.com`，站点目录可用 `/www/wwwroot/m10v-site`，与源码目录分开。
2. 申请 SSL 证书，开启 HTTPS，并将 HTTP 跳转到 HTTPS。
3. 反向代理目标填写 `http://127.0.0.1:3000`，关闭代理缓存。保留浏览器的 Origin，发送 Host 为请求的原始域名；不要改成 localhost，也不要清空 Origin。
4. 在 HTTPS server 中使用 `nginx-location.conf` 的 location 内容：上传上限 64m，代理读写超时 300s。如果宝塔已经生成 `location /`，编辑它，不能再添加一个重复块。
5. 移除宝塔自动生成的图片与 JS/CSS 本地缓存 location，它们会截获应用静态资源并从空站点目录返回 404。保留敏感文件拦截及 ACME 验证规则。
6. 保留示例中的 16k 响应头缓冲、4×16k buffers 与 32k busy buffers，先 nginx -t，通过后再重载。原生下载审计响应头约 7 KB。

低内存服务器使用上述 Node 堆设置，促使固件处理期间及时回收临时对象；它并不把整个进程内存限制在 128 MiB。固件 Buffer 和编译进程仍需额外内存。不要与其他高内存服务共用仅 2 GB 的节点。

保留 `proxy_buffer_size 16k`、`proxy_buffers 4 16k` 和 `proxy_busy_buffers_size 32k`：原生固件下载包含约 7 KB 的审计响应头，默认小缓冲区可能拒绝响应。修改后先执行 `nginx -t`，通过后再重载。

若公网 HTTP 返回阿里云 `Non-compliance ICP Filing`，但服务器本地 HTTPS 验证正常，应处理大陆节点备案接入，或迁移到香港/海外节点。更换证书不能解决该类网络入口拦截。

测试阶段建议开启宝塔网站的“密码访问”，限制访问人员。`/api/status` 的令牌用于请求校验，不是账号登录；当前服务不是具备访客数据隔离、配额和权限体系的多用户 SaaS。

## 5. 验收

先检查目标域名：

```bash
curl -fsS https://m10v.izhaoo.com/ -o /dev/null -w '%{http_code}\n'
curl -fsS https://m10v.izhaoo.com/guide/ -o /dev/null -w '%{http_code}\n'
```

随后在浏览器核对：导入两款官方样本、胶卷目录／五槽／800T、风险弹窗取消与确认、对应机型 BIN 下载。再在服务器各生成一份固件候选：

```bash
cd /www/wwwroot/m10v
M10V_LLVM_CLANG=/usr/bin/clang node scripts/export_gr3_m10v_native.mjs builds/server-gr3-test
M10V_LLVM_CLANG=/usr/bin/clang node scripts/export_gr3_m10v_native.mjs builds/server-gr3x-test --model=gr3x
```

2026-10-14 已在 Alibaba Cloud Linux 3、Node 24、Python 3.12、LLVM 15 环境生成 GR III／GR IIIx 候选，并验证 www 服务用户可构建。柔光的二次幂采样使用位移，避免旧版 LLVM 引入相机中不存在的 ARM 除法辅助函数。修改固件的相机刷入和成像仍需实机验收。

如果宝塔的暂停代理规则生成空配置，先备份该站点的代理文件，再使用 `nginx-location.conf` 补齐。执行 `nginx -t` 确认通过后才重载，并在宝塔核对代理状态。保留原有证书、ACME 验证目录和其他站点的配置。

## 6. 更新

管理员拉取源码后重启服务，不要删除 bin、data、.venv：

```bash
cd /www/wwwroot/m10v
sudo git pull --ff-only origin main
sudo systemctl restart m10v
```

参考：[宝塔反向代理文档](https://docs.bt.cn/user-guide/site/php/site-config/reverse-proxy)、[阿里云安全组](https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups)、[Node.js 下载](https://nodejs.org/en/download/)、[Ubuntu clang](https://packages.ubuntu.com/clang)。

## GitHub 推送后自动部署

现有服务器可使用签名 Webhook 自动部署 `main`；配置、持久化队列、日志核验和停用方式见 [WEBHOOK.md](WEBHOOK.md)。

当前生产自动发布使用 [受限 SSH 方案](SSH.md)。HTTPS Webhook 因云端网络问题未启用。

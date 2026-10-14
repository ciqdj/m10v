---
name: m10v-baota-publish
description: Use when the user asks to push or deploy the M10V GitHub project to its Baota server, quickly synchronize a release, or verify m10v.izhaoo.com after publishing.
---

# M10V 宝塔快速发布

发布目标：GitHub `https://github.com/zhaoo/m10v.git` 的 `main` 与 `develop`，生产 `/www/wwwroot/m10v`，systemd `m10v`（www、loopback3000），公网 `https://m10v.izhaoo.com`。宝塔入口由用户提供；当前服务器 IP 为 `114.55.142.234`。先确认仍匹配现场状态。

用户明确要求推送并部署该项目时，按既有授权完成，不重复索取确认。只要求检查时，不执行推送或部署。登录凭据、cookie、私钥不放进 skill、Git 或输出。

## 本地推送

检查当前分支、diff 与待发布提交，选择明确文件提交；不能仅 push 而遗漏未提交修复。运行适合改动的测试（Node 原生路由/部署检查、相关 ARM 测试），核对成功结果。刷新 origin，确认远端 main/develop 都是发布 HEAD 的祖先，然后普通原子推送：

```sh
git fetch origin
git merge-base --is-ancestor origin/main HEAD
git merge-base --is-ancestor origin/develop HEAD
git push --atomic origin HEAD:main HEAD:develop
git rev-parse HEAD
git ls-remote origin refs/heads/main refs/heads/develop
```

记录完整40位SHA；遇到分叉或推送拒绝先处理，不强推。未经测试的修改不自动提交。

## 服务器更新

优先使用现有可用 SSH；若 SSH 验证失败，使用用户已登录的宝塔「终端 → 本地服务器」。不为快速发布自动新增 SSH 授权、修改面板API白名单或开放应用端口。终端用一次性粘贴而非逐字输入长命令；粘贴前确认空提示符，执行后读实际输出。宝塔常用命令可保存下面的通用命令，终端执行时填写此次SHA。

发布脚本仅更新已有main checkout：检查干净工作区和服务，获取指定提交，fast-forward，以www构建GR III调试版和GR IIIx，再重启、检查调试开关，失败尝试保留工作区修改的回退。保留bin/data/.venv；不运行git clean，不修改Nginx或证书。

首次/脚本更新时，在服务器运行（将完整SHA替换为此次发布值）：

```sh
cd /www/wwwroot/m10v && git fetch origin main && git show origin/main:skills/m10v-baota-publish/scripts/update-server.sh > /tmp/m10v-update-server.sh && bash /tmp/m10v-update-server.sh --check
bash /tmp/m10v-update-server.sh --deploy FULL_COMMIT_SHA
```

脚本 `--check` 为只读环境核验；获取脚本会写其专用/tmp文件并更新远端Git引用。`--deploy` 含实际更新与服务重启。服务器路径、服务用户或进程管理方式不同则先核对，不直接套用脚本。没有登录能力时，完成本地准备并明确缺少的登录条件。

## 上线校验

必须看到 `DEPLOY_OK commit=<此次SHA> ... service=active`，再用curl检查公网首页、`/gr3/`、`/guide/`及`/gr3/studio.js`中debug_mode请求。固件构建与HTTP检查不能替代相机实测。报告GitHub提交链接、上线地址和实际检查结果；失败说明推送/同步/构建/重启具体停在哪一步。

---
name: m10v-baota-publish
description: Use when the user asks to push or deploy the M10V GitHub project to its Baota server, quickly synchronize a release, or verify m10v.izhaoo.com after publishing.
---

# M10V 宝塔快速发布

发布目标：GitHub `https://github.com/zhaoo/m10v.git` 的 `main` 与 `develop`，生产 `/www/wwwroot/m10v`，systemd `m10v`（www、loopback3000），公网 `https://m10v.izhaoo.com`。宝塔入口由用户提供；当前服务器 IP 为 `47.96.158.25`（Ubuntu 24.04）；旧 `114.55.142.234` 不再作为新发布目标。先确认仍匹配现场状态。

用户明确要求推送并部署该项目时，按既有授权完成，不重复索取确认。只要求检查时，不执行推送或部署。登录凭据、cookie、私钥不放进 skill、Git 或输出。

## 每次发布必须更新 changelog

每个新发布提交都必须在仓库 `web/changelog.json` 的 `releases` 首部新增记录，页面为 `https://m10v.izhaoo.com/changelog/`。即使只有修复、部署脚本或文档变化，也要记录。重跑同一 SHA 的失败发布复用原记录，不重复新增。

新增记录包含：唯一日期编号 `YYYY.MM.DD.N`、上海时区日期、中文标题、具体改动和影响机型。最新记录使用 `evidence: current`、`commit: null`、`evidence_url: null`。把上一条记录归档：填完整提交 SHA 及对应 GitHub Actions 成功链接，证据为 `deployment`；没有成功部署证据的历史条目用 `documented` 或 `source`，不能写成已上线。保留已有历史条目，不把计划、失败回退或离线测试写成实机验证。

发布前在仓库运行 `node scripts/check_changelog.mjs --base 上次推送的完整SHA`，并运行 `node --test node/changelog.test.mjs`。检查器要求新增版本并保留历史；只改旧条目、漏写或复用版本号都会失败。changelog 与功能一起提交、一起推送，不能留待上线后补写。GitHub Actions 在 SSH 部署前强制执行同一检查。

发布成功后核对 `/changelog/` 为 200，确认最上方记录与本次版本、改动一致，再报告发布完成。维护技能时同步仓库版与本机 `~/.codex/skills/m10v-baota-publish/SKILL.md`。

新服务器的管理连接、初始化、低内存配置和排障见 [Ubuntu 宝塔运维](references/ubuntu-server.md)，仅在初始化、迁移或排障时读取。

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

## 首选：GitHub Actions 自动发布

当前生产方式见仓库 `deploy/SSH.md`。原子推送 main/develop 后，跟踪 main 对应的 `Deploy Baota`：`gh run list --workflow deploy-baota.yml` 找到本次 SHA，`gh run watch RUN_ID --exit-status` 等到终态，并检查实际日志中的 `DEPLOY_OK commit=此次完整SHA ... service=active`。不能把 push 成功或任务启动当作部署完成。失败先读首个构建/健康检查错误，修复后重新发布；同一 SHA 的重试使用 `gh run rerun RUN_ID`。

服务器用 root 持有的受限入口传入 Git bundle，以 www 构建 GR III 调试组合包，并检查 GR IIIx 官方基线及原生详细菜单导出拦截；800T 原厂详细菜单地址当前仅验证 GR III。不要为通过发布检查关闭机型保护。修改 root 持有的发布脚本后，需通过现有管理入口安装已校验的新脚本，再重跑；常规发布不新增 SSH 授权。用户明确要求初始化新服务器时可建立专用受限发布密钥。

以下手动链路仅作为已授权发布的备用，执行前同样先更新并校验 changelog。

## 服务器更新

优先使用现有可用 SSH；若 SSH 验证失败，使用用户已登录的宝塔「终端 → 本地服务器」。不为快速发布自动新增 SSH 授权、修改面板API白名单或开放应用端口。终端用一次性粘贴而非逐字输入长命令；粘贴前确认空提示符，执行后读实际输出。宝塔常用命令可保存下面的通用命令，终端执行时填写此次SHA。

发布脚本仅更新已有main checkout：检查干净工作区和服务，获取指定提交，fast-forward，以www构建GR III调试版并检查GR IIIx机型保护，再重启、检查调试开关，失败尝试保留工作区修改的回退。保留bin/data/.venv；不运行git clean，不修改Nginx或证书。

服务器GitHub连接正常时，在服务器运行（将完整SHA替换为此次发布值）：

```sh
cd /www/wwwroot/m10v && git fetch origin main && git show origin/main:skills/m10v-baota-publish/scripts/update-server.sh > /tmp/m10v-update-server.sh && bash /tmp/m10v-update-server.sh --check
bash /tmp/m10v-update-server.sh --deploy FULL_COMMIT_SHA
```

脚本 `--check` 为只读环境核验；获取脚本会写其专用/tmp文件并更新远端Git引用。`--deploy` 含实际更新与服务重启。服务器路径、服务用户或进程管理方式不同则先核对，不直接套用脚本。没有登录能力时，完成本地准备并明确缺少的登录条件。

## 增量包快速链路

服务器拉取GitHub超时，或用户希望快速同步时，先用宝塔终端读取服务器当前完整HEAD，并确认它是本地发布HEAD的祖先；创建增量包（只含Git跟踪对象，不含bin/data/.venv）：

```sh
git bundle create /tmp/m10v-release.bundle SERVER_SHA..HEAD
git bundle verify /tmp/m10v-release.bundle
```

在已登录宝塔「文件」中导航到`/tmp`，上传bundle和本skill的`update-server.sh`。使用唯一文件名避免覆盖已有文件。上传本地源代码属于本次同步发布的范围；不导出浏览器cookie或新增面板API权限。随后终端执行：

```sh
bash /tmp/update-server.sh --check
bash /tmp/update-server.sh --deploy FULL_COMMIT_SHA /tmp/m10v-release.bundle
```

服务器验证bundle前置对象并把HEAD导入专用`refs/m10v/releases/<SHA>`，核对SHA再更新，不修改origin/main引用。首次部署或服务器HEAD不是祖先时不能使用该增量范围，先检查差异。bundle导入与直接fetch共享构建、重启和回退逻辑。

## 上线校验

必须看到 `DEPLOY_OK commit=<此次SHA> ... service=active`，再用curl检查公网首页、`/gr3/`、`/guide/`、`/changelog/`及`/gr3/studio.js`中debug_mode请求。固件构建与HTTP检查不能替代相机实测。报告GitHub提交链接、上线地址和实际检查结果；失败说明推送/同步/构建/重启具体停在哪一步。

# 状态：历史 HTTPS 方案，当前停用

生产自动部署使用 [SSH.md](SSH.md)。以下为保留的实现说明。

# GitHub → 宝塔自动部署

GitHub Actions push/main → 签名 Git bundle → 现有 HTTPS `/hooks/github` → 仅 loopback 监听的独立部署服务 → 固定部署脚本。仅 `zhaoo/m10v` 的 `main` 推送触发；`develop` 推送忽略，避免双分支同步造成重复发布。

使用原始请求体 HMAC-SHA256 和常量时间比较校验 GitHub 签名。密钥仅保存于 GitHub Webhook 配置和服务器 `/etc/m10v-deploy/secret`，不写入 Git。站点 www 进程仅转发请求，不持有密钥。部署服务使用固定命令参数，仅接收 40 位 SHA；部署脚本再次 fetch 并校验远端 main，执行 fast-forward、完整 GR III 组合包/GR IIIx 构建、服务重启和健康检查；失败回退。

队列持久化于 `/var/lib/m10v-deploy/state.json`，服务中断重启会恢复未完成任务。相同运行中/已部署 SHA 不重复执行，快速连续推送合并到最新等待提交。失败会记录状态和 systemd 日志。Actions 在投递后继续查询签名状态接口，只有对应 SHA 部署成功才变绿。

首次在生产 checkout 执行 `bash deploy/install-webhook.sh /安全目录/secret`，在 GitHub Actions Secrets 中配置同一 `M10V_DEPLOY_SECRET`，工作流见 `.github/workflows/deploy-baota.yml`。原生 GitHub Webhook 已停用，避免重复触发。不要把服务器 API、SSH 私钥或面板 Cookie 放进 webhook。

核验：`journalctl -u m10v-deploy -n 100 --no-pager`，以及 `cat /var/lib/m10v-deploy/state.json`。成功日志必须包含此次 SHA 的 `DEPLOY_OK` 和 `DEPLOY_FINISHED`。失败修复后可以在 GitHub 重新投递；禁用自动发布可执行 `systemctl disable --now m10v-deploy` 并禁用 GitHub Actions 的 Deploy Baota 工作流。

接收器和更新脚本位于 root 所有的 `/usr/local/lib/m10v-deploy`，普通应用重启不会中断部署。修改这些受控文件后需要重新安装；常规业务提交无需重新配置。

服务器到 GitHub 的连接不稳定，因此 Actions 从固定初始提交 `f34a53636bae0bb9939d4ae9f5057b1d2c005762` 创建增量 Git bundle，通过 HTTPS 携带原始请求体签名投递，并有限重试。服务器验证 bundle 前置对象、目标 SHA 和 fast-forward 关系后导入，自动部署无需主动访问 GitHub。JSON 请求体上限 32 MiB，超过上限工作流明确失败。签名事件 `m10v-status` 仅返回当前部署队列状态，不执行部署。

查看自动发布结果：[Deploy Baota Actions](https://github.com/zhaoo/m10v/actions/workflows/deploy-baota.yml)。只向 `main` 推送时自动发布；同步 `develop` 不会重复部署。也可在 Actions 页面选择 Run workflow 对 main 重试。绿色表示状态接口已确认对应提交部署完成，红色保留具体构建或网络错误。

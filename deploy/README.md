# GitHub → 宝塔自动部署

GitHub push webhook → 现有 HTTPS `/hooks/github` → 仅 loopback 监听的独立部署服务 → 固定部署脚本。仅 `zhaoo/m10v` 的 `main` 推送触发；`develop` 推送忽略，避免双分支同步造成重复发布。

使用原始请求体 HMAC-SHA256 和常量时间比较校验 GitHub 签名。密钥仅保存于 GitHub Webhook 配置和服务器 `/etc/m10v-deploy/secret`，不写入 Git。站点 www 进程仅转发请求，不持有密钥。部署服务使用固定命令参数，仅接收 40 位 SHA；部署脚本再次 fetch 并校验远端 main，执行 fast-forward、完整 GR III 组合包/GR IIIx 构建、服务重启和健康检查；失败回退。

队列持久化于 `/var/lib/m10v-deploy/state.json`，服务中断重启会恢复未完成任务。相同运行中/已部署 SHA 不重复执行，快速连续推送合并到最新等待提交。失败会记录状态和 systemd 日志；GitHub 202 仅表示入队，不表示上线完成。

首次在生产 checkout 执行 `bash deploy/install-webhook.sh /安全目录/secret`，再创建 GitHub push webhook，URL `https://m10v.izhaoo.com/hooks/github`，JSON，SSL 验证启用，配置同一 secret。不要把服务器 API、SSH 私钥或面板 Cookie 放进 webhook。

核验：`journalctl -u m10v-deploy -n 100 --no-pager`，以及 `cat /var/lib/m10v-deploy/state.json`。成功日志必须包含此次 SHA 的 `DEPLOY_OK` 和 `DEPLOY_FINISHED`。失败修复后可以在 GitHub 重新投递；禁用自动发布可执行 `systemctl disable --now m10v-deploy` 并禁用 GitHub webhook。

接收器和更新脚本位于 root 所有的 `/usr/local/lib/m10v-deploy`，普通应用重启不会中断部署。修改这些受控文件后需要重新安装；常规业务提交无需重新配置。

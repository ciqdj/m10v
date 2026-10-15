# 推送 main 后自动部署宝塔

当前生产入口为 GitHub Actions [Deploy Baota](https://github.com/zhaoo/m10v/actions/workflows/deploy-baota.yml)。只响应 main 推送，可手动 Run workflow 重试；develop 不会重复发布。并发任务按顺序执行。

Actions 先运行部署保护测试，再创建相对固定初始版本 f34a53636bae0bb9939d4ae9f5057b1d2c005762 的 Git bundle，通过受限 SSH 传入服务器；服务器无需拉取 GitHub。远端核验 bundle 前置对象、完整目标 SHA 和 fast-forward 关系，然后以 www 构建完整 GR III 组合包及 GR IIIx，重启 m10v 并检查健康状态。只有本次 SHA 的 DEPLOY_OK 返回后，Actions 才显示绿色。构建或健康检查失败会尝试回退。

专用公钥在 root authorized_keys 中使用 restrict 和固定 command；拒绝交互 shell、PTY、端口转发、agent 转发及任意远端命令，仅接受 `deploy <40位SHA>`。私钥存储于仓库 Actions Secret `M10V_DEPLOY_SSH_KEY`，不写入 Git。服务器 Ed25519 指纹通过宝塔核对，固定于仓库变量 `M10V_DEPLOY_KNOWN_HOSTS`，SSH 严格验证。

服务器入口 `/usr/local/lib/m10v-deploy/receive-ssh.sh` 与 update-server.sh 均由 root 持有；日志 `/var/log/m10v-deploy-ssh.log`。站点服务仍由 www 运行，监听 loopback 3000；未新增公网端口。增量包上限 24 MiB，超限明确失败。

常规业务推送无需重新配置。修改受控入口脚本后，应在服务器核验并安装相应文件。停用自动发布：在 GitHub 禁用 Deploy Baota 工作流；撤销服务器访问：从 root authorized_keys 移除注释为 m10v-github-actions-20261015 的专用公钥。

HTTPS Webhook 方案因 GitHub Actions 到本站 TLS 连接重置暂不启用，原生 Webhook 和 m10v-deploy 接收服务均应保持停用。历史实现见 WEBHOOK.md，不是当前生产入口。

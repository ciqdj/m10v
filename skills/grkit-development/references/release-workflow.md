# 测试包 → 用户验证 → GitHub/宝塔

用户在本次会话明确约定：先测试包，由用户验证完成后再合并main、推送GitHub并部署宝塔。此顺序同时约束普通M10V固件迭代和未来GRKit SD模式；写入skill本身不启动发布。

## 1. 准备和本地实现

先 fetch 并核对远端最新 main 与线上部署 SHA，以最新 main 创建独立分支/工作树；保留当前脏工作区与无关文件。历史候选只移植本次功能的最小差异，其他逻辑复用最新 main。不自动迁移架构或拆掉既有功能。先用功能保护矩阵明确本次改动和回归范围。

## 2. 交付测试候选

回归通过后，沿本项目已有导出链构建候选，而非另写一套绕过网页配置/校验的构建器。普通GR3/IIIx的CLI为 `scripts/export_gr3_m10v_native.mjs`；A/B专用 `scripts/build_gr3_ab_candidate.mjs` 包含显式HDF和扩展保护，不能无分析替换为普通默认导出。只有迁移范围明确时才用GRKit构建链。

每包交付：

- 唯一候选名称、目标机型/固件、BIN/ZIP或SD包的SHA-256。
- Git revision及dirty状态、源/配置指纹、build receipt/manifest、匹配的FILMS.M10或GRF及恢复说明。不能仅记录HEAD而漏掉未提交native代码。
- 本次改动、应保留功能、实际验证/跳过项、已知问题、用户需验证的具体步骤。
- 如需诊断，仅针对问题启用debug，说明build_id和要回传的文件；不要以环形日志尾窗未出现事件证明没有发生。

输出到新的构建目录，保留上个候选。交付包不夹带其他机型候选、不覆盖卡上用户配置，不上传固件/照片/密钥到公开Git。

阶段终态是 **WAITING_FOR_USER_VALIDATION**：此时可以结束当前回合等待实测。不能合并main、推送任意GitHub分支、运行Actions或部署/重启生产。M10V的deploy-baota.yml对main push自动部署，所以“只推main先不部署”也不满足门槛。

## 3. 接受用户结果

用户针对当前可识别候选明确说测试通过/验证完成后，记录候选SHA、验证机型、反馈和覆盖范围，进入 **USER_VALIDATED**。根据该授权直接继续后续发布，不再重复索取同一目标确认。

问询、沉默、只说下载成功、单项通过或仍报告故障不能推断完整验收。当前指令若缺少通过确认，停在测试包阶段。修复失败项后发新包，旧包通过不能覆盖新候选。批准后若又改native行为/构建参数，重新构建并获得该候选验证；纯changelog/provenance变化经检查不改变候选行为可继续。

## 4. 合并与发布

读 `m10v-baota-publish`，本机通常在 `/Users/zhaoo/.codex/skills/m10v-baota-publish/SKILL.md`，仓库版在 `skills/m10v-baota-publish/SKILL.md`。它负责具体Git、changelog、Actions、SSH及宝塔恢复细节，本文件负责统一的前置门槛。

只提交本次相关代码及必需技能/文档，记录用户验证的source fingerprint。更新并验证changelog，再将验收的改动合并main，运行集成检查。合并冲突若改变功能则重新测试包。沿既有main/develop同步策略普通推送，不强推、不夹带无关改动。main/develop分叉先核对整合，不能假定任意开发HEAD都能覆盖两者。

推送main会触发生产Actions；跟踪确切SHA到终态，要求日志 `DEPLOY_OK commit=<本次SHA> ... service=active`。检查公网首页、机型工作台、guide、changelog与实际版本。生产HTTP/构建通过不扩大用户设备验证范围。失败按发布技能恢复，不能报告上线成功。

最后报告用户验收候选、发布完整SHA及提交链接、Actions结果、线上校验；如部署脚本或网页生成的运行体与验收候选不同，先解释并验证来源，不能仅凭同一版本名认定相同。

---
name: grkit-development
description: Use when modifying M10V Ricoh GR functionality, preventing regressions in its existing features, researching or migrating to GRKit SD plugins, diagnosing Linux installer, RTOS hooks, or Ricoh Bluetooth AF/status connections on macOS, preparing camera test packages, or releasing a user-validated M10V build through GitHub to Baota. Does not imply permission to publish an unvalidated candidate.
---

# M10V 开发与发布 · GRKit

用源码证据完成 GRKit 链路研究、插件开发和机型适配，避免重复逆向。参考资料按需读取，先定位函数再读代码。

## M10V 的首要约定

在 M10V 工作时，先读 [已有功能保护基线](references/m10v-preservation.md)，再按 [回归索引](references/m10v-regression.md) 选择验证。GRKit 是实现参考，不是新的产品规格；不能因其默认实现更简单而减少 M10V 功能、重排胶卷编号、更换存档或改变按键语义。用户明确要求改变的行为按本次需求修改，同时保护其他行为。源码中的修复候选和已知故障不等于设备已验收。

统一交付流程：**开发及回归 → 交付可识别的测试包 → 等用户明确验证通过 → 合并 main → 推送 GitHub → 部署宝塔并核验**。细则见 [测试包与发布门槛](references/release-workflow.md)。测试包未获确认前不合并 main、不推送 GitHub、不触发生产部署。用户对同一候选明确验证通过后，按既定流程完成发布，无需再索取重复批准。

## 每次迭代以线上最新 main 为基线

所有后续迭代先 fetch 远端 main，核对宝塔当前部署 SHA，记录最新 main 与线上提交；若两者不一致，先查清待发布差异。以最新 main 创建独立工作树/分支，再移植本次功能的最小改动。历史候选仅作为修复参考，不能用旧分支、旧文件或旧产物覆盖 main 的其他逻辑。

合并冲突时保留 main 的既有功能、胶卷目录与槽数、资源编号、存储 ABI、机型门禁及网页行为，只调整本次需求涉及的部分；共享接入点需适配当前 main。发布前再次 fetch，以最新 main 为比较基线审查累计 diff；若 main 已推进，先整合并核验，不能强推或回退线上功能。无法证明行为等价的冲突改动应重新交付测试包，不沿用旧候选的设备验收。

## 起点

研究基线：`ahonn/grkit` commit `8a886cbfa7ca3af7726c942d4b0d367d9486acb4`，2026-10-21，workspace version `1.1.1`。本机源码在 `/Users/zhaoo/Desktop/code/zhaoo/grkit`；这是便利路径，不是使用前提。先确认实际 checkout 的 revision 与 dirty 状态。更新源码时保留本地更改，重新核实受影响的结论，不把 `main` 网页缓存当作固定版本。

```sh
git -C /path/to/grkit rev-parse HEAD
git -C /path/to/grkit status --short
```

没有源码时克隆 `https://github.com/ahonn/grkit.git` 到独立目录；需要复现基线时在干净副本中 checkout 上述 commit。不要覆盖 M10V 的脏工作区。

## 核心模型

`电脑 Rust 构建 → SD ModeSet 启用脚本 → STARTUP.TTL → PLUGINS.TTL → lcmd → Linux SCAN/INSTALL → /dev/mem → RTOS Hook → 插件处理`

- 插件静态链接进 runtime；SD 加载不代表动态卸载或运行中热替换。
- Linux 安装器负责地址校验、内存发布；菜单/成像 Hook 在 RTOS 域。Linux gdb 不能直接当成 RTOS 调试器。
- 驻留 TTL 脚本持有插件数据和图标数组。脚本异常退出会释放数组，已有 Hook 可能悬空。
- 修改代码、GRF 或插件选择后，以关机、更新卡文件、重新开机安装为默认开发循环。
- `PLUGINS.TXT` **不存在=全选，空文件=全不选**；未知或重复名称拒绝安装。关闭一个插件不会关闭其他插件共享的扩展点。
- 公开版本号不唯一标识内部构建；保留指令、重定位、分配及尾部占用检查。失败时分析报告，不能删校验强装。

## 任务路由

| 任务 | 先读 |
| --- | --- |
| 任何 M10V 功能迭代或迁移 | [m10v-preservation.md](references/m10v-preservation.md)、[m10v-regression.md](references/m10v-regression.md) |
| 测试包、用户验收、main/GitHub/宝塔 | [release-workflow.md](references/release-workflow.md)，生产执行再读 m10v-baota-publish |
| 启动、Linux→RTOS、内存和重定位 | [chain-and-source-map.md](references/chain-and-source-map.md) |
| 新增功能、修改插件、构建打包 | [development.md](references/development.md) |
| M10V 迁移、安装失败、设备验证、恢复 | [migration-and-diagnostics.md](references/migration-and-diagnostics.md) |
| GR2013/GR II 逆向、GitHub 参考筛选与固件差异定位 | [gr1-gr2-porting.md](references/gr1-gr2-porting.md) |
| 保持上网 Wi-Fi 的蓝牙连接、触屏 AF、USB/BLE 能力边界 | [bluetooth-diagnostics.md](references/bluetooth-diagnostics.md)，附 macOS 只读探针 |
| 本 skill 的实测范围 | [validation.md](references/validation.md) |

## 开发工作流

1. 记录机型、公开版本、官方输入哈希、运行中构建证据、已有自定义固件/SD 脚本、源码 revision 和任务范围。没有相机时继续离线工作，明确设备步骤未执行。
2. 决定改哪层：效果数据用 GRF；功能用插件；固件依赖放 core/target；连接和工具链用 host。不要给插件直接塞 RTOS 地址。
3. 按参考定位调用者、扩展点和生命周期，选择现有插件作为模式。新增低层 Hook 同时更新目标布局、重定位输入、扩展点归属和测试。
4. 先补可观察行为的验证，再修改；从 registry/ABI 真源生成派生文件。保存构建清单与证据，避免重复全文件反汇编或全图 ARM 模拟。
5. 完成相关 host/ARM/打包检查后，报告各层结果。缓存同步、图像所有权和任务生命周期变化需要真机证据才能宣称设备通过。

## 按影响机型发布

单机型需求默认只构建和验证受影响机型，以缩短发布等待。网站仍是同一个服务、同一次代码部署；按机型裁剪的是固件构建和回归范围。

- 发布前记录 `base_commit`、`target_commit`、受影响机型、实际构建机型和跳过原因。范围以生产当前提交到目标提交的累计差异及共享调用链为准，不能仅按用户提到的机型或文件名前缀判断。
- GR III 专属改动只跑 GR III 固件构建；IIIx、IV 专属改动同理。GR III/IIIx 复用的 runtime、胶卷数据、状态协议、固件解码器或网页模块变化时，纳入实际消费者。依赖范围不明时保留完整机型构建。
- 仅文档、skill、静态文案等不影响固件产物的改动，跳过固件编译，保留相关文档/页面、部署保护和服务健康检查。所有发布都保留 changelog、提交身份核验、原子更新、回滚和线上检查。
- 机型裁剪只减少无关任务；保留选中机型的官方身份、指令 preimage、空间、封包回读及资源限制。发布记录明确哪些机型未执行，不把跳过记为通过。

**现有实现边界（2026-10-25）**：`skills/m10v-baota-publish/scripts/update-server.sh` 仍固定遍历 `gr3 gr3x gr4`，服务器还执行 root 持有的脚本副本。仅更新本 skill 不会自动提速。下一次单机型发布前先落实构建范围选择，覆盖 GR III 专属、共享变化、纯文档、未知范围及多提交累计变化用例；经已有管理入口同步并核对服务器脚本，再从日志确认选中机型执行、其他机型明确跳过。当前已启动的发布沿原流程完成，不为提速取消后重跑。

## 完成时输出

给出改动层/扩展点、源码 revision、机型和固件身份、产物及哈希、实际执行/跳过的检查、安装结果与恢复方法。引用源码用 commit 固定链接。研究或写 skill 不代表获准启用相机设置、覆盖 SD 或刷机；这些动作须处于当前用户授权范围内。

固件、运行时 dump、照片和用户配置不进入 skill 或公开 Git。保留代码和效果数据各自许可证。USB Shell、网络代理、RTOS 远程调试和热更新必须有独立实现及验证，不能从 SD 启动成功推导出来。

# GR III 三批扩展实施计划总览

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement these plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 建议由当前会话直接实施；所有分计划以本文全局约束为准。

**Goal:** 实现用户批准的三批固件功能和流畅UI，并完成XMP与Street关机图相邻扩展。

**Architecture:** 严格规范化配置驱动补丁组合、分配和独立验证。保留旧五槽构建回归，逐步接入新胶片系统。预览使用Worker，任务使用不可变快照和可取消运行资源。

**Tech Stack:** Node.js 20+、ES modules、Python 3.12、现有ARM/C构建和Unicorn/Capstone测试、原生HTML/CSS/JS。

**Spec:** [已确认设计](../specs/2026-10-13-m10v-gr3-three-batches-design.md)

## Global Constraints

- 精确官方源SHA-256：`d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`，GR III Street Edition 2.10；固件版本默认保持原厂。
- 不自动刷相机，不扩大到其他机型。所有candidate绑定source/configuration/engine/evidence摘要。
- 固件和图片只在本机处理；BOOTPARA/DRAMPARA/PARTPARA/M0/BOOT/CPU及更新器默认原样。
- 草稿schema `m10v-gr3-customization/v2`；`filmSystem.mode`取`replace-five`或`append`。追加首版上限6，最大组合证明不足时阻断，不能默默降规格。
- 颗粒UI档0/1/2/3对应原厂存储0/3/2/1；质感按胶片ID保存，按槽位解析后写入。
- 柔光/红晕仅支持已证明的拍摄JPEG路径；DNG CFA和内嵌预览分别报告。RAW NR有意改变CFA，采用相同NR策略基线验证空间效果。
- 浏览器验收：1280×800及窄视口，控件反馈p95<100ms、低清p95<150ms、应用同步长任务不超过50ms、620×413高质量稳定预览<1s。保存300ms合并，停止拖动200ms后精细预览。
- 不把离线成功写成实机成功。未知证据保留具体阻断，不用占位按钮冒充交付。
- 保留现有未提交/未跟踪工作；只按明确清单提交本次文件，不使用`git add .`。工作树选择遵循using-git-worktrees技能，必要时包含现有未提交依赖，不能从HEAD建立缺失基础文件的checkout。
- 固定上游来源、摘要和许可；GPL代码与色彩数据各自保留声明；不提交固件或未经许可素材。

## Review Focus

1. 改方案时旧预检/拟合响应迟到：A1/A4必须拒绝旧revision，不能替换当前UI或下载旧结果。
2. 胶片换槽/删除/升级时参数串档：A3/B3必须按稳定ID映射并安全回到合法原厂值。
3. 生成器与验证器共同误解补丁：A2/B2/C1独立从配置推导前像、映射、分派，不能只比较自报expected。
4. Shared Vivid/Positive分支和已有800T入口被覆盖：A3/C1验证Positive原样、单入口调用顺序与所有寄存器/缓存契约。
5. 取消操作只是UI消失、后台继续写文件：A4验证worker/进程退出、临时目录删除、候选无新下载入口。

## 执行顺序与分计划

1. [A：原厂编辑、颗粒和流畅编辑基础](2026-10-13-gr3-batch-a.md)，任务A1→A2→A3→A4。
2. [B：色相分区、新增胶片、RAW显影与保存](2026-10-13-gr3-batch-b.md)，任务B1→B2→B3。
3. [C：柔光/800T组合、RAW NR和更多画幅](2026-10-13-gr3-batch-c.md)，任务C1→C2→C3。
4. [D：XMP、Street关机图和整体验收](2026-10-13-gr3-batch-d.md)，任务D1→D2→D3。

每个任务先写失败测试、确认失败原因、实现、跑相关检查、按文件清单提交。检查通过后只因新改动或未解决问题重复检查；整批结束做全量回归和真实浏览器操作。任务涉及固件地址时先完成只读前像/调用链探查，再进入补丁实现。

## 当前状态和验收

设计已确认，计划待审阅，功能实施尚未开始。上一轮基线npm test为84通过、1跳过；实施前读取最新状态，不能沿用旧测试结果作最终验收。

- [ ] A完整接入构建、独立回读与UI。
- [ ] B六槽最大组合、RAW显影/存储生命周期和原厂模式回归。
- [ ] C组合效果、内存边界、NR策略与画幅消费者证明。
- [ ] D导入/关机资源与全流程性能记录。
- [ ] 按每项实际证据更新README、测试记录、许可和候选manifest。

实施计划确认后，当前会话直接执行。只有出现必要外部证据缺失才停下报告具体条件；相机验收结果仍需用户提供实机记录。

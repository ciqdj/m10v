# 官方固件导入兼容性修复验证 / 2026-10-26

基线与线上最近成功部署均为 `a4aefd2238afc1dc3f3b8405976a51a330f7cf9c`；工作分支 `daily/fix-firmware-frame-compatibility`，本报告记录发布前含未提交更改的离线验证快照。用户随后明确确认本次候选已验收，并要求合并 main、发布 GitHub 与宝塔。

## 问题与修复

用户提供的 GR III 官方 2.20：SHA-256 `5c53760b3b564c87239dbf7f5c94d0f6fd91accd156ec4ba672ebfd6b861793e`，30,472,516 字节，内部版本 2.20.20.28。

身份检查已支持此包，但共用帧解析与重封包仍固定 2.10 展开长度 59,718,388；2.20 实际展开为 59,798,532，触发 `invalid frame sizes`。同时 2.20 的 RTOS/资源位置已变化，不能直接套用 2.10 补丁。

按用户明确确认的方案，上传原包保持不变；所有工作台资源与构建入口使用同机型已验证基线。当前注册来源覆盖 GR III 2.10、2.20 与 IIIx 1.60；对应输出基线为 GR III 2.10、IIIx 1.60。未知身份继续拒绝，不将任意 BIN 视为官方。新增来源仍需登记和验证身份，但无需给共用解码器新增固定长度分支。

解码器改为读取容器声明的长度，并保留上限、边界和可选精确长度校验。重封包使用源包实际长度。实际导出测试还复现了改名 Clear 时的跨帧回指问题，已在帧重放与补丁重封包中检查前 8191 字节历史，避免复用依赖已改变历史的压缩帧。

导入报告保留上传版本及 SHA；新增 build_source 披露输出基线与两份身份。资源读取、原生胶卷、原厂预设、800T、桥接和历史分析入口使用统一基线选择。备份和官方 SD 准备仍使用上传原包。导入、方案清单、预检、保存确认与下载完成提示明确显示输出基线。

## 已执行验证

- 先运行新增 2.20 测试，观察到固定长度解码与缺少构建来源元数据的失败，再修复并复测。
- 41 项专项用例通过，0 失败、0 跳过；覆盖 2.20 解码/重封包、上传/备份、实际预设导出、原生预检、桥接预检、2.10/IIIx 来源与模型隔离、修改来源拒绝、开关机图片、保存确认和真实导入处理函数。
- 新增独立的跨帧预设改名回归：未修改 main 上复现“独立回读与补丁计划不一致”，修复后通过。专项总计 42 项通过。
- Chromium 真实页面上传用户提供的 2.20 包，来源区显示 2.20.20.28 和原始 SHA，输出基线与保存区显示 2.10。无 invalid frame sizes。
- 通过实际网页 HTTP 原生构建入口生成默认胶卷样本：150 个 Hook 校验通过；下载后再次执行 auditGr3Candidate 独立回读。
- `git diff --check`、Node 语法检查通过。

## 离线候选

目录：`builds/firmware-compat-220-20261026`。

- 输出文件：fwdc239b.bin，32,091,212 字节。
- SHA-256：`b8db3756febc37eb3d8bf13871c2d5e7c2493a974b12800299d37c450a3aabab`。
- 实际输出基线：GR III 2.10 / 2.10.21.27。
- 独立回读：展开 60,760,800 字节；2473 帧；仅 RTOS 分区变化，增长 1,042,412 字节。
- receipt.json 记录配置、源代码指纹、上传/基线身份及构建检查；manifest.json 记录未提交源码和产物 SHA。

本次为来源兼容修复，不包含 2.20 原生功能移植。导入 2.20 不代表输出保留 2.20 的新增行为，也不代表机内更新器接受 2.10；现有桥接版本限制保持不变。本次候选已获用户验收确认；上述条目记录的是开发侧离线验证证据。

## 全量回归的已知失败

首次完整 `npm test`：362 项，320 通过，36 失败，6 跳过。对这 36 项逐项在未修改的 main 副本复跑，35 项同样失败，主要是既有目录/状态/资源编号断言。另一项是此次输出版本文案变更使旧静态断言过期，已由真实导入处理函数的上传/输出版本行为断言覆盖。

同时补齐导入测试桩已有的 setModel 方法缺失，三个旧失败恢复通过；包括新增 2.20 UI 测试在内的 15 项 UI/保存确认复测全部通过。未修改这 32 项剩余旧失败的期望或实现，也未声称全量测试通过。它们都已在原始 main 复现：

- Charmera has an independent identity without stealing existing custom ID 79
- GR III preflight preserves factory choices and binds the new slot layout to approval
- Harman films append stable IDs and shared 40px icon records
- M10V native library builds from official bytes without a compatibility runtime and audits every patch
- Phoenix EI120 persists independently per slot and resets on a different stock
- SD pack contains every current platform recipe, independent of five active slots
- both colour views edit a single native configuration and do not restore the legacy film builder
- deleting texture processing retains all55 previous-revision film records
- digital HDF is independent of films and retired soft values never become HDF
- film name stamp migrates off and packs independently from date
- final joined firmware contains all selected components and rejects repaired-checksum tampering
- five retained style filters keep their identities and requested group names
- four colors persist per slot, texture reset preserves color and switching film clears it
- four halo controls and grain/soft are packed in each version4 slot
- fresh defaults and every film selection leave extra effects off
- fresh journals preserve independent timestamp corner and colour bytes
- last delivered 47-film and named custom packs remain readable after opt-in defaults
- legacy effects serialize as neutral and resetting preserves film and special controls
- legacy retired effects migrate to neutral without losing other slot settings
- new builtin LUT records retain names icons and source contract identity
- old effects upgrade and film-specific bounds accept bounded integer simulated EI
- old web configuration migrates into v4 and validates effect ranges
- one catalogue exposes only requested legacy simulations
- original M10V web workflow binds all five slots and timestamp into audited firmware
- prior renderer custom LUTs remain accepted while repaired-CRC tampering is rejected
- product home exposes GR IV native workbench and GR II inspection with truthful limits
- requested groups retain stock identities
- schema4 packs EI in each effects reserved byte and common reset preserves EI and disables extra effects
- single studio orders source, settings and save with the library embedded directly
- switching away from a manually enabled effect resets extras, selecting same film preserves them
- v1 built-in pack from the preceding release remains readable
- web debug export uses the running Node when the service PATH contains no node

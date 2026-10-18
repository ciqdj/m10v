# 2026-10-18 最新实机结果：一阶失败

用户补充：确认更新后立即失败，仍可正常开机。已撤销通过结论并暂停公开下载。未取得实机完整版本或实际 BIN 回传，不将失败直接归因为版本号。以下保留研究历史。

# GR III 纪念版拒绝更新与桥接研究（2026-10-18）

当前状态：已生成 2.10.22.27 两阶段实机测试包并接入本地平台，离线验证通过；周年机接受性、完整实机刷写与恢复仍未验证。最终产物和证据见文末。最初反馈为“刷入失败”，未取得完整机身版本或周年服务固件，这个提示本身不能确定是版本门禁还是其他校验。

## 本次重新执行的证据

`tests/test_gr3_updater_version_gate.py` 从精确官方 BIN 提取并校验 RTOS SHA，再执行原厂 ARM。已有四项测试复跑通过；新增桥接阶段对照覆盖四种合成输入：

- DSP、CPU 外层都提高时，公共类型 2 版本比较通过。
- 只提高外层 CPU、内层保持公共版本时，类型 6 仍拒绝。
- 第二包恢复官方版本、当前 CPU 运行号仍较高时，类型 2 拒绝。
- 第二包恢复官方版本、当前两个运行号均为公共基线时，类型 2 通过。

这些是局部比较测试；最后一项通过不证明有办法让服务固件接受第一包，也不证明 CPU 运行号已被实际恢复。当前版本 getter 是测试替身，闪存写入没有执行。

## 为什么待刷固件中的日志解决不了安装前拒绝

安装前执行的是机身中已存在的更新器。新 RTOS 中新增的日志代码并未启动，不能把它当作获取当前服务固件版本的入口。

公共 RTOS `536285dc..536285f8` 的拒绝分支只向 `536b82d4` 传固定格式串 `53d33804`：`Update Version is older than Current Version!!`，没有传 DSP/CPU 当前值或候选值。即使取得这条输出，也不足以得到四段版本。尚未确认未知周年固件的日志出口。

## 新追踪的原厂日志导出路径

在同一公共 RTOS 中静态确认：

- `5353e784..5353e7a4` 取得项目号并生成 `C:\\KB%ld.CAM`，路径放在 `5534706c`。这是原厂 CameraLog 路径，不是 M10V 日志。
- `5353cd84` 为导出实现，`5353cf2c..5353cf5c` 将版本型字段格式化为四段十进制；`5353d00c..5353d020` 把路径、缓冲区和长度交给 `5362eb24`。
- 表 `540927d8` 指向 `[CpuFwVersion]`，`540927e0` 指向 `[DspFwVersion]`，另有 Previous 版本字段。仍须追踪这些缓存字段的更新时点，不能直接假定永远等于当前运行号。
- `53021558` 调用导出实现，其前置分支比较子命令 `output`（`53d127a0`）。这是工程命令处理路径，尚未确认用户能从 USB/Wi-Fi/SD 访问命令入口。
- `536bf1cc..536bf1f0` 是另一个导出包装，调用后清理对象 `+74a`。`536bee80..536bef38` 的事件值 `0x12` 会设置 `+74a=1`；尚未闭合用户按键、菜单或文件到该事件的可达链路。

因此不能给用户杜撰“放一个文件即可导出日志”的操作，也不能把字符串存在当作导出已实机成功。

## 桥接需要解决的两个独立问题

1. 第一包必须被现有服务更新器接受。现有 DSP-only 开关保留 CPU 门禁，因此 CPU 更高时明确不足；服务更新器是否与公开固件一致仍未知。
2. 安装后的版本来源必须允许第二包。DSP 公共运行号来自代码常量；CPU 的尾号来自实际写入闪存头 `fffe0093`，单纯提高其元数据会保留较高运行号。

可研究的方案之一是单独改变 CPU 运行报号来源，让安装门槛版本与运行报号分离。它不是桥接的必要条件：下文 Ricoh-GRMod 参考提供了另一条已在 GR III 局部门禁验证的路线，即让安装后的更新器接受较低版本。不能声称只调包头已经实现可恢复桥接；也不能把修改待刷 RTOS 的比较指令当作第一次安装的绕过。

## 需要的现场证据

- 受影响相机刚拍的原始 JPEG/DNG，用 MakerNote 读取 DSP 尾号；不能通过此推断 CPU。
- 更新失败发生在确认版本之前、之后还是出现进度后，以及屏幕原文。
- 如已有 `KB*.CAM`，检查其版本字段并核对生成时间。不要为了取证触发未验证的工程写入、日志导入或重置操作。
- 网友桥接包的原文件或明确来源，及确认适用机型；比对包头、CPU 代码、运行版本来源和校验，不直接刷写未知包。

上述为初始调查阶段。当时尚未修改平台导出策略；后续已增加独立桥接测试导出，见文末。全程未发布、未向 SD 写固件，未进行实机刷写。

## Ricoh-GRMod 参考与判断修正

参考仓库：[Maxwooow/Ricoh-GRMod](https://github.com/Maxwooow/Ricoh-GRMod)，读取提交 `16327dbe7bf9e5fd5e4db99ef47237b2240e5487`。源码 `core/src/fw/bridge.ts`、`bridge-data.ts` 给出官方 GR IV 1.11 到桥接版本 1.12.10.7 的可逆差分及输出 SHA；[v0.6.1 发布说明](https://github.com/Maxwooow/Ricoh-GRMod/releases/tag/v0.6.1) 称该文件已实机验证。这是作者对 GR IV 的验证声明，不是 GR III 的硬件证据。

本地从已持有的官方 GR IV BIN 应用其公开差分，在内存中还原桥接文件，确认大小 `38752180`、SHA-256 `ecdfc3034441d9f1cc4684955de546a6d3d4bb495470a48fb8e1d84971659adb`。再分别解码官方/桥接载荷，逐字节比对，结果存于 `builds/gr3-bridge-research/gr4-reference-diff.json`。桥接整包未输出到 SD 或项目发布目录。

核心补丁位于 GR IV RTOS `5383188c`：原 `e82c09e3`（`movw r2,#9ce8`，低版本拒绝日志入口）改为 `dcffffea`（`b 53831804`，返回成功）。其余差异包含版本副本和校验。不能将这些地址用于 GR III。

GR III 的对应拒绝入口是 `536285dc`：原 `042803e3`（`movw r2,#3804`）可用 `e6ffffea`（`b 5362857c`）在内存模拟中改道到成功返回。此补丁不会在第一包安装前执行；第一包依赖提高包版本通过旧更新器，第二包才利用桥接更新器的较低版本准入。

新增可复现研究探针 `scripts/probe_gr3_bridge_gate.py`，不生成更新 BIN。50 个 ARM 场景通过：

- 36 个原厂/补丁对照，覆盖类型 0、1、2、3、4、6 和 DSP/CPU 分别较高的情况。
- 6 个 CPU 包装对照：正确载荷通过，校验损坏和项目号错误拒绝。
- 2 个空候选拒绝对照。
- 6 个第一包边界场景：原厂门禁、当前 DSP/CPU 均为 `2.10.255.255`、候选均为研究值 `2.11.21.27`，六种类型均通过。

研究值 `2.11.21.27` 不是官方发布版本，不是已观察到的周年版本。该结果证明的是公共更新器的两个局部阶段，未验证第一包整体解析、所有版本副本、其他机型、服务代码兼容性、实际闪存写入、掉电恢复或硬件回刷。

上一轮将“CPU 运行报号恢复”为桥接重点过于狭窄。此参考表明，可以保留桥接较高运行号，改由桥接更新器允许第二次降级，不必先修改 Renesas RX 运行版本 getter。后续实现应围绕独立的两阶段桥接流程，不能将 DSP-only 开关重新标记为通用解锁。

## 完整候选与平台接入（最终采用 2.10.22.27）

用户要求保留 2.10，只增加第三段。最终构建器固定包版本 **2.10.22.27**，不是前面研究阶段的 2.11，也不是中途讨论的 2.10.21.28。仅覆盖公共门禁下当前 DSP/CPU 均不高于 2.10.22.27 的情况；未知周年组件更高时第一包仍会拒绝。

实现：

- `node/gr3-bridge.mjs`：精确官方 GR III SHA 锁定；构建与独立重新解码审计；压缩帧复用额外核对 8191 字节回溯历史；不接受 GR IIIx 或已有修改包作为基线。
- 仅修改外层 DSP `38`、CPU `50`，RTOS `2038`，CPU `90`，GR III 更新器 `536285dc` 和 CPU/decoded/容器校验。其余所有逻辑字节、分区头、引导载荷均必须不变。
- `POST /api/projects/{id}/bridge/prepare` 和 `/bridge/export`：沿用 token/Origin 校验，限制请求体；导出必须绑定预检 plan_id 并确认实验说明；不提供任意地址或任意版本写入。
- 主工作台“保存固件”页新增独立桥接入口，GR IIIx 隐藏；原 DSP-only 功能改名“单包版本适配”，不与桥接混用。ZIP 分开 stage-1-bridge 与 stage-2-official，附 README、receipt、SHA256SUMS。
- `scripts/build_gr3_bridge.mjs` 可复现构建，文件以独占方式写入，已有文件不覆盖。

实际候选：`builds/gr3-bridge-2.10.22.27/stage-1-bridge/fwdc239b.bin`，30,446,032 字节，SHA-256 `e49cce2858e52b200b9d451100d13f3ff7ea51f30b66503cb26d503851431955`。第二阶段包含精确官方包 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`。

最终 decoded 实际变化 11 字节：RTOS 包头第三段 1 字节、更新器分支 4 字节、CPU 补数 1 字节、CPU 包头第三段 1 字节、decoded 补数 4 字节。外层两个第三段与容器校验另计。未修改任何 RX 指令。

注意：CPU 回复的第三段固定为 21，读取头部的是第二、第四段；本候选只提高第三段，所以公共代码路径预测 DSP 和 CPU 运行号均保持 **2.10.21.27**。这是静态来源结论，不是周年实测。包头版本和菜单版本不能混为一谈。

验证：

- 构建/篡改拒绝与 HTTP 集成定向测试通过；真实 HTTP 返回 ZIP，两阶段文件和 receipt 可读，未经鉴权和错误 Origin 拒绝。
- `scripts/verify_gr3_bridge_candidate.py <最终BIN>` 实际读取最终候选的 RTOS/CPU，35 个 ARM 场景通过（含真实 DSP 初始化与版本模型 getter）。包括第一包对 2.10.21.255 与相等值的准入、对更高版本的拒绝；使用最终更新器对官方第二包的准入；最终 CPU 正确载荷/坏校验/错误项目号；空候选拒绝。当前版本 getter 仍被替代，没有模拟 Flash 控制器或完整更新状态机。
- Python zipfile 独立验证 ZIP CRC、SHA256SUMS 全部成员及第二阶段官方原字节一致。
- 本地真实浏览器已走通官方来源导入、桥接预检、确认说明、发起 ZIP 下载；截图为 `builds/gr3-bridge-2.10.22.27/platform-bridge.png`。

没有实机刷写，没有声称周年机已解决，没有发布线上服务。测试包可供明确知晓实验状态的用户进行实机验证。

### 最终回归结果与共用工作区限制

桥接专项最终复跑 3/3 通过；旧版本适配及共用 ZIP 相关定向测试 18/18 通过；独立审查未发现 P1/P2。`git diff --check` 通过。

全量 `npm test -- --test-concurrency=1` 已结束：247 项，231 通过、11 失败、1 超时取消、4 跳过，耗时 737.7 秒，**不是全绿**。期间工作区存在另一组并发 GR IV 原生库/共用前端改动，已保留；本任务没有改动其源码、测试或生成契约来掩盖失败。

未通过项目逐项记录：

- not ok 59 - all eight extension combinations preserve selected/unselected bytes in debug and release
- not ok 108 - native RAW NR export independently reads back off and threshold together with old extensions
- not ok 120 - web debug export uses the running Node when the service PATH contains no node
- not ok 121 - original M10V web workflow binds all five slots and timestamp into audited firmware
- not ok 124 - stock overlay composes onto a freshly audited native candidate without shifting sections
- not ok 138 - independent settings audit binds owned controllers, original fallback and root captions
- not ok 229 - shared import derives the model from official identity and keeps local choice separate
- not ok 230 - the same import handler accepts both models and updates target labels from official identity
- not ok 231 - local sample selection does not override the loaded target until import completes
- not ok 232 - unsupported identity leaves the previous verified source and configuration intact
- not ok 234 - GR IIIx uses the shared stock capability endpoint
- not ok 235 - GR IIIx imaging tab can select the custom workflow after removing native film

原因分类：组合矩阵超过 180 秒；RAW NR 组合审计报告编译后 halation_core.c 已改变；4 个原生构建用例因 SD recipe contract 过期而失败；6 个共用工作台用例受到 GR IV 改动影响，其中测试抽取环境缺少 gr4Workbench，另有旧字符串断言失效。完整错误保存在 builds/gr3-bridge-2.10.22.27/full-node-tests.log。桥接路径不调用原生库编译或 SD recipe contract 生成，最终三项专项测试在这些共用变动后再次通过。

组合矩阵单独复跑仍超过原有 180 秒上限，取消（进程总耗时 205.3 秒），记录为 `matrix-retry.log`；没有提高测试时限或将取消标为通过。复跑期间 SD recipe contract 检查已恢复通过，但未重新运行整套全量测试，因此不撤销上述全量失败记录。

交付 ZIP SHA-256：`735d2361c59085ec72de8683c3dbbeb95aa5611a0b01b19dbcf02a88bba49cbd`。

## 用户实机确认后的正式化

用户于 2026-10-18 明确反馈本次方案“测试通过”，并要求完整接入 m10v。已按此更新正式入口、使用说明、套件名、回执实机来源及更新日志，并收起 GR III 旧单包适配；已测 BIN 不变。后续当前状态和验证边界以 [实机反馈与正式化记录](../testing/gr3-bridge-hardware-2026-10-18.md) 为准，前述“尚未实机验证”是反馈前的历史状态。

## 失败后的解析路径追踪

外层解析 `5362bd40` 检查项目、双标记、类型和容器补数；`5362bf48` 调用 `536b5c5c → 537f9460 → 53858130`。最后一处把输入、输出与长度写到 `0x1b030000` 硬件寄存器，不能以 JS 解码或门禁 Unicorn 测试替代实际硬件验收。官方包本身已有 729 个 literal 帧，因此不能仅凭新包含 literal 帧就断定格式不支持。

# M10V 既有功能保护基线

核查日期 2026-10-21，项目 `/Users/zhaoo/Desktop/code/zhaoo/m10v`，HEAD `c988e7a907d22fa68a8412a656f3c8b0bb40ff1a` **加未提交/未跟踪改动**。HEAD 不代表完整现状。文件指纹见 [m10v-source-baseline.json](m10v-source-baseline.json)。实施前重新读取实际代码与 git status；指纹变化用于发现资料过时，不用于阻止用户的新迭代或还原工作区。

优先级：用户本次明确需求 > 当前源码和对应测试/最新设备证据 > 此快照 > 旧 README/研究笔记。不要为“保护现有功能”固化已知 bug，也不把尚未实现的承诺当作现有功能。

## 与 GRKit 的差异及保真要求

| 能力 | M10V 当前实现/契约 | 对照 GRKit 时的要求 |
| --- | --- | --- |
| 胶卷目录 | 78 个内建历史 ID，当前 UI 过滤后 46 款（id>=33），五活动槽；tone12/18/19/20/21 | GRKit 20 effects 是其产品限制，不得截断/重排目录，不能把内部78与可选46混成一个数量 |
| 胶卷数值/图标 | 共享目录、名称、40×40像素；历史编号和映射稳定 | 名称/图标修改不连带重拟合 LUT；保持网页/机内 ID 和图标一致 |
| 质感与特种胶卷 | 各槽独立 grain/halo/grainSize/leak/filmExposure；800T、5207、蓝凤凰、RED及新胶卷有专属路径 | 不能用 GRKit 三档原厂 grain 替代全部质感；按胶卷能力显示参数，保留关闭及无效输入边界 |
| 柔光/HDF | 旧 soft 字段为兼容保留，当前 normalizer 将 soft 归零；独立 digital HDF 是不同功能，初始强度0 | 旧 README“柔光可调”有过时内容，不能重新启用旧 soft，也不能因 HDF=0 删除菜单/模块 |
| 蓝凤凰/RED EI | 67号蓝凤凰仅0..1；68号RED为0..2；其他内建卷不接受曝光枚举 | 保留具体 EI 映射、切卷/reset 规则；不能把曝光作为通用0..2参数套所有胶卷 |
| 状态存储 | 104-byte state、magic、version4、sequence、CRC；当前 M10V5A/B.bin，兼容历史多代记录 | GRKit STATE.TXT 不能无迁移替换；保留已有记录优先、无记录才编译默认值、坏新页回退和写失败原子性 |
| 自定义SD胶卷 | FILMS.M10，4096头/12288记录、stable ID、CRC和renderer合同；部分custom LUT有双bank | 不是 GRKit GRF；不能改扩展名冒充兼容。区分内建闭合renderer记录和custom LUT路径，不能用旧笔记否认后来的custom实现 |
| 换卷 | 浏览不激活/不保存；确认复核ID→记录验证→保存回读→更新目标槽；不影响其他槽 | 不用“高亮即永久选择”替换现有交互；保留页/焦点/取消及失败提示 |
| 菜单/资源 | settings/controller/view、原生TopMenu所有权、私有route、动态卡片RAM和原厂资源回退 | GRKit 第六ADJ不能自动替代全部入口。ROM/追加RTOS只读，动态descriptor放所属页RAM；先销毁控件再撤指针/释放 |
| 拍摄选择 | 每张冻结独立快照；前端property选择优先并校验，后端/帧tone回退；已排队照片不被新UI选择改写 | 不能改为全局last-selected；保留首张换卷修复及原厂三bank逻辑 |
| 成像 | 原生完成mask需绑定recipe/frame；未完成阶段CPU回退；关闭效果保持基底/stride padding | 不能因为安装Hook就认定ISP已处理并跳过CPU；去重处理主图/缩略图别名，保留内存/预算/失败回退 |
| RAW安全 | RAW-only/CFA alias拒绝像素访问；LIVE/RELEASED基于独立归属token，释放后禁止读RAW | 不以日志或pool free单点代替完整认证；原厂RAW/JPEG/回放/快门路径不能因迁移破坏 |
| 水印 | 日期/日期时间、4格式、4角、4色、独立胶卷名；大号斜体分段、双行右对齐、小图缩放 | 不能直接用GRKit固定日期样式覆盖；用本张照片时钟，时钟无效只跳印字，不丢胶卷效果 |
| A/B候选 | 菜单/ADJ影像控制DISP设置，取景DISP正式tone setter；原厂12项含黑白+五槽；Fn原功能；配对持久、重启关闭 | 不改成Fn开关、预览替代正式setter、截成仅五胶卷；但当前设备无反应仍未闭环，不能宣称已修复 |
| 组合工具 | aspect/level/negativeGrain/RAW NR；GR3 HDF feature与强度分开；原厂工具与胶卷库方案有组合限制 | 不静默丢选项；不支持组合应明确拒绝；GRKit Framing不等于覆盖全部既有工具 |
| 机型 | III/IIIx/IV各有构建/ABI与特性门禁；II仅只读固件检查 | IIIx共用GRKit runtime不代表M10V全部feature共用；HDF/live_color门禁、GR4独立适配、II导出禁用保留 |
| 构建与诊断 | 官方哈希/preimage、source/config fingerprint、receipt、最终BIN回读、debug默认关闭、CRC环形日志 | 不用GRKit INSTALL.OK替代最终固件/功能检查；按候选build_id核对日志，环形尾窗不证明完整事件历史 |
| 网页编辑 | 草稿、五槽同步、搜索筛选、撤销重做、取消构建、机型切换与配置绑定、导出确认 | 改加载方式时也要覆盖网页/服务入口，不能只验证C和CLI |

## 三处易被历史资料误导

1. `README.md` 写 Standard 取景、部分旧文档写实时色彩，源码 `prepareNative` 又有 `live_color` 和pipeline选择。分开记录标志、实际执行、用户看到的效果；本轮不得顺手改变取景或承诺GRKit预览与M10V成片一致。
2. SD库旧研究只覆盖33卷闭合记录，当前源码存在custom LUT与更多ID；查 `m10v_sd_camera.c`、`m10v_library_select_custom` 及对应测试，不能用旧规格删除后加能力。
3. A/B早期“通过”指离线。最新 `docs/testing/gr3-ab-controller-fix-20261021.md` 明示用户仍无反应，`gr3-ab-log-audit-20261021.md` 只确认保留窗口内release，未确认按下阻断根因。禁止把release0x36直接改成点击触发，也禁止删除去重、Fn透传、RAW开发隔离来让测试变绿。

## 修改前/后交付物

先列本次功能影响矩阵：功能、旧行为、预期行为、源码/测试入口、设备证据、迁移策略。需求之外各行保持不变；确需改变时说明具体原因和影响，按用户范围推进。

完成时提供 changed/preserved/known-broken/untested 四类结果，不把“代码存在”“离线通过”“用户验收”“已发布”混为一谈。对应测试用例的行为是合同，不能删断言、改期望或扩大stub来掩盖回归。

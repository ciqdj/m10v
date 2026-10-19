# GR III 空间效果原厂 IIP 可行性核对（2026-10-18）

本次只读研究针对 GR III 2.10 的空间效果、工作内存及 IIP 原语。没有改生产代码、模型、原厂二进制或生成固件。目标是判断怎样保留漏光、光晕、颗粒并移出目前的整帧标量 CPU 路径；没有把已有原厂效果当作当前效果的等价替代。

## 结论

1. **原厂 Granulation 是 ARM 控制、NEON 生成随机工作面、IIP Loader → LUT → Blend → Store 合成的混合路径。** `0x5367ad3c` 本身是可执行 ARM 函数；称它为 “DSP-only” 或 “纯 CPU 颗粒” 都不准确。没有看到该路径提交外部 DSP 任务。
2. **有确凿的原厂空间效果加速基础。** Granulation 证明 IIP 可把一张独立空间平面与原图结合。IIP 的 LUT、Blend、GPC、SPF 都有真实控制类/驱动类和原厂调用链，不只是字符串线索。
3. **颗粒的原厂工作面不是零成本。** 官方查询分支实际返回 `align16(width) * height` 字节：6000×4000 为 **24,000,000 字节**。这不在当前 M10V 589,824 字节 scratch 限额内；迁移应接入原厂阶段的工作区规划与生命周期，不能在现有拍后回调直接额外申请后就假定安全。
4. 漏光的坐标场 + Blend、亮部遮罩 + SPF/缩放 + Blend 光晕是有证据支持的研究方向；**当前还不能证明能逐字节重现现有算法，或承诺秒回放**。原厂颗粒的三档、8 位输出与现有多尺度/彩色颗粒也尚未等价。
5. 本次证实的是一维 LUT 的六个数据窗口、预运算与组合原语。**没有证实一条可直接执行当前 15³ tetrahedral 颜色 LUT 的原厂硬件路线，也没有证实整芯片不存在 3D LUT 硬件。** 不能用缺少字符串推出后一个结论。

## 固定来源与证据

- RTOS：`builds/gr3-extension-validation/official-rtos.bin`
- 长度：17,520,064 字节；虚拟基址 `0x53000000`。
- SHA-256：`8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`。
- 证据目录：`builds/gr3-isp-research/spatial/`（ignored），内含按入口地址命名的 Capstone ARM 反汇编、`rtti.json`、`granulation-tables.json`、`probe_granulation_query.py` 与执行结果 `granulation-query.json`。
- 跨仓参考：`../gr3-film-mods/FINDINGS.md` §47/48 记录了实际机身上的 stage gate 与 grain 可见性。§45/46 的 DSP 归因、文件前部的 “No 3D LUT hardware anywhere” 不能作为本次结论。

以下地址都来自上述固定 RTOS。线性反汇编文件会包含邻接函数及 literal pool；不能把 literal pool 的伪指令解码当作代码。

## Granulation：参数、执行单元和内存

### 上游不是只写 metadata

`0x53503054` 读取 shooting information 的 `+0x793..+0x796`，写入效果参数块：

| 参数块 | 原厂含义 / 本次确认范围 |
| --- | --- |
| `+0` signed16 | Shading 参数 |
| `+2` signed16 | Clarity 参数 |
| `+4` signed16 | Grain，shooting 值 1/2/3 反向映射为处理值 3/2/1 |
| `+6` signed16 | SI `+0x796` 对应处理参数 |
| `+8` float | 该阶段比例参数；不能当成颜色/颗粒任意强度接口 |

`0x53680dc0` 是多效果阶段。`0x53680f2c` 在工作量查询路径调用 `0x5367ad3c`，`0x5368104c` 在实际执行路径再次调用它。阶段是否进得去仍由 processing plan gate 决定；UI 上出现 Grain 或文件记录了 Grain 都不能单独证明像素经过这一阶段。

### `0x5367ad3c` 的实际链

| 位置 | 可直接验证的行为 |
| --- | --- |
| `0x5367ad58..0x5367adc0` | 从图像描述符 `+0x10/+0x12` 取宽高；工作指针和宽均向 16 字节对齐；计算工作容量。 |
| `0x5367add0..0x5367adfc` | 工作指针为 0 时只查询所需字节，返回 1；不进行图像处理。 |
| `0x5367ae14` | 调用 `0x5368a92c(work, aligned_width * height)` 填满随机工作面。 |
| `0x5367ae24` | 调用缓存维护 facade `0x536bbcac`，后者跳转 `0x5383c834`，并非 DSP 提交。 |
| `0x5367ae28..0x5367ae3c` | 内部颗粒值 1/2/3 选择振幅 `0x100/0x80/0x40`。 |
| `0x5367ae40..0x5367af30` | CPU 复制/生成三张 256 项表；输入 ROM 表为 signed16，依颗粒档位缩放。 |
| `0x5367b010, 0x5367b040` | 两次构造 `LoaderControl`，入口 `0x536789f0`，分别读原图与随机工作面。 |
| `0x5367b070` | 构造 `LutControl`，入口 `0x53679180`。RTTI 名为 `10LutControl`。 |
| `0x5367b144` | 构造 `BlendControl`，入口 `0x53674f54`。 |
| `0x5367b15c` | 构造 `StoreControl`，入口 `0x5368c3d8`。 |
| `0x5367b308..0x5367b404` | 注册输入/输出图像、连接各 Control、安装表，调用 `0x5376cd10` 组装 IIP composite。 |
| `0x5367b410` | 调用 `0x5368a510(context, 0x400)` 等待事件；该函数进入原厂事件等待接口，带 timeout/error 分支。不能假定为同步零延迟寄存器操作。 |
| `0x5367b418..0x5367b4ec` | 清理 composite、control、描述符及表。 |

RTTI 是从构造函数所写 vtable、vtable[-1] 的 typeinfo、typeinfo 名称指针逐级解析得到；不是按函数附近字符串猜测。映射保存在 `rtti.json`。

### NEON 与 CPU 分工

`0x5368a92c` 先通过时间/随机数服务初始化种子，随后：

- `0x5368a9b0`：`vld1.32 {d16,d17}`。
- `0x5368a9d0..0x5368aa04`：`q8..q13` 上进行 `<<11`、`>>19`、`>>8`、XOR 与状态交换；每次 `vst1.32 {d20,d21}` 写 16 字节，字节计数减 16。
- 这是实在的 ARM NEON 随机面生成循环；不是仅用 VFP 搬运零常量的构造函数。
- LUT 缩放仍是 CPU 标量的 256 项循环；图像合成通过已识别的 IIP 配置/事件路径进行。

因此即使全面接入原厂路径，24MP 工作面生成与带宽仍存在。按可见的原图、随机面、输出三路，至少有整帧级数据流量；不能只拿 IIP 运算吞吐推算整张照片延迟。

### 原厂缓冲容量与精度

安全 ARM 探针仅执行 `work_pointer=0` 的官方容量查询，不模拟 IIP、不读写真实相机。Unicorn 在 sandbox 外运行以避开本机已知的 SIGILL 限制：

```text
2×1        ->         16 bytes, return 1
6000×4000  -> 24,000,000 bytes, return 1
3360×2240  ->  7,526,400 bytes, return 1
6144×4096  -> 25,165,824 bytes, return 1
```

入口直接栈预留为 `0x640 + 0x0c`，另保存 11 个寄存器，共约 1,656 字节；不包括下游调用栈。可见的直接 heap 申请还包含两张 `0x200` 表、两个 `0x50` 描述符、`0x10` rectangle、两个 `0xc0` loader、`0x180` LUT control、`0x100` blend、`0x1c0` store、`0x120` composite，合计 2,960 字节；**这不是整个 IIP 服务的总内存上界**。

ROM 表 `0x538f19d4` 是 256 个 signed16，范围 3..258；`0x538f1bd4` 是 -3..252；`0x538f1dd4` 范围 0..255。前两张由 1、1/2、1/4 振幅得到围绕 identity 的扰动，第三张参与最终映射。Store 配置处明确使用 `0xff` 上限。当前可证的是这条原厂颗粒路线的 256 项、signed16 表与 8 位目标输出；不能据此宣布整个 IIP 只有 8 位。

颗粒路径读取图像描述符 `+4` 指向的平面；可见代码没有对第二 chroma 平面执行当前 M10V 那样的独立随机 RGB 扰动。因此原厂颗粒能作为快速实现基础，不能未经图像对照就认定等价于当前 `grain_size=0..2` 和彩色颗粒模型。

## LUT：已证实的表规模与不能越过的结论

`LutUnit` 服务初始化入口 `0x53779744`：

- 分配 `0x1c` 的寄存器服务，调用 `0x53778030`，其寄存器基址写为 `0x28880000`，数据 aperture 基址写为 `0x29820000`。
- 分配 `0xc4`，调用 `0x5377c150`：RTTI 为 **UnitInformationTableDriver**；它不是一段逐像素 LUT 算法。
- 分配 `0x88`，调用 `0x53779d78`：PixelFormatTableDriver。
- `0x54035898` 是 `7LutUnit` vtable，实际只有两个析构条目；邻接数据不是更多虚方法。

数据地址 getters `0x5377959c..0x5377960c` 暴露：

| 表 | 数据 aperture 相对地址 | 窗口规模可证范围 |
| --- | --- | --- |
| A / B / C | `0x0000 / 0x2000 / 0x4000` | 与 D/E/F 交错的 `0x1000` 地址窗口 |
| D / E / F | `0x1000 / 0x3000 / 0x5000` | 各 `0x1000`；按 loader 的 32 位写入，窗口容纳 1024 个 word 地址 |
| pre 0..3 | `0x10000 / 0x10400 / 0x10800 / 0x10c00` | 各 `0x400` 地址窗口，256 个 word 地址 |

这是**暴露的数据窗口容量**，不是已经验证的“每张逻辑曲线最大 1024 个独立采样点”。`0x5376c368` 可根据模式把单表交错分到两个窗口；模式、precalc、bank 选择和 address shift 会影响有效表规模。

`0x5376c314` 的原厂装表循环使用 `ldrsh` 从 signed16 数组取样、`str` 按 4 字节写数据 aperture，可设置源步长。这证明 16 位 signed 表值被交给硬件，**不证明硬件 32 位像素精度**。LutControl 默认裁剪上下界包含 `0x3fff/0x4000`；像素格式 driver 的若干范围/offset 字段为 18/15/14 bit，也证明该接口远不只 RGB8，但本次没有解码所有数值格式、饱和与舍入规则。

六张 LUT A..F 与各自 PRECAL/控制寄存器、参数化 GPC 并不等同于现有 15³ RGB tetrahedral 查询。必须找到或构造多通道索引、取顶点及插值的完整链，再评估精度；本次没有完成这一步。相反，也不能从六张一维表推导全芯片没有别的 3D 加速单元。

## 漏光、光晕与各硬件原语

| 原语 | 直接证据 | 能支持的迁移方向 | 尚不能承诺 |
| --- | --- | --- | --- |
| Loader / Store | Granulation 的真实调用及格式/stride 描述符 | 原图、随机面、坐标遮罩、多次中间结果的流式读写 | 任意描述符格式、原地 alias、RAW 或 preview buffer 可安全复用 |
| LUT | 上述六个表窗口、precalc、signed16 装表 | 亮部阈值/非线性权重，颗粒分布/强度，分通道曲线 | 当前 15³ 颜色变换逐字节等价，任意维 LUT |
| Blend | `BlendControl`、`BlendUnit`、ALPHACTL/WADDCTL/DIVCTL/MSKCTL；Granulation 实际使用 | 把空间漏光面/光晕面与原图结合，按通道赋色 | 现有 `light*transmission*(255-rgb)`、保护项和整数舍入可在一趟内精确表达 |
| GPC | `GpcControl`、`GeneralPurposeOperationUnitService`、`GeneralPurposeConfigUnit`；输入选择、移位、round rule、alpha 和输出控制 setters | 计算阈值、差、权重、混合前后的分通道算术 | 指令集是通用 shader；一次能容纳所有现有效果；未量化的累积精度/吞吐 |
| SPF | `SpatialFilterUnitService`、`SpfControl`、`SpatialFilterUnit`；`0x53772888` 申请/配置 `0x284` 字节寄存器映像，`0x53772a38` 配置驱动 | 对亮部遮罩作局部空间滤波，再叠加；可能作为多尺度光晕的一部分 | 任意大半径卷积、现有多次 distance=1/2 blur 的精确替代、当前 broad/fine 光晕无需多趟 |

SPF 驱动可见 `SPF_MD`、每通道 `FLTW/VTH/CORE/CLP/EOADD`、`EP_GA/OFS/BD`、`ADAPT_K/TH/DIV` 等控制，相关 setter 还包含 11/15 位字段。这证明是可配置空间处理单元，但本次没有把它的 kernel、边界扩展和所有模式解码成数学算子。不能拿原厂 Clarity 或 Soft 功能名证明它能原样实现当前光晕。

漏光只依赖坐标、seed 和参数，可在较小预计算面/原厂 loader 支持的输入上准备空间场，再让 IIP 做整帧算术。这条方向比 CPU 对每个像素重新计算漏光更有依据；但必须实际验证低分辨率场的采样/插值是否等价，不能借迁移悄悄降低空间精度。

光晕仍需要先从原图提取亮部/红敏能量、邻域扩散、受保护合成。LUT/GPC/Blend 提供组成材料；扩散半径、边缘、软光与高光保护关系须由 SPF 或原厂缩放/多趟计划实现并验证。当前“保留所有效果、画质不退、秒回放”的联合目标尚未被这些原语的存在本身证明。

## 下一步必须实机闭环的空缺

1. **生命周期与资源**：在原厂 processing plan、IIP scheduler/互斥、DMA/cache 与 buffer owner 范围内提交效果；验证工作区查询和上游容量预留，不能继续在编码前临时新建 24MB 工作面并假设无内存压力。
2. **精度与颜色**：确认每个节点前后的位深、range、YCbCr/RGB 域、舍入/饱和、chroma 采样；对新旧管线使用相同 RAW/曝光，以完整 JPEG/DNG 和裁切对比，不只看 MakerNote 或采样 hash。
3. **颗粒等价性**：三档幅度、空间尺寸、亮度依赖、彩色分量与 seed 时机都需定义；若原厂粒子与当前效果不同，应明确差异，不能按“原厂”之名默默删掉效果。
4. **光晕数学契约**：用点光、细线、饱和红光、白色核心、边界点光和均匀暗场测 SPF/缩放边界、响应半径与 fine fringe；不接受通过减分辨率、减半径、关效果换速度。
5. **完整时延**：分别测原厂效果阶段、JPEG encoder、SD 写入和回放可用事件；profile adapter 内的毫秒不能代替拍摄到回放的总时延。记录高熵场景、RAW+JPEG 和连拍最坏情况、内存峰值、失败后的原厂接续。
6. **硬件验证边界**：本次 Unicorn 只跑了 scalar 查询。NEON 填面与 IIP 执行链由静态机器码证明，尚未在本研究中完成真实 IIP 输出实验；没有产生可刷机候选。

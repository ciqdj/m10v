# GR III 800T 平滑高光红晕修复

用户的新实拍包含大片冷白顶灯扩散，外围缺少红晕。本次定位并修复原生强档算法，色彩表和拍摄适配器隔离规则保持原状。附件不能证明当前机身固件散列或强弱档，因此这是已复现的算法缺陷，不能据此声称实机hook已执行。

## 根因

附件转近似全范围YCbCr422后为2498×1662，Y最大249。Y>216有198780个像素，Y>=248仅26个。旧强档要求源比四邻域平均亮度高64级，Y>=248时也要求16级；只有123个像素满足。大片平滑灯光被拒绝，剩余源集中于灯座和缝隙等边缘。

源阈值216同时用于接收像素保护，禁止Y>=216区域着色。因此高光压缩后的235～247区域既难成为源，也不能接收扩散。峰值247的平滑高斯灯回归在旧核心上得到外围Cr增量0；新版测试要求外围强度及四向包围关系。

## 修改与边界

- 局部对比不足64时，强档改用近白软源：Y>235时`(Y-235)*12`，最大240；235及以下平坦表面仍无源。
- 强档白芯保护改为248；接收增益`min(4*(248-meanY),255)`，近白逐渐减弱，暗部增益封顶。共享色度的一对像素任一达到248即保护。
- 强档二项式扩散3→5轮；工作网格和三缓冲294912字节上限不变。
- 弱档公式不变，附件输出前后SHA256均为`f12503fddeaf2193acde6bbdac741b4fe2ac152cb27e8292507acbe40e9309c9`；独立审查另比较10组随机尺寸、padding和色度顺序，弱档逐字节一致。
- ARM编译增加`-fomit-frame-pointer`，核心2372字节，固定2376字节区剩4字节。10个适配器各1636字节，小于1656字节预留区。源码和代码锁已同步。

附件旧强档修改6211个色度对，累计Cr增量69381；新强档修改109520个色度对，累计Cr增量1843314。它们是算法差值，不是胶卷准确性评分。预览运行实际C核心并保留输入色彩，没有再次叠加800T色彩表；RGB↔YCbCr422和相机ISP有差别。

本地复现位于`builds/gr3-800t-diffuse-fix/`：`before-2.png`、`after-2.png`、`probe.py`、`input-ycc.npz`、`photo-metrics.jsonl`。脚本引用本次临时附件路径，用户原图不加入公开仓库。

## 联网依据

[CineStill官方](https://help.cinestillfilm.com/hc/en-us/articles/360029185291-What-is-Halation)说明背面反射产生高光溢光。[Dehancer Halation](https://www.dehancer.com/learn/article/halation)把光源限制、背景显现、扩散和增益分开，并说明冷色背景压低红晕可见度。

[Dehancer官方Quick Guide](https://cdn-files.dehancer.com/ZkkxCyol0Zci9Q06_DehancerOFXPluginQuickGuide.pdf)指出LUT导出不包括Halation等空间效果。[PictureFX 800T v2](https://marcrphoto.wordpress.com/2025/02/28/picturefx-cinestill-800t-v2-0-lut/)用HALDCLUT转cube，适合色彩参考；本次未复制或打包该作者LUT。[Spektrafilm](https://github.com/andreavolpato/spektrafilm)提供逐通道Gaussian散射控制，本次仅参考空间处理的架构，没有移植其光谱模型。

LUT以单像素RGB决定输出，无法单独把灯光扩散到邻近像素。固件继续采用色彩表加独立空间内核。

## 验证

44项相关原生/ARM测试全部通过，包括平滑灯、两档与两种顺序逐像素一致、原厂分配路径、最终trampoline、寄存器/APSR/SP、缓存范围、CFA/元数据隔离和时间戳顺序。硬件缓存、ISP和JPEG编码器未仿真。

Node全量128项：127通过、1项既有Python备份兼容样本跳过。审计回归改为即时构建当前writer，避免历史ignored实验包与当前代码锁不同；仍验证writer和expectation同时同意的错误分支被独立accepted-plan审计拒绝。

Python全量68项：66通过，2项既有首页断言失败：`test_direct_file_open_keeps_styling_and_explains_server_requirement`及`test_page_exposes_actual_import_backup_and_locked_features`（`tests/test_workflow.py`期待单机型首页和相对CSS路径，当前已有页面为多机型选择页）。本次未修改首页或放宽断言。日志保存在本地构建目录，独立代码审查未发现P1/P2阻塞问题。

## 候选与实机验收

两份候选均基于锁定GR III Street Edition 2.10官方源，800T放在Bleach Bypass槽，强档；其余四槽使用现有实验构建默认胶片，不继承任意既有自定义包的其他功能。内部版本2.10，仅RTOS和ICONBIN改变，RTOS增长27200字节。构建独立回读和导出文件再次回读均检查完整代码字节与配置绑定。

| 文件（`builds/gr3-800t-diffuse-fix/`） | 字节数 | SHA256 |
| --- | ---: | --- |
| `fwdc239b-800t-red-halo.bin` | 31164344 | `f20a4962024de531be56d1f216a52084f1786ee4f89fa288abd8a2dcd3d6f82d` |
| `fwdc239b-800t-red-halo-timestamp.bin` | 31265532 | `2c7371351fc004c2e391bab4d85c958f6f73eeb1499f7698a6c1157677a3baa2` |

离线核验通过，尚未实机验证。选择机内800T分别以JPEG-only及RAW+JPEG复拍同灯和小点灯，记录保存耗时与稳定性；无高光场景作为对照。分别检查DNG的CFA数据与内嵌JPEG，不能用整份DNG哈希替代RAW隔离验收。弱档对平滑灯仍保持原外观。

局部亮度无法语义区分灯具、白墙或倒影。Y=236～247的平坦亮面也可能产生染色，本次不声称自动排除反射。新增两轮网格扩散的实机耗时仍需测量。宽广白色柔光的形态与清晰聚焦灯芯不同，本次解决平滑高光漏检，不声称等价于真实乳剂或完整线性光谱模拟。

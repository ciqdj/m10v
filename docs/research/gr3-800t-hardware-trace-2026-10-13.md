# 800T 实机失败复查与硬件诊断

> 本文记录第一版诊断包。随后用户交回了实际日志，确认第11步错误拒绝高地址RAW，已修正并生成新候选。最新结论和包散列见[实机RAW地址修复记录](gr3-800t-raw-bank-fix-2026-10-13.md)。下文的“尚未定位”是取得日志前的历史状态。

## 已确认的证据

用户实际刷入文件`/Users/zhaoo/Desktop/fwdc239b-2.bin`，SHA256为`f20a4962024de531be56d1f216a52084f1786ee4f89fa288abd8a2dcd3d6f82d`，确实是上一轮强档、无时间戳新版，不是旧包。

用户桌面的`00003958.JPG`及`00003958.DNG`属于同一次快门12617。DNG记录2026-10-13 22:00:28；相机RICOH GR III 2.10、1/6秒、ISO6400。ImageTone263被ExifTool解释为Bleach Bypass 2，对应800T替换的内部18槽。JPEG为6000×4000，有612810个Y>=216像素、188203个Y>=248像素，最大255。既有算法在这些高光上应有输出，因此不能继续以“高光不足”解释实机失败。

逐字节核验已刷入包及新原厂反汇编，未发现确定的失败guard。独立审查执行原厂module6 getter及消息存储，证明普通链直接传`recipe+9b8`；不是Clone，因此没有按猜测解除拓扑检查。现有模拟仍不能提供用户拍摄瞬间的实际地址、分配返回值和每条guard结果。

**当前仍未修复实机红晕失效，也没有确认具体运行时根因。** 上一轮离线图像增强不能证明相机执行内核。本轮交付硬件诊断候选，以取得缺失证据。

## S9参考文件

下载并检查[Zack公开S9/S5IIX CineStill800T](https://www.photosbyzack.com/luts)，文件链接为[33³ .cube](https://res.cloudinary.com/djdxy2rdp/raw/upload/v1783537169/CineStill_800T_jftcll.cube)。标题为Daylight、Like709；作者允许个人/商业使用，不允许作为自己的文件重分发。本地参考文件只保存在ignored构建目录，没有打包进固件。

灰轴输入0.875输出RGB约0.91372/0.89412/0.86667，0.9375输出0.97647/0.95294/0.92157。近白偏暖、暗部偏蓝；cube只有RGB→RGB映射，没有邻域卷积或模糊信息。网页的halation文案和样片不能单独证明机内空间扩散。用户所指具体S9案例尚未取得链接，继续保留参考差异，不能否定所有案例或将颜色红边冒称物理halation。

## 诊断实现

`native/gr3/halation_trace.c`使用锁定时间戳模块的原厂FileSystem ABI：`535847d8`取manager，manager+14取impl，vtable+1c打开、+28写入、+20关闭，第五参数位于栈。写模式0，沿用该模块实际ARM调用约定。C:是原厂调试文件目标（如`C:\BEPRCLAP.CSV`）；实际SD路径可见性仍待硬件验证。

`scripts/build_gr3_800t_trace.py`在现有adapter的16处return分别插入退出原因；正常尾部为100。**没有放宽任何guard，没有修改原生红晕公式。** 正常处理另外记录最多约16129个有效位置的处理前后Y/Cr求和、亮样本数、最大Y和内核返回值。采样增加能证明CPU改写发生；相等不能严格证明全图没有改写。

日志256字节，唯一文件`C:\M10V8.BIN`，每次拍摄覆盖本诊断文件。logger和采样只读图像/CFA/配置；文件API及实际SD控制器没有被模拟。打开失败跳过日志，写入失败仍关闭句柄。stack stats在logger返回之前保持有效。

新增logger位于540bc000..540bc340，adapter位于540bc400..540bcd10，原核心540bb6b8保持原状。追加tail24576→32768；wrapper的540bb008处BL改为eb0004fc，准确跳至540bc400。新代码在原厂0x54000000可执行identity section内，未修改映射权限。

机内名称改为**800T Trace**以便确认实际加载了诊断包。此包强档、无时间戳，其余槽使用原实验包默认配置，不能继承任意旧自定义包的其他功能。

## 候选与验证

候选`builds/gr3-800t-live-debug/fwdc239b-800t-trace.bin`，31172536字节，SHA256 `29c9e5bd7e29ecd9c60c09c7ea223db978ed335aabe28d68b5046e13844ea8c0`。状态`HARDWARE_TRACE_REQUIRED`，不标记为已修复或已实机验证。

50项相关原生/ARM测试通过。新增测试执行logger真实ARM字节（文件API明确stub），检查固定记录、正确路径/写标志/参数、打开失败、写失败后关闭、无配置或图像写入；traceadapter与原adapter在成功/错误tone/分配失败/CFA别名条件下图像和系统调用一致，日志状态正确。采样测试验证内核返回值和前后求和。

`scripts/audit_gr3_800t_trace.mjs`从原包、可信色彩模板、原核心锁及审查后的两段诊断机器码独立重建所有预期字节，不读取writer expectation；完整section、尾部、分支和散列核验通过。独立代码审查未发现P1/P2阻塞问题。硬件执行、SD文件系统及拍摄稳定性仍待验证。

## 取得下一步证据

刷入时使用相机要求的`fwdc239b.bin`文件名；确认机内名称800T Trace后，拍一张带灯的RAW+JPEG。把SD根目录`M10V8.BIN`和这次原始JPEG/DNG交回。若没有日志，也记录这一结果，不能将缺文件当作成功。

解码：`.venv/bin/python scripts/read_gr3_800t_trace.py /path/to/M10V8.BIN`。状态码映射记录在`builds/gr3-800t-live-debug/stages.json`。日志用于区分guard跳过、分配失败、内核成功但采样无明显改变、以及CPU已修改而输出未体现等情况；最后一种仍需进一步查缓存/JPEG消费路径，不能只用图像模拟证明。

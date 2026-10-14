# GR III 800T 描述符证据入口

精确固件、样本与原厂指令依据见 [2026-10-12 研究记录](gr3-800t-samples-2026-10-12.md)。生产检查入口为 `node/gr3-800t-evidence.mjs`，它核验完整官方身份、RTOS 散列、调用点、JPEG 类型 vtable/name、格式转换、地址计算、缓存区间和维护指令的前像。

复现命令：

```sh
.venv/bin/python scripts/analyze_gr3_800t_layout.py fwdc239b.bin
```

命令先使用 m10v 原包解码器校验精确身份，再执行原厂 ARM 地址计算和格式转换，并记录被模型替代的缓存调用。没有固件写入器。

本轮进一步检查了 `C:\YUV%dCb.raw` 等调试字符串：精确字符串地址未发现对齐指针或直接 MOVW/MOVT 引用，不能从其名字推出主图缓冲区的字节顺序。`ConvertYCbCrToRgb` 相关路径进入原厂硬件配置；当前 CPU 探查没有执行 ISP、缓存硬件或 JPEG 编码器，不能把软件 CBCR/CRCB 两种通过结果选一项当作相机事实。

低级格式 1/2 对应 422/420、观察的创建路径包含合并色度区，这些证据保持有效。但硬件消费者的分量顺序、编码、缓冲区所有权与全部 RAW/JPEG 分流仍未闭合。四项阻断的当前定义及实现范围见 [实施验证记录](../testing/gr3-800t.md)。

## 2026-10-13 闭合更新

原厂 CPU 填充与正式低描述符转换已证明 CbCr uint8/128；拍摄 planner、生产者等待、callback 和 JPEG 消费链已闭合到受限模式，运行时 CFA/元数据/scratch 守卫已实现。上述历史缺项不再阻断受限离线实验候选。见 [色度契约](gr3-800t-chroma-contract.md)、[捕获契约](gr3-800t-capture-contract.md) 和 [最终实施验证记录](../testing/gr3-800t.md)。硬件时序仍待实机，未将其标记已验证。

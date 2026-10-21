# Kodak Charmera Pixel Filter

2026-10-21。本轮实现是独立编写的高反差双色模拟，尚未获得原机同场景输入/输出或原厂算法，不能宣称逐像素或 100% 原机还原。

依据：

- [原机使用者的 12 种实拍对照](https://www.reddit.com/r/toycameras/comments/1nv3f2r/all_12_kodak_charmera_photo_looks_filters_frames/)区分普通 B&W 与 Yellow/Grey/Blue/Red Pixel Filter。
- [Charmera 模拟器](https://charmera.app/charmera-simulator/)列出四种 Pixel Filter。该网站自称匹配硬件，但未提供本轮可核实的标定证据，其脚本访问返回 403；未复制其代码，也不把其营销说法当作准确性证明。
- [GR III 改滤镜介绍](https://www.reddit.com/r/ricohGR/comments/1x4vqxs/gr_iii_firmware_mod_bake_your_own_look_into_the/)讨论 sensor matrix 与 look matrix 分离。[GR Mod 源码说明](https://github.com/Maxwooow/Ricoh-GRMod/blob/16327dbe7bf9e5fd5e4db99ef47237b2240e5487/README.md)展示矩阵/LUT、机内参数和 JPEG 空间处理是不同层。本轮复用 M10V 已有 JPEG 所有权/回退链路，不增固件地址 Hook，不以平滑 LUT 插值近似二值化。
- [Processing THRESHOLD](https://processing.org/reference/filter_)作为类似阈值模型的算法参考；不是 Charmera 原厂算法证据。

用户附件的最频繁非黑白像素是黄 RGB(249,211,78)、蓝(1,0,249)、红(253,1,0)。采用这些色值作为参考图对齐目标；截图压缩和色彩管理可能使其与原机 JPEG 不同。灰色没有附件样本，使用 RGB(224,224,224)，需原机样本校准。

模型：full-range Y >= 128 映射至单色亮部，否则黑。网页从 RGB 以整数 77/150/29 得 Y；相机使用已有 Y 平面。CbCr422 对相邻两个像素共享色度，混合边缘会有原生采样误差，所以网页 RGB 与 JPEG 不宣称逐像素一致。默认关闭颗粒和漏光，用户仍可自行调节；时间水印/HDF/原厂上游处理会改变最终外观。

兼容性：历史内建 1..78 不变；79..288 自定义 LUT 不变；Charmera 使用 289。UI number 是目录排序后的 1..47，存档 film 是稳定身份，禁止混用。保留 state v4 的104字节格式，以 Charmera 槽位 effects 最后一个保留字节记录 0..3 颜色，其他卷该字节必须为0。SD记录仍使用现有格式和完整 SHA/CRC 验证；接受上一版合法内建摘要及自定义 renderer 合同，不放宽未知配方或保留字段校验。

影响矩阵：

| 功能 | 本轮行为 | 证据/边界 |
|---|---|---|
| 目录/编号 | 47款可选，连续UI序号，追加稳定ID289 | Node目录、SD与ARM菜单验证 |
| 影像控制 | 仅Charmera增加颜色；原厂详细页ID29，0红1黄2蓝3灰 | ARM回调、持久化、失败原子性 |
| 成像 | JPEG独立阈值/调色，不声明ISP已完成此色彩 | host/ARM、stride padding验证；无真机性能证据 |
| 旧胶卷/自定义LUT | ID/存档/银行/已知合法SD合同保留 | 既有回归及旧合同新测试 |
| A/B、HDF、水印、RAW | 沿用已有实现，候选显式保留HDF功能和组合工具 | 原有A/B实机无反应问题不在本轮宣称修复 |
| GR IV | 不提供Charmera，不改其既有46款 | 共享目录对GR IV过滤，拒绝导出未适配ID |

本轮正式发布依据用户明确授权执行，包含独立构建审计、自动化回归和线上校验。研究中的原机算法与标定范围保持上述事实边界。正式发布基于最新线上自定义胶卷修复，未包含本地 A/B 实验。

# M10V 精选：七款风格滤镜（2026-10-23）

本次增加稳定 ID 291–297，GR III / IIIx 网页精选与机内胶卷目录由 48 增至 55 款。历史内建 ID 1–78、自定义 ID 79–288、Charmera 289、Pixel World 290、五槽 104-byte v4 journal 均保留。GR IV 尚未提供这七款的资源适配，其目录与导出继续明确拒绝这些 ID。

## 参考资料和采用方式

| ID / 名称 | 可核验依据 | 实际采用 / 限制 |
|---|---|---|
| 291 Leica Monochrome | [Leica M11 Monochrom 官方](https://leica-camera.com/en-US/photography/cameras/m/m11-monochrom)说明无彩色滤镜传感器；[Street Monochrome 作者文档](https://github.com/sfi0zy/street-monochrome/tree/3f915315da4f43dd86af304273615b3a54939a94)明确 Eerie 有 Leica Monochrom 风格 | 采用 Ivan Bogachev 的 Eerie 64³ 社区 LUT，转为严格 R=G=B。CC BY 4.0，保留署名、许可和修改说明。不声称复制传感器光谱响应、分辨率、动态范围或高 ISO 表现 |
| 292 Lomography | [Color Negative 400 官方](https://www.lomography.com/magazine/244515-lomopedia-lomography-color-negative-400-iso-35mm)：ISO 400、鲜艳色彩与清晰感 | 未找到身份与许可均可核验的 CN400 同名 LUT；独立设计偏暖、较高饱和度与反差。审阅社区 X-Pro 200、Redscale 后未替用，因为它们不是 CN400 |
| 293 Polaroid | [现代彩色 i-Type 官方](https://www.polaroid.com/en_us/products/color-itype-instant-film)的复古与不确定性色彩；[社区 PX-680 LUT](https://github.com/YahiaAngelo/Film-Luts/blob/af957b631a304e6be94778b96cb3395de3438e9f/luts/instant_consumer/polaroid_px-680.cube) | PX-680 是历史彩色即显胶片的明确代理；不能当作现代 600 / i-Type 实测。保留暖黄、青色暗部与压缩反差；不额外添加白框。不使用 Polachrome、669 撕拉片或过期片冒充 |
| 294 Fujifilm Velvia 50 | [RVP50 官方数据表](https://asset.fujifilm.com/master/emea/files/2020-10/a71dda63e2662f012b3b74110794918a/films_velvia-50_datasheet_01.pdf)：ISO 50 日光彩色反转片、高饱和度、细颗粒、中性灰和深暗部；含特性曲线与光谱图 | 采用[同名 Velvia 50 社区 LUT](https://github.com/YahiaAngelo/Film-Luts/blob/af957b631a304e6be94778b96cb3395de3438e9f/luts/colorslide/fuji_velvia_50.cube)，不使用 Velvia 100。官方曲线仅作方向核查，未将显示 RGB 冒充曝光密度数据 |
| 295 Cyberpunk | 无唯一胶片或厂家参数标准；检索社区摄影 LUT 与游戏调色文档后，未找到适合直接复用且身份明确的摄影基准 | 独立制作青蓝暗部、洋红红色霓虹及较强反差。参数公开；普通日光照片不会凭空产生霓虹、光晕或夜景 |
| 296 Cyanotype | [Jacquard 蓝晒说明](https://www.jacquardproducts.com/cyanotype)：普鲁士蓝单色印相；[CyanoLUT 作者](https://github.com/alareta/CyanoLUT)说明负片补偿曲线依赖具体纸、打印机与曝光链路 | 独立制作蓝色墨到纸白的正像 LUT，墨色 RGB [0.025,0.09,0.22]，纸白 [0.98,0.975,0.96]。没有把用于制作负片的校准 LUT 当正像滤镜，也未伪造化学测量 |
| 297 德系冷调 | 此名称没有唯一厂家或标准测量对象 | 独立设计冷灰、低饱和度、深黑与肤色保护，不标为 Leica / Zeiss 官方色彩 |

同名社区 LUT 与官方测量不是同一回事。所有条目保留 `camera_calibrated=false`、`film_calibrated=false`、`official_lut=false`、`approximation=true`。ISO 信息不改变相机 ISO、曝光或白平衡。无法证明 100% 还原；真实胶片还受光源、曝光、乳剂批次、冲洗与扫描影响。

作者 LUT 固定到上述 Git revision，原文件及许可证位于 `third_party/style-filter-luts/`。Eerie 下载还核验了 Git blob SHA-1 `ff769726d39118b9bcbc31fabb7c6b00aba858ec`（7,077,934 字节）。源文件 SHA-256、参数、目标色表和拟合结果见 `native/gr3/style-filters-reference.json`。完整署名见 `third_party/style-filter-luts/README.md`。

## 成片和预览

网页、CPU 和 SIMD 使用同一组 15³ / 8-bit、RGB 蓝轴最快 LUT，通过四面体插值采样。`.cube` 的红轴最快排列在导入时显式转轴。7 张表分为 4 + 3 的独立只读 bank，均低于每个 ARM 模块 64 KiB 的链接上限。

**这七款的保存 JPEG 使用 LUT CPU / SIMD 路径。** 原厂 ISP 预览是单独拟合，不标记为 still native color completion。这样避免把不够精确的 ISP 拟合作为成片处理完成证据，尤其 Polaroid。代价是拍摄新增色彩处理工作，需要设备测量保存耗时；RAW 保护与既有拍摄生命周期不变。

新预览曲线采用完整 256 节点，不改变历史胶卷已有的 8-bit delta 压缩格式。蓝晒对后矩阵和曲线作数学等价的缩放分解，保留 signed9 / signed12 校验，不截断越界系数。独立随机 8192 点的原厂模型拟合误差如下；这些是**预览模型对自建色表的误差，不是实际胶片还原精度**：

| 滤镜 | ΔE00 中位数 | P95 |
|---|---:|---:|
| Leica Monochrome | 0.77 | 2.61 |
| Lomography | 0.47 | 1.47 |
| Polaroid | 1.91 | 5.52 |
| Velvia 50 | 0.62 | 1.79 |
| Cyberpunk | 0.87 | 2.50 |
| Cyanotype | 0.84 | 2.52 |
| 德系冷调 | 0.61 | 2.07 |

默认关闭颗粒、光晕、漏光等附加质感，沿用用户主动开启的现有控件；原有胶卷配方与编号不重排。新图标使用 761–767，文字追加在原资源之后；不移动已有 Charmera、自定义 LUT、A/B、裁切焦距的资源编号。

SD 包延续原格式，完整记录摘要绑定渲染器；额外冻结了本次变更前的 47 卷摘要和自定义渲染器摘要，使原卡包继续可读。新稀疏 ID 的机内快照文件使用 M10VS01–07.bin；旧 33–78 与 Charmera 的 M10VS00.bin 不变。

## 再生成和验证入口

```sh
.venv/bin/python scripts/build_gr3_style_filters_reference.py
.venv/bin/python scripts/fit_gr3_style_filters_native.py
.venv/bin/python scripts/build_gr3_isp_native_look.py --generate-profiles
.venv/bin/python scripts/generate_m10v_icons.py
.venv/bin/python scripts/generate_m10v_film_cards.py
node scripts/generate_gr3_sd_contract.mjs
.venv/bin/python scripts/verify_gr3_style_filters_reference.py
.venv/bin/python scripts/preview_gr3_style_filters.py
```

实际检查结果、测试候选与验收步骤见 `docs/testing/gr3-style-filters-20261023.md`。独立代码审查未发现需修改的问题；这不替代真机验收。

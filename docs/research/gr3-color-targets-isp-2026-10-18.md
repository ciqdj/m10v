# GR III 5207 / Phoenix II 色彩目标与 ISP 输入域调查

日期：2026-10-18。范围仅含色彩研究、当前映射量化及离线参考；没有修改生产模型、生成头文件、固件或相机设置。保留全部画质及空间效果的 ISP 迁移应另行验证。

## 结论

“5207、蓝凤凰几乎和原图没区别”得到当前代码及数值支持：它们是刻意克制的 **encoded display sRGB → encoded display sRGB** 设计映射，参数不是 Kodak / HARMAN 实测数据。现有参考验证只证明 LUT 插值能复现该设计，不能证明胶卷模拟准确。

随机 65,536 个 RGB8 样本，5207 有 98.14%、Phoenix II 有 97.51% 的输出相对输入 ΔE00 小于 2。两模型之间的随机色 ΔE00 中位数也只有 0.765。不能靠增大固定蓝偏、暖偏或饱和度，宣称恢复了真实胶卷。

**当前可用目标**：5207 可用已 vendor 的 MIT 开源 `spectral_film_lut` 构造场景域的 5207 + 2383 打印模拟离线参考；该目标有明确输入及输出契约，但不能直接套在相机 JPEG。Phoenix II 官方提供曝光与扫描流程约束，未发现可在当前仓库合法、可校验地直接使用的官方 Phoenix II 正像 3D LUT；需要实拍标定，不能拿 Phoenix I 或任意蓝色 LUT 代替。

## 可复现量化

在仓库根目录运行：

```sh
.venv/bin/python scripts/analyze_gr3_film_color_targets.py
.venv/bin/python scripts/analyze_gr3_film_color_targets.py --spectral-probe
.venv/bin/python scripts/analyze_gr3_film_color_targets.py --spectral-probe --verify-native
.venv/bin/python scripts/analyze_gr3_film_color_targets.py --spectral-cube --verify-native
```

第一条无需网络、不写生产数据。第二条额外调用 vendored 5207 + 2383 管线，只输入合成场景线性 XYZ 曝光阶梯。第三条还编译 C 表采样器作独立交叉校验，结果写 `native-sampler-verification.json`。默认依赖本地 NumPy 2.5.3、colour-science 0.4.7；可选 PNG 依赖 Pillow，光谱探针使用现有 vendored 包依赖。

产物位于已被 `/builds/` 规则忽略的 `builds/gr3-isp-research/color/`：

- `identity-distance.json`：解析设计、实际 15³ / 8bit 表、二者差异、模型间差异、源码 SHA256。
- `patches.csv`：灰阶及 ColorChecker 每个输入/输出 RGB 与 ΔE00。
- `colorchecker-comparison.png`：同一组合成 sRGB 色块的原图/5207/Phoenix II 对照。
- 可选 `spectral-scene-probe.json` 与 MIT attribution：合成场景曝光阶梯，明确不代表 GR3 实拍。
- 可选 `5207-2383-scene-linear-rec709-d65-domain0-4.cube` 与 `spectral-cube-contract.json`：33³，红最快，输入为 **scene-linear Rec709/sRGB 原色、D65、RGB=.18 中灰、DOMAIN 0…4**，输出 encoded sRGB D65。均匀线性网格会欠采样暗部，未经相机标定，只用于离线参考；不能直接用于显示 JPEG，也不是可部署的 ISP 参数。

度量约定：输入为编码 sRGB D65 的 RGB8；精确整数四面体插值与固件相同，最后 `(sum+127)//255`。灰阶覆盖 0…255，随机色由 NumPy seed=520767 生成均匀 RGB8；不是自然图像颜色频率分布。ColorChecker 使用 colour-science `ColorChecker 2005` 的 24 个 xyY，按其白点 Bradford 适配到 D65，编码并量化 RGB8。Lab 白点 D65，ΔE 为 CIEDE2000。这里的 ΔE 是对 identity 的距离，不是对胶卷真值的误差，也不应直接当作主观可见性判据。

ColorChecker 转 sRGB 时有 1 个通道超出显示色域并被裁到边界，记录在 JSON；这是显示参考色块集，并非该实体色卡的相机实拍或胶卷实拍。

| 模型 / 测试集 | RGB 单通道绝对差均值 / P95 / 最大值（0…255） | ΔE00 中位数 / P95 / 最大值 | ΔE00 < 2 |
| --- | --- | --- | --- |
| 5207 / 灰阶 256 | 2.313 / 5 / 6 | 0.706 / 1.189 / 1.230 | 100% |
| 5207 / ColorChecker 24 | 2.472 / 5 / 5 | 1.022 / 1.410 / 1.456 | 100% |
| 5207 / 随机 65536 | 3.332 / 7 / 20 | 1.119 / 1.853 / 2.972 | 98.14% |
| Phoenix II / 灰阶 256 | 1.316 / 4 / 5 | 0.323 / 0.851 / 1.023 | 100% |
| Phoenix II / ColorChecker 24 | 1.472 / 4 / 7 | 0.659 / 1.417 / 2.343 | 95.83% |
| Phoenix II / 随机 65536 | 1.879 / 6 / 11 | 0.733 / 1.765 / 3.798 | 97.51% |

灰阶 RGB 三通道相等。例：5207 的 `128→130, 230→226, 255→249`；Phoenix II 的 `128→128, 230→227, 255→250`。这不是大幅 film tone response。5207 的 `.985/.988/.98` 主对角混色矩阵、`.04` 暖色强度以及 Phoenix II `.025` 暖色、`.16` 条件蓝色参数，均为设计假设。

解析映射本身也接近 identity：随机色的解析 ΔE00 中位数为 5207 1.095、Phoenix II 0.674。表输出相对解析映射的 ΔE00 P95 仅 0.324 / 0.395，因此主要原因不是 15³ 表或整数插值把强烈效果“抹掉”。

本次另用本机 C 编译器编译当前 `film_5207.c`、`film_harman.c` 为研究用 dylib，通过 ctypes 比对每款 4,101 个随机/端点 RGB：Python 表采样与实际 `m10v_5207_rgb` / `m10v_harman_rgb(0, …)` 最大通道差均为 **0**。这验证表阶段模型；它不包含 YCbCr 往返、色度抽样、叠加空间效果及最终 JPEG，不能替代相机输出验证。

## 官方资料能约束什么

### Kodak 5207

[Kodak 官方技术资料 H-1-5207](https://www.kodak.com/content/products-brochures/motion-picture/KODAK-VISION3-250D-5207-7207-technical-information.pdf) 当前为 **2026 年 3 月修订**：日光 5500K、EI250、ECN-2；包含特性、光谱敏感度及染料密度曲线，强调高光宽容度。PDF 还说明 anti-halation undercoat 替代传统 remjet。曲线是指定条件下的代表性样本，并非每卷保证值。

这不是固定 sRGB 外观规范，也不是可直接作用于 JPEG 的官方 LUT。需要选定乳剂版本、曝光、冲洗、扫描/打印和最终显示目标。尤其不能以“5207”名称默认该 2026 PDF 与 vendored `year=2009` 数字化曲线完全一致。PDF 公开可读不等于获得其全部图表的开放再分发许可。

### HARMAN Phoenix II

[HARMAN 官方技术资料，Jul 2025](https://www.harmanphoto.co.uk/amfile/file/download/file/1968/product/2208/) 给出 ISO200 / C41、实用 EI100–200、比第一代更正常的反差与颜色、更细颗粒，仍有实验性。无橙色 mask，高反差场景可出现 halation；这些不推出固定的“蓝色”正像。

同一 PDF 的扫描起点具有设备差异：Fuji SP3000 使用 All Hard、饱和度 +2、C=-2；Noritsu 使用 Contrast 3、Chroma 100、Automatic Contrast 2=5、C=+1/Y=-2。它们是扫描器控制量，不能直接翻译为 RGB matrix、通道增益或软件 LUT。

[官方扫描建议](https://www.harmanphoto.co.uk/scanning-tips/) 对 Phoenix II 推荐自动曝光/颜色，或反转片扫描后再反相；说明正像结果取决于扫描及反相流程。网页的 **Phoenix 200 / 第一代** 段落另有降低饱和度建议，不应混入 Phoenix II 的契约。

## 开源参考、许可与输入契约

[Jan Lohse / spectral_film_lut](https://github.com/JanLohse/spectral_film_lut) 已 vendor 于 `third_party/spectral-film-lut`；`LICENSE` 为 MIT，Copyright 2026 Jan Lohse。可使用、改作及分发代码，但复制实质内容时保留完整许可与 attribution。第三方标识、厂家 PDF 和测量数据各自的权利不能单凭该软件许可一概推断。

vendored `negative_film/kodak_5207.py` 存有 `KODAK_5207`，包括数字化特性、敏感度、染料密度数据；未见 Phoenix / HARMAN stock。该文件未绑定官方 PDF 的具体修订版。项目作者也明确说明数据精度和未公开层间作用限制模型准确性：[作者文档](https://janlohse.github.io/spectral_film_lut/)。

本地源码 `film_spectral.py:input_transform` 和 `utils.py:film_conversion` 是本次准确输入契约的依据（[在线接口文档](https://janlohse.github.io/spectral_film_lut/reference/utils/) 可能与 vendor 版本有差异）：

| 管线位置 | 合法数值含义 | 易出错用法 |
| --- | --- | --- |
| `input_colorspace=None` | 场景线性 CIE XYZ，Y=.18 表示参考中灰 | 把编码 sRGB 或归一化 JPEG RGB 当 XYZ |
| 指定 RGB colorspace | `RGB_to_XYZ(..., apply_cctf_decoding=True)`；传入该色域及传递函数编码的**场景参考** RGB | 手动 EOTF 后仍标成 sRGB导致重复解码；给显示 JPEG 标 sRGB并声称恢复场景 |
| Log 输入 | 指定正确色域、Log 传递函数及中灰曝光约定，由该 colorspace 解码 | 任意 Log LUT 与 GR3 JPEG 直接相连 |
| `mode='negative'` | 可输出 ADX 编码密度（默认）或层密度，不是可观看正像 | 把负片密度直接作为 RGB 显示 |
| `mode='full'` + `print_film=2383` | 模拟负片曝光、打印、投影，再编码指定输出 | 忽略打印/投影白点和 Gamma；把 negative-only 曲线当最终 look |
| `inversion=True` | APD/反相模型；`inversion_gamma`、masking 等包含自由假设 | 把某个 gamma 宣称为厂家标定扫描结果 |

本研究可选探针明确：D65 场景 XYZ，中灰 Y=.18，从 -6 到 +6 stops，每 .5 stop；`exp_kelvin=6500`；5207 + 2383；printer lights=0、color_masking=None；输出 Rec.709 原色 + sRGB 编码；`sat_adjust=1`、无额外 shadow compensation。它用于检查合法场景域管线及高光趋势，不能作为“JPEG套LUT”的效果演示。实际 API 的 upsampling 名称为 `SFL upsampling`；部分默认签名仍写旧内部名 `barycentric_nnls_all`，直接使用会报未知方法。

该合成灰阶实际得到中灰约 `[.481,.481,.481]`，+6 stops 约 `[.972,.980,.923]`，25 个点均无通道达到 1。只说明这个参数组合的合成参考有高光肩部，不能证明相机高光、彩色高光或真实胶卷匹配准确。

## ISP 迁移的明确校准目标

1. **先锁定输入点**：通过取样/抓帧证明该 ISP 节点接收的是 RAW线性、白平衡后 camera RGB、scene RGB/XYZ，还是已调色 YCbCr。记录位深、黑白电平、full/limited range、矩阵与transfer。sRGB 解码只移除显示 EOTF，不能恢复相机 tone curve、曝光、光谱或已剪白细节。
2. **5207 目标必须带完整后链路**：先采用可审阅的 5207 + 2383 场景参考，或定义某个扫描器/反相版本的正像。保留中灰、高光肩部、彩色高光、肤色、蓝/青和叶绿的匹配指标，不以“颜色差越大越好”设门槛。ISP 的 matrix/curve/post 参数必须相对 **GR3 原厂 Standard 基线**拟合及验证：不能把完整目标 matrix 当作叠加修正 matrix，不能把已包含标准 ISP tone 的显示 look 再叠一次标准 tone。需要明确替换/复合顺序并测量最终 JPEG。
3. **Phoenix II 需要建立目标集**：同场景同光源，GR3 RAW+JPEG 与实际 Phoenix II EI100/200 包围曝光，统一 C41；锁定一个扫描器、曝光、反相和白平衡流程，加入灰卡/ColorChecker、肤色、叶绿、蓝天、强背光点光源。没有这一组证据只能标“受启发设计”，不能标“实测胶卷”。
4. **拟合后留出验证**：训练和保留场景分开，比较输出 ΔE00、灰阶单调性、色相轨迹、高光保留、越界/剪裁比例、实际照片，记录误差分布及例外。只要输入仍是显示 JPEG，就将模型标为显示域拟合，承认无法重新获得胶卷宽容度。
5. **空间效果与性能保持独立契约**：3D LUT 可表达逐像素颜色，但不能表达颗粒、光晕、漏光的空间和随机行为。ISP 迁移不能通过降低分辨率、位深或关闭这些效果换取速度；数值等价、完整画质、相机端耗时及回放行为均需实机验证。本次没有作实机“秒回放”结论。

没有采用来源不明或无授权的商业胶卷 LUT，没有把设计假设伪装成厂家参数，没有刷写固件。

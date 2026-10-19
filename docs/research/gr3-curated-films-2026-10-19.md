# Portra 160、富士业务用 100、新版乐凯 C200

本次新增稳定 ID 69、70、71；旧 ID 1–68、五槽 journal 的 schema/字节布局保持不变。当前公开目录从 36 款扩展到 39 款。精选在网页、机内内置目录和新导出的 SD 胶卷包中优先显示。SD 包的同类内部顺序保留输入顺序，安装、名称、图标仍通过稳定 ID 对应。

## 来源与模拟边界

| 胶卷 | 官方依据 | 社区依据与实际采用方式 |
| --- | --- | --- |
| Portra 160 | [Kodak E-4051](https://www.kodakprofessional.com/sites/default/files/2025-07/e4051.pdf)：ISO 160、低反差、中等饱和度、细颗粒等定性约束 | [G'MIC 社区同名现代 Portra 160 LUT](https://github.com/YahiaAngelo/Film-Luts/blob/main/luts/negative_new/kodak_portra_160.cube)，保留原始文件与许可，不使用 NC/VC |
| 富士业务用 100 | [FUJICOLOR 100 官方产品说明](https://www.fujifilm.com.hk/products/consumer_film/color_negativefilms_35mm/100/index.html)：ISO 100、细颗粒、肤色与宽容度的定性方向；并未由此证明业务卷与其他富士乳剂相同 | 没找到可核验且可用的业务用 100 专属公开 LUT，采用 [Superia 100 社区 LUT](https://github.com/YahiaAngelo/Film-Luts/blob/main/luts/negative_old/fuji_superia_100.cube) 的 80% 混合作为近似；此比例为设计假设 |
| 乐凯 C200 新版 | [乐凯影像商城](https://www.lucky.cn/)用于确认新版产品身份；本次未找到可用的官方感光曲线、光谱数据或官方 LUT | 参考 [Ross McConaghy 的新版 Lucky Color 200 社区方案](https://www.rossandhisjpegs.com/lumix/lucky-color-200)的色彩方向，独立生成显示域色表。未下载 Firebird/Daisy 文件，未将松下机内参数直接映射为理光参数；全部数值均为明确记录的假设，不使用老 Super 200 LUT |

三者均标记 `camera_calibrated=false`、`film_calibrated=false`、`official_lut=false`。此实现不宣称 100% 还原；尤其后两款仍需要可靠的本胶卷色表、指定冲扫参考和同场景实拍来进一步校准。ISO 仅作为参考资料，不改动相机 ISO。

## 色彩与质感

CPU 路径和网页预览共用 RGB 排列、蓝轴最快的 15³、8 bit 色表，使用四面体插值。原始 `.cube` 为红轴最快，导入时显式转轴。三款新表单独存放在 `film_curated.c` 模块，以维持每个 ARM 链接模块的 64 KiB 上限。

原厂 ISP 路径使用相同目标色表拟合独立的相对矩阵、256 点曲线和 12 区色相矩阵；它与 CPU 色表并非逐像素等价。使用已提取的 Standard gamma 模型，而不是把 JPEG 当作场景线性光。8192 个固定种子的独立随机点上，完整量化模型与目标色表的 ΔE00 中位数 / P95 为：

| 胶卷 | 中位数 | P95 |
| --- | ---: | ---: |
| Portra 160 | 1.40 | 3.53 |
| 富士业务用 100 | 1.13 | 2.83 |
| 乐凯 C200 | 0.23 | 0.41 |

这些数值是**实现对自身目标色表的拟合误差**，不代表对真实胶片的误差，也不代表真机校准结果。

Portra / 富士默认弱颗粒、细颗粒尺寸，乐凯默认中颗粒、标准尺寸；默认关闭额外光晕与漏光。切卷清除 RED 专属 EI，保留其它槽位。网页与机内选择、完整重置、质感重置使用相同的新卷默认值。

## 资源与使用

新增图标、机内大卡片、文字资源及 SD 数据合同同时更新；GR III/IIIx 共用新目录，GR IV 的共享胶卷链路同步更新资源容量与颗粒图标编号。HDF 原资源编号保留，新卷文字追加在其后。

需要重新生成同版本固件并重新下载 SD 胶卷包，替换 `M10V/FILMS.M10`。旧资源包按既有版本合同拒绝安装，不会自动把历史资源包改成新排序；旧槽位的胶卷 ID 不改变。

离线再生成顺序：

```sh
.venv/bin/python scripts/build_gr3_curated_reference.py
.venv/bin/python scripts/fit_gr3_curated_native.py
.venv/bin/python scripts/build_gr3_isp_native_look.py --generate-profiles
.venv/bin/python scripts/generate_m10v_icons.py
.venv/bin/python scripts/generate_m10v_film_cards.py
node scripts/generate_gr3_sd_contract.mjs
```

来源哈希、原始 LUT、假设参数、色表插值误差和完整原厂模型拟合结果保存在 `native/gr3/curated-reference.json`。机内 SD 文件系统与最终照片效果仍需真机验收。

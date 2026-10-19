# CCD Classic：老 GR DIGITAL 风格模拟

2026-10-19 新增稳定 ID **72**、key `ccd-classic`，展示名 **CCD Classic**，归入 M10V精选。公开目录现为 40 款；旧 ID 1–71、五槽 journal 布局和已有槽位不变。

## 目标和网上依据

目标是老 GR DIGITAL 在低 ISO、正常曝光下的清透彩色直出，取 Standard/Vivid 方向。不是把传感器类型当作统一的色彩配置，也不把旧 GR DIGITAL IV 和现代 GR IV 混为一谈。

- [初代 GR DIGITAL 官方画册](https://www.ricoh-imaging.co.jp/english/r_dc/support/brochure/pdf/gr_digital.pdf)：确认 CCD/GR ENGINE 的产品身份；画册描述自然色彩和细节，并不提供可复用色彩矩阵。
- [GR DIGITAL IV 官方 Image Settings](https://www.ricoh-imaging.co.jp/english/r_dc/support/faq/bp/grd4/gr04404.html)：Standard 为正常反差、锐度和鲜艳度；Vivid 增强这些属性；自定义提供九级调整及橙、绿、蓝、红、洋红的色相/鲜艳度。这里采用其定性方向，没有把菜单级数冒充 GR III 数值。
- [GR DIGITAL IV 官方说明书](https://www.ricoh-imaging.co.jp/english/r_dc/support/manual/pdf/grd4/grd4_en.pdf)：用于核对自定义图像处理选项。
- [Canon G9 官方规格](https://www.usa.canon.com/support/p/powershot-g9)：同属 CCD，也包含多种不同 My Colors 模式，说明“CCD”本身不足以指定唯一色彩目标；未使用其色彩作为本款目标。

以上公开资料没有提供可核验的老 GR DIGITAL 官方 LUT、完整 CFA 光谱/ISP 变换或同场景配对测量。**所有下列强度均为公开记录的设计假设，不是厂家参数，不代表 100% 还原或真机校准。** 已有显示域图像无法恢复拍摄时已丢失的高光、低 ISO 传感器噪声、光谱同色异谱响应和镜头特征。

## 色彩参数

输入/输出均为编码 sRGB D65，沿用当前已完成 ISP 的输入契约：

| 参数 | 数值 | 用途 |
| --- | ---: | --- |
| 反差 | 0.32 | `x + 0.32*x*(1-x)*(2*x-1)`；压暗暗部、提亮亮部，保留黑白端点与中性灰 |
| 基础色度 | 1.065 | 小幅增强色彩，不叠加有色黑位或泛黄白点 |
| 蓝主导附加强度 | 0.055 | 增强蓝色纯度；权重随蓝色相对其他通道的优势变化 |
| 绿主导附加强度 | 0.025 | 温和增强绿色，避免全面改变肤色 |
| 红主导附加强度 | 0.015 | 小幅增强红色，减少橙色肤色过饱和 |
| 高光色度减弱 | 0.18 | 亮度 0.75 以上按平方权重减弱增强量，维持较干净的高光 |

默认颗粒、柔光、光晕、漏光均关闭；颗粒尺寸为细。没有人为加入紫边、竖向拖影、脏点、重度高 ISO 噪声或胶片雾化。用户仍可通过已有公共质感控件调整颗粒、漏光；切卷、质感重置、完整重置和网页默认保持一致。

## 还原度与速度的实现

复杂运算只在离线生成时进行，输出与现有精选同规格的 **15³、8 bit RGB 色表**，蓝轴最快，四面体整数插值。新增色表仅 10,125 字节，四张精选色表仍放在同一独立模块并低于每模块 64 KiB 限制；不新增运行时浮点色彩循环或全图缓冲区。

原厂 ISP 路径从同一色表拟合相对矩阵、256 点单调曲线、12 区色相矩阵。只有既有 recipe/generation 合同确认 ISP 已执行色彩后才跳过 CPU 色彩；软件回退仍完整可用。默认无质感残余时，CPU 后处理不需要遍历全图，也不需要额外 scratch。该性质不代表整机拍照、ISP、JPEG 编码和写卡耗时为零。

GR III 默认已有原厂 ISP/取景色调预览路径；GR IIIx 和 GR IV 沿用各自既有能力与限制，不因为新增 CCD 预设扩大其取景能力声明。GR IV 共用色表、目录、默认值及资源容量同步更新。

## 验证证据

- 新测试先确认缺少 ID72、预览拒绝和默认值无效，再实施。
- 网页：ID72、精选分类、SD 排序、切卷及重置、灰阶单调、中性端点和 alpha 保持。
- 原生：CCD 的两种重置、ISP 完成后的无 scratch 像素不变路径；独立整数参考核对 C/web 色表；ARM 原厂 ISP 写入、代次失配拒绝、缓存和原厂参数保护。
- 8,192 个固定种子独立随机点上，解析目标到 15³ 色表的 ΔE00 P95 **0.383**；完整量化 ISP 相对色表拟合中位数 **0.269**、P95 **0.492**。这些只衡量实现对自身目标的误差。
- `scripts/verify_gr3_ccd.py` 输出 [对照图](../previews/ccd-classic/comparison.jpg) 和 [验证 JSON](../previews/ccd-classic/verification.json)。左为仓库已有显示域图，中为 LUT，右为 ISP 模型；不是老 GR 的配对实拍证据。
- 24MP、主机 clang `-O2`、五次测量：CPU LUT 软件回退中位数约 **0.325 秒**；ISP 已完成时，无质感 CPU 残余约 **0.002 毫秒**。这只是本次主机测量，不是相机性能承诺，完整样本保存在验证 JSON。

构建审查修正了新增名称后的资源数量校验，更新静态图标和动态卡片边界。旧固件与旧 SD 包仍按版本合同拒绝混用；使用新构建后需重新下载配套 `M10V/FILMS.M10`。

## 可重复生成

```sh
.venv/bin/python scripts/build_gr3_curated_reference.py
.venv/bin/python scripts/fit_gr3_curated_native.py
.venv/bin/python scripts/build_gr3_isp_native_look.py --generate-profiles
.venv/bin/python scripts/generate_m10v_icons.py
.venv/bin/python scripts/generate_m10v_film_cards.py
node scripts/generate_gr3_sd_contract.mjs
.venv/bin/python scripts/verify_gr3_ccd.py
```

生成器/输入哈希与全部拟合数据保存在 `native/gr3/curated-reference.json`。真机验收需同场景老 GR 与目标机的 JPEG：日光肤色、红绿蓝物体、灰卡、逆光高光、室内混合光，并记录白平衡、曝光、ISO、色彩模式及保存耗时；目前没有这些配对测量，不作真机标定结论。

## 最终回归与候选交付

- Node 全量 285 项：280 通过、4 跳过、1 项组合测试仍加载旧画幅标题编号的断言；同步到新编号后，该测试覆盖的 release/debug 全部八种扩展组合独立复测通过。没有通过放宽生产校验来消除失败。
- 受影响的原生/ARM 集成链路 89 项全部通过：包含 SD 记录与安装、末页与保存失败回退、机内完整目录与 42 行边界、五槽与旧 journal 迁移、图标/文本、设置视图和 GR IV 共用运行体。
- CCD/色表/原厂 ISP 专项 15 项通过；Node CCD/精选/SD 专项 15 项通过。
- 更广的 Python 全目录探索未完成，不声明 Python 全仓测试通过；最终采用上述受影响链路专项与 Node 全量加组合复测作为验证范围。
- 已执行独立代码审查并修正资源总数量 guard；`git diff --check` 通过。

候选保存在 `builds/ccd-classic/gr3/` 和 `builds/ccd-classic/gr3x/`。二者第一槽均为 CCD Classic；GR III 的 `receipt.json`、GR IIIx 的 `M10V-build-receipt.json` 包含完整配置和 SHA256，SD 包为各目录 `M10V/FILMS.M10`。已经构建和回读校验，未部署网站或写入相机，`camera_tested=false`。

<div align="center">

![M10V — Your films. Your GR.](docs/previews/readme-hero.svg)

**你的胶卷，你的 GR。**

面向 **RICOH GR III / GR IIIx / GR IV** 的原生胶卷工作台，并提供 **GR II** 固件检查。

[更新日志](https://m10v.izhaoo.com/changelog/) · [功能](#功能) · [开始使用](#开始使用) · [名字的故事](#名字的故事) · [开发与验证](#开发与验证) · [致谢](#致谢)

</div>

> **当前状态：待实机验证。** 网页、固件构建与 ARM 执行检查已完成，但修改固件的刷入、启动、菜单显示和成像仍需真实相机验证。刷入可能导致无法启动、数据丢失或设备损坏（变砖），且无法保证恢复。

## 名字的故事

在 GR III 官方固件内部的 Linux 根文件系统中，`/etc/hostname` 写着四个字符：`m10v`。

拿起 GR 时，我们关注镜头、色彩与快门；沿着固件往里走，还能看见这些体验背后的代码和配置。M10V 沿用了这个小小的内部名字，把它带到界面上，成为选胶卷、调质感、建立自己影像方案的工作台。

**从读懂相机开始，最后回到拍照本身。**

[查看名字来源的固件证据](docs/research/m10v-name-origin.md)

## 功能

| | 你可以做什么 |
| --- | --- |
| **胶卷库** | 46 款可选胶卷共用一个目录，配置五个活动槽位，保留历史胶卷编号 |
| **新增六款胶卷** | 富士 C200、ProImage 100、T-Max 100、Aerochrome III 1443、Aerocolor IV 2460、VISION3 50D 5203；[资料、拟合误差与模拟边界](docs/research/gr3-six-film-references-2026-10-20.md) |
| **胶卷图标** | 原创 40×40 胶卷罐图标，网页与固件使用相同像素；800T 为红色 |
| **颗粒与柔光** | 每槽独立设置关闭、弱、中、强 |
| **机内胶卷参数** | GR III 在【图像控制】按 FN，各卷可独立调颗粒、柔光、颗粒尺寸与漏光；800T／蓝凤凰另有三项光晕参数，蓝凤凰另有 EI 200／120、HARMAN RED 另有 EI 125／64／250 模拟曝光。参数行使用不同原厂图标和数值，选中后保留中文标题；实机验收待完成 |
| **突破版本锁** | GR III／GR IIIx 原生导出可选，默认关闭；开启默认只适配 DSP 包头、保留 CPU，不需填写未知版本号。CPU 更高时仍可能被拒绝；高级方式需实际完整 DSP／CPU 版本。尚未验证纪念版机身刷写 |
| **时间戳** | 日期或日期与时间，可选格式、位置和颜色，使用相机时钟 |
| **开关机图片** | GR III 2.10 分别上传、裁切预览、恢复默认，随同一固件导出；开机原生资源替换已离线验证，正常开机显示入口尚未闭环，[证据与边界](docs/research/gr3-power-images.md) |
| **统一工作台** | 导入后自动识别机型，设置方案，确认风险，再保存对应固件 |
| **配置编辑** | 搜索与分类筛选、五槽同步、草稿、撤销／重做、取消构建 |

![M10V 胶卷图标目录](docs/previews/m10v-film-icons.png)

### 支持机型

| 机型 | 当前官方核验样本 | 导出文件 |
| --- | --- | --- |
| **GR III** | Street Edition 2.10 | `fwdc239b.bin` |
| **GR IIIx** | 1.60 | `fwdc243b.bin` |
| **GR IV** | 1.11（内部 1.11.10.7）；原生五槽胶卷库与配方工具，等待实机验收 | `fwdc248b.bin` |
| **GR II** | 3.00；组件、资源与原样往返只读检查 | 修改导出未开放 |

GR III／GR IIIx 工作台支持配方参数、原厂名称与图标、负片颗粒、RAW 降噪、画幅比例和水平仪等工具；GR IV 同步提供五槽胶卷、SD 换卷、时间戳、六位置配方、20原厂名称/图标、65:24、水平仪及RAW降噪工具。工作台按机型显示可用状态。

GR IV 的 `/gr4/` 使用共享工作台与独立原生ABI，复用GR3颜色算法和46款当前胶卷；原厂参考编辑器保留在 `/gr4/reference/`。实现通过原始ARM、完整封包及网页下载验证，GR4刷入和成像仍待实机验收。[功能对照与验证](docs/research/gr4-native-m10v-parity-2026-10-18.md)。GR II 已解析嵌套 UNITY 容器和 121 项资源，但修改后的更新校验与原生接口尚未证明。[查看两款机型的逆向证据](docs/research/gr4-gr2-port-evidence.md)。

### 使用边界

- 胶卷效果处理保存的静态 **JPEG**。取景采用 Standard 原色，不模拟胶卷色彩；机内 RAW 再开发暂未接入；RAW 原始像素受保护，DNG 内嵌 JPEG 预览需单独验收。
- 五个胶卷承载槽的静态成像色彩配置统一采用 Standard 基底，避免与 Vivid／Bleach Bypass／Retro／HDR／Cross 的原厂色彩叠加；静态胶卷处理已获实拍确认；取景统一采用 Standard 原色，新优化待实机验收。
- 目录含 33 套 M10V 风格和 32 套已有模拟预设，不保证与其他实现的成像逐像素一致。
- 首次没有有效 M10V 记录时使用网页配置；已有机内记录优先，网页配置不会自动覆盖已有机内设置。
- 原厂工具方案与原生胶卷库方案分开构建；切换方案会保留草稿，暂不叠加两套运行区。
- 胶卷库随固件内置，无需 `FILMS.GRF`、授权码或外部图片文件。

## 开始使用

### 1. 准备环境

需要 **Node.js ≥ 20、Python 3 和 LLVM clang**。Node 服务使用内置模块，无需 `npm install`。

```bash
git clone https://github.com/zhaoo/m10v.git
cd m10v
git switch develop
python3 -m venv .venv
```

macOS 可通过 Homebrew 安装 LLVM：

```bash
brew install llvm
```

开关机图片的预览与压缩需要 Pillow：`.venv/bin/python -m pip install pillow`。

GR IV 参考编辑器还需要 LLD：`brew install lld`。导入后可在设置中查看编译、链接和 ARM ELF 预检结果。

构建器会查找 Homebrew 的 LLVM；其他安装位置可用 `M10V_LLVM_CLANG` 指定 **clang 的完整路径**。

### 2. 放入官方固件

官方固件不随仓库分发。自行准备与当前核验样本完全匹配的官方文件：

```text
bin/
├── fwdc239b-gr3-official.bin       # GR III Street Edition 2.10
├── fwdc243b-gr3x-official.bin      # GR IIIx 1.60
├── fwdc248b-gr4-officical.bin      # GR IV 1.11，保留现有本地文件名
└── rg2_v003/rg2_v003.frm           # GR II 3.00
```

部分历史测试仍读取根目录别名，可创建符号链接：

```bash
ln -s bin/fwdc239b-gr3-official.bin fwdc239b-offical.bin
ln -s fwdc239b-offical.bin fwdc239b.bin
```

### 3. 打开工作台

```bash
npm start
```

按终端显示的地址打开浏览器。macOS 也可双击 `start.command`。

**导入固件 → 设置方案 → 保存固件**

先选槽位，再选胶卷与质感。点击「保存固件」时阅读风险提示，明确确认后才会开始构建。取消或按 Esc 不会生成文件；每次保存都要重新确认。

> 服务器监听 loopback；配置 `M10V_PORT` 和 `M10V_PUBLIC_ORIGIN` 后可通过 Nginx 反向代理。不能只上传静态 web 目录。Ubuntu 24.04 + 宝塔的具体步骤见 [部署指南](deploy/README.md)。

<details>
<summary><strong>GR III 原厂工具的可选兼容运行时</strong></summary>

原生胶卷库采用本仓库 C/ARM 实现，不依赖外部胶卷包或 GRLife 兼容运行时。部分原厂工具仍使用锁定的兼容运行时，它不纳入源码仓库：

```bash
node scripts/sync-grlife-runtime.mjs
```

该路径需要 Python 3.12；可通过 `M10V_PYTHON` 指定解释器。GR IV 参考核心及其 Python 依赖保留在 `vendor/gr4/`。为保持源码仓库轻量，三份大体积 GR IV 校准 DNG 样片留在本机，不随 Git 分发；启用相关校准测试前，需从参考项目恢复，文件名与哈希见 `vendor/gr4/PROVENANCE.json`。各模块来源与许可见 [第三方说明](THIRD_PARTY_NOTICES.md)。

</details>

### GR III 固件桥接

新版 **2.10.33.27** 保持 2.10，只增加第三段。用户提供的 JPG 与 DNG 的 MakerNote `0x0027` 均为 `fd f5 df e4`，逐字节取反得到 DSP **2.10.32.27**，旧版 2.10.22.27 因此低于机内版本。CPU 完整版本未从照片取得。

在工作台下载新版两阶段测试套件，先安装 stage-1-bridge/fwdc239b.bin；明确成功并重启后，换成 stage-2-official/fwdc239b.bin 安装官方 2.10。第一阶段失败时不要继续。新版仅完成离线验证，完整刷写与恢复仍待实机验收；旧版停止使用。机内任一组件高于 2.10.33.27 时仍可能拒绝。

## 开发与验证

**`develop`** 为日常开发分支，**`main`** 为正式源码分支。分支名不表示固件已通过实机验收。

```bash
# JavaScript、API、固件容器和导出检查
npm test

# 原生运行体、ARM 执行与拍摄桥验证
.venv/bin/python -m pip install pillow capstone unicorn
.venv/bin/python -m unittest \
  tests.test_gr3_m10v_library \
  tests.test_gr3_m10v_library_arm \
  tests.test_gr3_m10v_capture

# 与网页相同构建链的命令行导出
node scripts/export_gr3_m10v_native.mjs builds/gr3-test
node scripts/export_gr3_m10v_native.mjs builds/gr3x-test --model=gr3x
```

完整样本测试需要本机官方固件；部分兼容回归还需要单独准备参考样本与运行时。官方输入、`.venv/`、`.runtime/`、`data/` 和 `builds/` 均不提交到 Git。

| 目录 | 内容 |
| --- | --- |
| `web/` | 统一工作台、胶卷目录和说明页 |
| `node/` | HTTP 服务、固件身份检查、构建与独立回读 |
| `native/gr3/` | 原生胶卷、菜单、图标、持久化与 JPEG 处理 |
| `scripts/` | ARM 编译、资源生成、导出与分析工具 |
| `tests/` | 原生和 ARM 执行测试 |
| `docs/` | 设计、逆向证据与验收记录 |

[机内功能验收](docs/testing/gr3-m10v-native-library.md) · [发布前检查](docs/testing/release-review-2026-10-14.md) · [第三方说明](THIRD_PARTY_NOTICES.md)

## 致谢

感谢 **gr-custom-tool、GRLife、gr3-film-mods、darkslide-gr** 在 GR 固件研究、胶片模拟与定制工具方面的公开探索。

M10V 的界面与胶卷图标采用自己的设计。使用和移植的第三方代码、数据保留对应来源与许可；详情见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。项目源码采用 [GPL-2.0](LICENSE)。

---

<div align="center"><sub>从相机里的一个名字，到你自己的影像工作台。</sub></div>

GR II、GR IV 与 GR III 使用一致的三步工作台：导入固件 → 设置方案 → 保存固件，并共享方案清单与机型导航。GR II 当前展示只读组件与资源，修改固件保存保持禁用；GR IV 支持五槽胶卷与配方/原厂预设工作流，参考编辑器单独保留。

GR IIIx 1.60 已开放与 GR III 相同的原生胶卷、机内 FN 调节、SD 换卷、时间戳、画幅、水平仪、颗粒、RAW 降噪、调试及版本适配；配方与原厂预设工具也可导出。以独立差异移植保留 GR IIIx 的型号和完整 CPU，不将 GR III 的型号数据刷入 IIIx。构建与 ARM 检查不代表 IIIx 实机验收。

GR III 2.10 的胶卷库在 Custom2 后提供五个独立胶卷位置，保留全部原厂预设，沿用已有五槽存档与 FILMS.M10。新槽 FN 提供该胶卷支持的 M10V 参数；原厂参数保留在原厂风格中。GR IIIx／GR IV 保持原有槽位布局。

# GR2013 / GR II 移植与 GitHub 参考加速

适用于原生固件适配、加载链、捕获与页面操作。数字 GR2013（本项目 GR1）、
GR II 与 GR DIGITAL 系列不能混淆。GRKit 的 Linux→RTOS 安装链主要是
III/IV 的参考，不能据其存在给 I/II 假定 Linux、相同 ABI 或同一地址。

## 开始前先找已有证据

- `git worktree list` 找实际开发分支；主工作区可能另有并行的未提交改动。
  仅修改任务所属工作区；用户明确指定的技能文件可以在指定位置更新。
- 查项目的 `docs/research/gr1-gr2-official-evidence-2026-10-20.md`、
  `gr2-checksum-loader-2026-10-20.md`、`gr2-native-memory-capture-2026-10-20.md`、
  `gr2-clarity-hdf-2026-10-21.md`、`gr2-native-detail-2026-10-22.md`。
  文件不存在时定位拥有它的 worktree，不把文档计划当实现证据。
- 复用已有官方输入 SHA、原指令、加载映射和探针。GR II 当前原生研究为
  ARMv4T/BE32/soft-float；GR III 的小端 widget、函数地址、属性布局不可直接搬用。
  汇编和模拟的 CPU 型号只是执行模型，不等于物理硬件鉴定。
- 页面只读、离线原生实现、可打包、真机验收是不同层级。研究有进展不能
  自动开放网页导出；未知接口继续研究，不直接归为底层不支持。

## GitHub 项目分流

先核实实际 checkout 的 commit、完整文件树和许可。搜索摘要可能过时；有
GitHub 页面不等于有实现源码。区分可复用源码、发布二进制、研究记录和功能介绍。

2026-10-23 已检查的起点（重用前检查是否更新）：

| 项目 | 固定研究版本 | 用途及边界 |
| --- | --- | --- |
| [FRAME-GR2](https://github.com/Lyle-xub/FRAME-GR2) | `384cd8849ff93a69800c4c64886404262524f389` | 当时仅 README/docs/SVG，没有固件实现源码或根许可；WNX-L1 发布说明含早期加载器优化、画幅和 RAW 编辑线索。可用发布固件做定位差异，不能声称已获得开源实现。 |
| [ricoh-gr2-boot-screen-mod](https://github.com/lc2425150/ricoh-gr2-boot-screen-mod) | `d99b561620973c29e86c65ea74aa12f777f4edeb` | 有工具、TTL、作业表及资源研究。`web-tool/LICENSE` 为 MIT，不默认覆盖根目录其他内容。其工具未解决更新校验，SD 脚本参数和回滚描述未做设备闭环。 |
| [grfs](https://github.com/jkbrzt/grfs) | 复用时固定 SHA | MIT、GR II HTTP 照片只读访问；用于连接/文件层，不是固件加载或 ISP 实现。 |

FRAME 当时搜索缓存显示 WN3，实际 git checkout 已是 WNX-L1。以固定提交的
[WNX 说明](https://github.com/Lyle-xub/FRAME-GR2/blob/384cd8849ff93a69800c4c64886404262524f389/docs/firmware/WNX.md)
定位发布物；其作者仍记录偶发额外镜头伸缩未确认修复。功能说明属于作者声明，
不是 M10V 真机证据。研究二进制不能取代本项目官方输入或直接成为交付物。

## 固件差异的有效顺序

1. 下载到忽略的研究目录，记录发布 tag、资产名、长度、SHA 和来源链接。
   网络中断保留部分文件，支持时续传。分段下载须检查每段 Content-Range 与长度，合并后核对整体 SHA；未收齐且未核对 SHA 前不调用完整解析器。
   限制重试次数，GitHub API 限流时用普通 git/发布页，不循环打限流接口。
2. 先解包容器，按组件、模块目的地址和原厂范围对齐；不要只对加密 `.frm`
   做逐字节差异。新增/搬移的段与原址 Hook 分开记录，避免重定位造成大量假差异。
3. 参考固件可能把早期模块尾部当临时搬运区，随后被正常模块覆盖。此时按逻辑记录编号与相同目的地址比较，并单列阶段性重叠、扩展段及未匹配范围；不能把临时尾部误配为后续模块代码，也不能为接受参考布局而放宽本项目生产加载门禁。
4. 优先看启动搬运/清零、堆与对象尺寸、早期入口和捕获/菜单跳转，再看功能数据。
   对差异点追踪原调用者、所有权、退出和失败路径；不要整份固件反复线性反汇编。
5. 将第三方地址/行为当线索，在本项目精确官方输入上验证相关原指令。保留
   来源与许可；不执行下载的安装脚本、不启用设备、不复制无许可实现作为自有源码。
6. 已经证明的容器、校验或分配器合同直接复用。可用 `scripts/compare_gr2_reference.mjs` 在有该脚本的分支生成按目的地址对齐的离线差异；仅接受其固定发布 SHA，保持官方输入身份检查。新增探针应回答尚未解决的
   问题，保存可重跑证据；已通过不等于物理缓存、DMA、时序和中断已验证。

## 验证与效率

开发时先跑受影响的语义、ABI 或原厂路径测试；共享 ABI/加载/内存/捕获集成节点
再扩大回归。只更新研究或技能不跑固件全套。完整发布验证仍遵守回归索引和发布门槛。

GR II 常用入口（需在对应分支核实文件存在）：

- 加载/校验：`tests/test_unity_update.py`、`test_unity_runtime.py`、
  `test_gr2_update.py`、`test_gr2_component.py`。
- 原厂合同：`scripts/analyze_gr2_native_contract.py`、
  `scripts/analyze_unity_runtime.py`、`tests/test_gr2_native_contract.py`。
- 菜单/存档：`test_gr2_detail.py`、`test_gr2_settings.py`、`test_gr2_sd.py`、
  `test_gr2_storage.py`；捕获和 HDF 使用对应 `test_gr2_capture*`、`test_gr2_hdf*`。
- 构建：`scripts/build_gr2_runtime.py`、`build_gr2_component.py`。研究组件、
  完整 `.frm` 和最终独立审计各有门禁，不能用其中一个替代其余层。

记录实际命令、数量和日志；全套启动后新增的用例或断言单独运行并注明覆盖范围。
遇到模拟指令预算耗尽，先定位停在哪个有限工作/等待/错误路径；不能只提高预算
掩盖死循环。指令数量、CPU 合成显示和模拟成功都不能宣称真机延迟或像素一致。

移植参考不得减少 M10V 的槽位、胶卷、存档兼容或网页操作。用户已批准直接实施
时连续推进，不把每个研究批次变成再次征求确认。

## GR II 实验工作台链（2026-10-23）

在有 `node/gr2-native-library.mjs` 的分支，`/gr2/` 与
`scripts/export_gr2_experimental.mjs NEW_DIRECTORY [configuration.json]`
复用同一生成器。先绑定官方源、五槽配置、原生/构建脚本/Node/LUT 指纹，再运行
原 BE32 构建器；独立重建补丁组件后才进入完整 Unity 容器封装、再次解包回读。
资源、验证开关、入口和延迟加载记录逐字节保持。保留研究层原门禁，额外收据
`experimental_offline`、`hardware_verified:false`、`release_ready:false` 不能解释为真机可用。
初始 HDF=0；第一版强度在机内独立菜单设置，不静默丢弃网页非零值。

用户明确要先出迭代第一版时，可先交付已实现能力的离线候选，同时列出尚待开发和
尚待真机验证项；不要继续等完整功能逆向才接页面，也不能因此关闭校验。
新增机型首页同时保留 `/changelog/` 等既有入口，并跑共享 server/历史页回归。
首个浏览器实际闭环包括导入、预检、源码变化使旧预检失效、构建和下载摘要对齐；
只看到五槽组件不算完成。产物与收据放忽略目录，避免混入原厂或第三方固件。

跨机型页面对齐优先复用 GR3 的共享 CSS、品牌导航、胶卷 `.workspace` 和 picker，
不另做浅色临时界面。公共 `navigation.js` 会重建 header/nav；页面不可依赖被替换的
菜单 ID，需使用稳定容器委托或共享导航真源，并实测加载脚本。GR II SD 入口使用
`/gr2/#sd` 保留机型，不默认跳入 GR3。样式一致不等于照搬 GR3 的桥接、解锁或未移植
能力。编辑→撤销/重做→切槽→构建→收据摘要，以及移动端溢出均需实际浏览器检查。

GR2013 参考核验补充（2026-10-23）：旧 crypto512/ricohdec 链接当日404；可访问的
[jokob/ricohdec](https://github.com/jokob/ricohdec/tree/4be717c9e6fcbd975b79a7d3887c272da5bfd4a7)
固定提交为4be717c9e6fcbd975b79a7d3887c272da5bfd4a7，只有Makefile/README/C解包器，
未列根许可。README明确示范GR5.01，两层组件尺寸匹配，但不是原生功能实现；仅作
格式线索，不能直接复制无许可代码。Theta notebook同样只是UNITY去混淆参考。
GR1单模块加载、长度检查、启动post-load及C堆边界必须逐项执行自己的原指令；
同样的启动入口地址不意味着内部调用相同。当前 GR1 原厂 C heap 与 GR2 不同，
模拟预留成功仅证明创建顺序和边界，不证明全机空闲内存或峰值需求满足。
可在已有此实现的分支使用 tests/test_gr1_startup.py、test_gr1_native_contract.py 和
scripts/analyze_gr1_native_contract.py 重跑；具体地址、身份与范围见项目GR1研究记录。

GR2013 原生服务补充（2026-10-23）：系统 region 初始化、RTOS create/allocate/free
和 stdio parser 已有独立原指令探针，`native/gr1/m10v_services.c` 的 BE32 编译桥可在
合成单池环境调用原厂实现。系统池与 C heap 分开，池区包含元数据，不能把整个池
视为可注入空闲空间。JPEG wrapper/config 的平面与行距算术可独立验证，但不能从
描述符吻合推导 RAW 隔离、生产完成或 DMA/cache 所有权。用实际 wrapper 的 BL
调用者定位 owner；GR2 owner 的短前缀在 GR1 会命中语义不同的函数，唯一短命中
仍不足以确认移植入口。相关测试 test_gr1_native_contract.py、test_gr1_native_bridge.py；
桥的 scratch 链接地址仅供 CPU 测试，尚无 GR1 安装或修改 FRM 产物。
GR2013 JPEG owner 已由实际 BL 调用者定位并执行三类句柄/尺寸分派；编码后
`A027E090→A00DAF04` 是输出大小 setter，不能按名字或相邻函数认作释放。
其 wrapper 编码长度写回 descriptor+0x10；模拟返回值也必须服从该机型原指令，
不能复制 GR2 探针的返回字段。owner 返回仍持有源句柄，外层生命周期需另外追踪。

### GR2013 图像、首次存档和原厂 UI 的已验证入口

在含本次 GR1 适配代码的分支，先读
`docs/research/gr1-native-runtime-2026-10-23.md`；它补充前述“外层尚待追踪”记录。
以下均是身份锁定 GR2013 5.01 的 CPU 证据，不能替代设备验收：

| 检索目标 | 已验证入口/判断条件 | 回归入口 |
| --- | --- | --- |
| 图像回收 | `A027DF3C`先清源槽，`A00DA9E0`减引用，最后引用才释放像素；`A027E090→A00DAF04`仍只是大小setter | `tests.test_gr1_capture_lifetime` |
| IMG 归属 | 录制固定池25块，每块`F91C+8`；构造`A00DC388`，池指针`A011F0DC`；核对 fixed 表成员、IMG magic/kind及精确块边界 | `tests.test_gr1_capture_guard` |
| RAW隔离 | 保护 context+`1CC/1D0/1D4/1D8`的像素与元数据；1D4生产角色仍待研究。JPEG输出也必须排除RAW标签及RAW重叠，不能只检查输入YUV | 同上；RAW-only/并发/生产完成/cache仍未证明 |
| 首次建档 | `H:/M10V5A.bin`、`H:/M10V5B.bin`均经原findfirst确证缺失（errno3）才创建；已有损坏档或介质错误不能当缺档 | `tests.test_gr1_storage`、`tests.test_gr1_journal` |
| FILE/FAT差异 | GR1 FILE控制块元数据池+`20`；H:volume=`A06A5CB8`，flags+`2E68`、盘符+`2E6C`；实际DTA name+`472`、size+`46C` | `scripts.analyze_gr1_native_contract` 的 `probe_fat_directory`/`probe_sd_file_lifecycle` |
| 时钟 | `A0032CD4`返回秒数，0秒有效；compact驱动`A0058338`，新桥验证公历日期，非法结果不写输出 | `tests.test_gr1_clock` |
| 原厂文字与图层 | 语言getter`A03710A0`，图形getter`A036A196`，字体init`A0365D9E`，文字draw`A0388010`；图层attach/member/detach=`A03658D4/A03659C2/A036529E` | `tests.test_gr1_ui` |
| 设置页与存档 | 独立GR1后端接五槽/时间戳；原事件dispatcher=`A03656AC`。卸载合法地将保留根菜单+`24`置dirty，要求重绘，不是根对象损坏 | `tests.test_gr1_settings` |

可复用固定兼容闭包的**无地址纯算法、五槽104字节线格式和控制器**；文件、池、
图层、菜单和时钟地址必须来自 GR1。BE 内存 CRC与LE文件 CRC分别计算。
完整存档回归应经过原 FILE 包装器，不能只把存档回调全部换成成功替身。
字体回归应加载自身官方资源并执行原字形引擎；缺字体时整页拒绝且不清屏。

`build_gr1_runtime.py` 当前产生**未安装的离线运行体**，`A0752000..A07C0000`
只是模拟预留范围；`can_package=false`。`/gr1/` 的 ZIP是开发包，不能刷机，
不能把构建/页面可点击升级为启动、拍摄或SD激活已完成。四个ASCII基础设置视图
已有原绘图证据，物理按键翻译、图标/中文/详情页、启动安装仍继续实现。
网页重新导入来源失败时也应使旧预检/下载失效，不能保留上一次可下载结果。

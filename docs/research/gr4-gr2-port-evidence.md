# GR IV / GR II 移植证据

2026-10-14。仅记录本地官方输入的离线证据，不代表相机刷入和成像通过。

## 复现

```sh
python3 scripts/analyze_model_firmware.py bin/fwdc248b-gr4-officical.bin --model gr4 --out data/research/gr4 --extract
node scripts/analyze_gr2_firmware.mjs bin/rg2_v003/rg2_v003.frm --out data/research/gr2 --extract
python3 -m unittest tests.test_model_firmware
node --test node/gr2-firmware.test.mjs
```

输出保持在忽略的 data/ 目录。解析器以文件内容身份识别机型，不依赖输入名称。

## GR IV

官方输入 SHA-256：`a2f664dfca034059eb0fd6e18ab08684c326b4a034d85c164dad7e1ec9b5655f`，38,648,776 字节。内部版本 1.11.10.7。严格解码得到 67,948,280 字节、2,765 帧、13 分区；重用原始压缩帧并重新封装后与输入逐字节一致。

RTOS 为 20,785,856 字节，SHA-256 `a9a9a51530c35819df47dee1cce9f4f560a17eeed1da258950167d282884fce1`，加载基址 `0x53000000`。原生启动复制为 ROM `0x5437b640` → RAM `0x55000000`，长度 `0x57480`。GR3 的复制源和长度不同，RAM 静态地址不能移植。

参考核心已有的菜单证据：列表地址由 `0x533cc78c/0x533cc794` 的 MOVW/MOVT 给出，数量字段在 `0x533cc7a4`；其他数量指令在 `0x533cc8c8`、`0x533bebf0`、`0x53375628`。名称与图标查询入口分别为 `0x5337f824`、`0x53380fac`；色彩 profile 查询入口 `0x53912cf4`，色彩表入口见 `vendor/gr4/gr4_editor/filter_reader.py`。这些是原厂/参考槽位编辑基础，不等于 M10V 原生 65 卷目录已接入。

### 拍摄缓冲 CPU 执行证据

```sh
.venv/bin/python scripts/analyze_gr4_capture.py --rtos data/research/gr4/RTOS.bin --out data/research/gr4/capture-allocation.json
.venv/bin/python -m unittest tests.test_gr4_capture
```

从构造函数的 PC 相对常量确认 recipe 虚表为 `0x53f85050`；虚表第 43 项是分配入口 `0x5370e804`。对官方构造片段 `0x5370ff7c..0x53710084` 与该分配函数执行 Unicorn 检查。Geometry 服务 manager/accessor 及其虚方法被拦截，返回合成的 160×120 缩略尺寸；其余分配算术与描述符写入执行官方 CPU 指令。

主描述符位于 `recipe+0xb0`，format=1，enum 字节=2；模拟 6256×4176/stride6288 和 3120×2088/stride3136 均正确返回。描述符尾部三个 padding 字节没有初始化，保留 A5 哨兵；不能像读取 enumWord 一样将其当成四字节固定值。

两个模拟尺寸下主 Y/C 地址间额外间隔分别为 **905,536 / 451,648 字节**。分配器 `0x5370e928..0x5370e944` 等指令加入 9×16×stride 的工作区，再进行对齐；不是只加固定 64 字节。若据 GR3 参数猜测 GR4 内存布局，会把工作区错误地当成图像平面或产生越界。

拍摄链调用点为 `0x537035c8`，原始 BL 目标 `0x538dd430`。附近的 request 辅助结构偏移由 GR3 的 0x89f8 变为 0x89fc；GR4 的 recipe planner 也不再能通过 GR3 的原始指令序列找到相同入口。因此本证据尚不足以接入 JPEG 运行体；模式准入、完整 request/RAW 生命周期、时钟和持久化需分别追踪。

可定位的候选辅助函数包括 allocator/free `0x538e09b0/0x538e09ec`、cache `0x53a95804`、model root `0x5323ea84` 和 clock `0x533a2584`。这些候选来自正规化指令匹配，尚未验证完整调用契约，不能作为可写 profile 使用。

## GR II 容器与资源

官方输入 SHA-256：`3643850f2ae74ae967eb336794048f554caa1b11d05b8569824d5719f1838331`，14,033,920 字节。UNITY 魔数位于零偏移，总长度和记录数分别为大端字段 `0x20/0x24`。2048 字节容器头中，从 `0x40` 开始每个记录 64 字节：起点以 512 字节块计，长度为字节数，名称占 12 字节，类型/编码字段在记录 `+30/+31`。

| 记录 | 文件偏移 | 大小 | 类型 | 解码后 SHA-256 |
| --- | --- | ---: | --- | --- |
| b01firm6 | 0x800 | 7,896,704 | 分块 XOR | 9e0d291f5b9b74f76a2dd269c4b23fe8f524b5db92b86bf82150d5dc3096abf8 |
| rg2_v001up | 0x788800 | 6,134,784 | 原样嵌套 UNITY | 由 inventory.json 记录 |
| b01firm8 | 嵌套包内 0x800；全文件 0x789000 | 6,132,308 | 分块 XOR | 13fa830bff194679628eb1bb3f233420ee23c4fca3a28c4b650c53692820de95 |

XOR 对每个载荷重置密钥，初值 `0xf8e69612`，每 512 字节加 `0xbe39b193`（模 2^32），逐大端 32 位字异或。嵌套记录本身不能再次直接 XOR。解密再加密，并保留全部头、对齐和尾部字节，完整文件逐字节一致。

b01firm6 的版本字段 `+0x12` 为 `0x0300`，对应 3.00。资源目录从解码文件 `0x786000` 开始，共 121 个 64 字节记录。名称占 32 字节，偏移与长度为记录 `+32/+36` 的大端字段。

**资源偏移相对 512 字节卷头，实际文件位置须加 `0x200`。** 例如 `A:/cpu1/cp1.bin` 的表内地址是 `0x6e9c00`，程序从 `0x6e9e00` 开始，首个 ARM 大端指令是 `0xee110f10`。不加偏移会读到 update.ttl 的尾部。command.txt 和 update.ttl 的正确文件头也独立验证了这一映射。所有资源范围、对齐、重叠及名称均经解析器检查。

资源包括原厂图案、语言字体、固定/校准参数、命令地址表、更新脚本和 CPU1 程序。主 CPU 更新程序内含 ARM/Thumb 大端指令与 SOFTUNE REALOS/ARM 标识；GR3 的 ARM 小端运行体不能直接注入。

## 更新校验调查

两个解码组件头都有 `0x164` 数据长度、`0x168` 文件长度、`0x16c` 校验字段。b01firm6 的值为 `0x787c80/0x787e80/0xa3a80234`；b01firm8 为 `0x5d9054/0x5d9254/0x826a5e33`。程序中的 nUpdateCsum、bCompareCsum、bExecVerify 字符串和相应打印调用确认了字段用途。

目前常规 CRC32、Adler32、字节和、16/32 位加法和及 XOR 均未匹配原厂校验字段。原样往返仅证明容器编码，不证明任何修改后校验有效。未完成算法与执行路径证明前，不提供 GR II 修改固件下载。

## 公开线索与来源

GR II 编码参数的线索来自 [gr2-boot 研究源码](https://github.com/lc2425150/ricoh-gr2-boot-screen-mod/blob/main/tools/gr2boot.py)，研究时 checkout 为 `d99b561620973c29e86c65ea74aa12f777f4edeb`。仓库根未提供复用许可；本项目只采用经过本地字节验证的格式事实，自行实现解析器，未复制该工具源码。其资源读取直接使用表内偏移，本项目额外验证并修正了 512 字节卷头偏移。

[FRAME-GR2](https://github.com/Lyle-xub/FRAME-GR2) 的当前公开仓库仅有发布说明，没有可用于移植的实现源码；不依赖其发布固件来替代官方输入或自有实现。

## 移植状态

容器核验及原样往返已建立。GR4 参考原厂编辑器与 M10V 五槽原生胶卷库是不同路径；GR II 仍需证明修改校验和主程序/图像处理 ABI。已完成的读取能力不能标记成原生功能已复刻。后续证据与验收状态随具体实现更新。

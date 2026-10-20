# GR II 更新校验与加载链进展

2026-10-20。本记录更新同日初查中“修改校验未解决”的状态；不代表原生功能或真机刷入完成。

## 更新载荷校验已建立

从 GR II 官方 b01firm8 的 `0xA003FCE6` 文件检查函数沿调用链定位：读取 512 字节头、检查文件长度与头、由 +0x178 的 bCompareCsum 控制进入加权校验；+0x164 为载荷字节数，+0x16c 为预期校验。累加器与字节位置分别初始化为 0 和头 +0x20 的值，载荷从解码组件文件偏移 512 开始。

公式为：

```text
checksum = sum(payload[i] * (2 + (uint32(initial_position + i) % 6))) mod 2^32
```

GR II `0xA00B0B88` 的原厂 ARM 辅助函数通过乘法倒数计算无符号余 6；调用方再加 2 后与字节相乘。不是 CRC32 或普通字节和。128 KiB 只是读取分块，权重位置跨分块连续递增，不能每块重新从 2 开始。

| 项目 | GR II | GR |
| --- | --- | --- |
| 原厂加权路径 CPU 入口 | 0xA003FD72 | 0xA00546E2 |
| 原厂校验比较指令 | 0xA003FEB8 | 0xA0054828 |
| 原厂余 6 ARM 入口 | 0xA00B0B88 | 0xA00AE644 |
| b01firm6 原厂值 | 0xA3A80234 | 0x7C565038 |
| b01firm8 原厂值 | 0x826A5E33 | 0x7B62E1A9 |

以两机型各自官方 b01firm8 指令执行四个完整载荷，均进入正确比较成功分支。只拦截分配、读文件和释放边界；原始 Thumb 算术、ARM 取模、累计字节数比较与校验比较没有替换。

GR II 还验证了 0、1、3、4、511、512、513、131073 字节，奇数/短读分块、错误预期值、载荷变异、长度不足/多出、字节位置的 32 位回绕。错误值或长度不符均进入拒绝分支。头识别三例保留：原厂相等、低位变化不等、高位变化仍相等。

Node 与 Python 独立实现同一数学规则；Node 导入器现在额外验证两个解码组件的长度与校验，返回各组件校验值和原始开关。没有关闭 bExecVerify、bCompareCsum 或修改原厂策略来规避检查。

复现：

```sh
node --test node/unity-checksum.test.mjs node/gr2-firmware.test.mjs node/gr1-firmware.test.mjs node/unity-firmware.test.mjs
.venv/bin/python -m unittest tests.test_unity_update tests.test_unity_runtime tests.test_gr2_update
.venv/bin/python scripts/analyze_unity_update.py --model gr2 --component data/research/gr2/implementation/b01firm8.bin --out data/research/gr2/implementation/update-proof.json
```

## 加载记录语义已执行，但启动链尚未闭环

GR II 原厂文件加载器 `0xA0040464` 的记录循环位于 `0xA0040538`；GR 对应循环为 `0xA003F0FA`。共 16 条，每条五个大端 u32 字段。

前 15 条：源字段 +512 作为组件文件偏移，按指定长度读入指定目标地址，然后由原厂 ARM 清零函数清除第四/第五字段给出的地址和长度，最后更新加载完成标记。第四/第五字段不是可用空闲空间。

最后一条：先分配临时缓冲并读取载荷；GR II 原厂回调 `0xA0046E92` 把缓冲、目标、长度、清零地址和长度保存到 boot context 的 +0xF4..+0x104。该阶段未直接写入低地址，也未清除最后一条的 aux 区。GR 的同类回调为 `0xA0043E9C`，不能沿用 GR II 地址。

| GR II 原厂记录 | 值 |
| --- | --- |
| 第 0 条文件偏移 / 目标 / 长度 | 0x200 / 0xA0020400 / 0xA46C4 |
| 第 0 条清零地址 / 长度 | 0xA05F5800 / 0xC5700 |
| 第 15 条文件偏移 / 目标 / 长度 | 0x5D5600 / 0x400 / 0x3C54 |
| 第 15 条清零地址 / 长度 | 0x4054 / 0x380C |

CPU 测试使用合成的 16 条记录、文件、目标 RAM 和 boot context，执行原厂循环、清零、回调及完成标记；独立检查源偏移、载荷、前后哨兵、清零边界、最后一条暂存字段和低地址未被提前改写。原厂正式地址清单单独解析，不冒充已经在这些地址上完成实机启动。

短读实验显示：不能只根据加载器返回了落在整体地址范围内的入口值，就认定每个记录都成功。分析器还检查全部 16 个完成标记及每段内容；未来候选审计也必须逐记录检查，不能依赖一个返回地址。

低地址最终提交、启动上下文初始化、更新/boot-ROM 的完整调用顺序和最终跳转仍待追踪；`deferred_commit_proved` 保持 false。此缺口不判定为机型不支持，也不通过模拟一个成功回调来抹掉。

## GR II 正常启动的按记录加载链

通用文件加载器不是正常启动的全部路径。官方 `0xA0020944` 启动编排调用 `0xA0022E28`，后者检查完成标志，并经 `0xA003FB02` 调用存储加载器 `0xA0056722`。该加载器按一个记录索引读取扇区，执行非对齐首尾拷贝、aux 清零、加载完成标记；索引超界或读取失败返回 `0xFFFFFFFF`。

CPU 探针分别验证源偏移 0、1、511、512，长度 1、512、513、1024、1025，首尾哨兵、37 字节 aux 清零、失败读取和无效索引。存储描述符与块读取被替换，原厂扇区运算、memcpy、清零及返回路径执行不变。此处的源偏移相对组件载荷；通用文件加载器则需加上 512 字节头，不能混用。

正常启动探针的模块顺序为 `0,1,4,2,3,5,10,11,8,9,6,12,13,14`。已测试的提前分支也先加载记录 14，再到达共同调用位置 `0xA0020AB4`（原目标 `0xA0023234`）。探针执行原厂分支和调用顺序，各子系统初始化与模块服务返回值为明确的合成边界；尚未证明完整相机启动。记录 14 原本仅 4 字节，因此存在后置原生初始化的研究方向；这里尚未生成补丁或授权任意目标内存。

原厂记录 15 的低地址代码保持原样。不能把按记录加载器的成功，扩大为已证明低地址最终提交或 boot-ROM 更新全过程。

## GR II 原厂更新区容量策略

执行原厂描述符工厂 `0xA005658E`、容量回调 `0xA0056560` 和 NAND 单位计算 `0xA0044036 → 0xA005FD06`，只替换驱动初始化/解锁边界，得到每块 256 扇区 ×512 =131072 字节。

| 组件类型 | 原厂块数 | 追加扇区 | 载荷上限（不含 512 字节头） |
| --- | --- | --- | --- |
| 1，b01firm8 | 64 | 254 | 0x81FC00 / 8,518,656 字节 |
| 2，b01firm6 | 63 | 254 | 0x7FFC00 / 8,387,584 字节 |

测试确认恰好上限返回 0，上限 +1 返回 `0xFFFFFFFF`。没有关闭 `bCheckRomSize`，也没有替换容量计算来接受增大的组件。此证据不涉及实际擦写和 NAND 坏块处理；GR 的容量尚未沿其独立实现证明。

## GR II RTC 原生 ABI

通过原厂 `RTC_GetTime` 字符串及断言交叉定位包装函数 `0xA00341A8`。它调用紧凑驱动读取 `0xA005AE20`，将年（u16）、月/日/时/分/秒（u8）转换为调用者的六个大端 u16，共 12 字节。R0 最终等于秒值；把它当作布尔成功值会在整分钟误判。

`scripts/analyze_gr2_native_contract.py` 执行此原厂包装函数，仅替换 RTC 硬件读取，验证三组日期、输出端序、边界哨兵和被调用者保存寄存器。RTC 就绪/时间有效性、印字渲染与捕获生命周期仍待接入；该项保持 researching。

复现新增证据：

```sh
.venv/bin/python -m unittest tests.test_unity_runtime tests.test_unity_update tests.test_gr2_update tests.test_gr2_native_contract
.venv/bin/python scripts/analyze_unity_runtime.py --model gr2 --component data/research/gr2/implementation/b01firm8.bin --out data/research/gr2/implementation/loader-proof.json
.venv/bin/python scripts/analyze_gr2_native_contract.py --component data/research/gr2/implementation/b01firm8.bin --out data/research/gr2/implementation/native-contract.json
```

## GR II 普通文件读写 ABI

普通文件入口分别是 open `0xA002C70E`、read `0xA002CA98`、write `0xA002CC4A`。更新器的 `0xA00550A4`/`0xA0055252` 等包装函数会根据全局后端模式切换特殊存储读取，不能直接作为配置持久化 API。

原厂 H: 路径打开模式选择已执行到 `fopen` 边界，并在那里停止，没有创建文件：flags 0→`r`，1→`w`，9→`a`，2→`r+`，10→`a+`，0x102→`w+`。媒体状态、锁与就绪检查为合成边界；原始位测试、比较和模式字符串选择没有替换。

原厂读/写包装函数分别执行到完整传输返回：read 调底层 `0xA0065386(buffer,1,count,file)`，write 调 `0xA0065428(buffer,count,1,file)`。后者检查底层项数等于 1，再返回 count 字节。测试使用带正确 magic 的合成句柄、H: 路径及后端数据，校验原始 magic 检查/路径分派、参数顺序、返回值和缓冲哨兵。另以 8 字节请求、3 字节读取加 EOF 边界，确认原厂返回 3 并保留其余缓冲哨兵。文件打开/关闭生命周期、短写与错误恢复、介质挂载、原子持久化仍需继续证明；不能把这组 ABI 测试视为实际 SD 保存成功。

## 还需完成

- 追踪暂存低地址段的最终提交和启动交接。
- 定位原生菜单、持久化、时钟、JPEG 缓冲及内存分配生命周期。
- 证明运行体注入空间、链接地址和更新恢复兼容后，再开放原生固件构建。
- 逐项补齐工作台功能与真机验收；校验算法通过不等于完整功能移植通过。

后续原生内存、启动尾部修正、编译桥及平面契约见 [专项记录](gr2-native-memory-capture-2026-10-20.md)。

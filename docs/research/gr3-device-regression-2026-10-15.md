# GR III 实机故障：上传固件、日志、官方 ARM 与历史对照

日期：2026-10-15。范围：分析用户提供的三个文件，未修改桌面原件、未生成修复固件、未刷机。用户补充确认死机入口是拍摄画面的 ADJ/快捷滤镜列表。

## 1. 样本身份与证据绑定

- 上传固件：`/Users/zhaoo/Desktop/fwdc239b(1).bin`，30,994,620 字节，SHA256 `3a1bcb83915a131bd1d07b7fc97a8adbaa33cbc0a4b29434aae68569af002384`。
- 官方基线：`bin/fwdc239b-gr3-official.bin`，SHA256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`。
- 容器/解码体校验通过。仅 RTOS 分区变化，增长 481,184 字节；原厂 RTOS 范围内只有 27 个 32 位字变化，均为原生库的菜单、资源、图标、拍摄挂钩。其他分区不变。
- 提取的原生模块 478,560 字节。用当前 HEAD 的 halation_core.c（不是工作区尚未提交的新版）、其余现有源码、提取出的初始状态和日志 build_id `5d9a6740` 重编译，**整个模块与上传固件逐字节一致**。因此下面对 capture/menu 源码的解释已绑定实际上传包，不是猜测线上版本。
- 两份 M10VCP 日志均 CRC 有效，build_id 均为 `5d9a6740`；解码器按同一通道选择最新快照，不把两页中的重复事件算成额外拍摄。

初始五槽胶卷 ID 为 1、64、54、37、33；第五槽是 800T，grain=2、soft=0、gain=8、spread=8、threshold=0、profile=3。**时间戳初始值为关闭。** 机内有效 M10V2A/B 记录仍会覆盖编译初值；此次没有这些持久化记录，不能声称初值就是每张照片的运行值。

## 2. 红晕/颗粒不生效：捕获链在渲染前退出

日志有六组 capture.before(100) → capture.after(101)，返回值全为 `0xfffffff9`，有符号解释为 **-7**。没有 capture.render.before(110) 或 capture.render.after(111)。

`native/gr3/m10v_library_capture.c` 的 -7 只有一个出口：

```c
if (state.stamp || state.slots[slot].grain) {
    ...
    if (!ram(service, 0x1a0) || !clock(service, time)) return -7;
}
```

因此不是高光识别算法强度不够，而是整个 `m10v_library_render()` 没有执行。该函数承担色彩、800T 红晕、软件颗粒、柔光和时间戳；此出口会一起跳过它们。原厂 tone 的成像仍会继续，屏幕显示自定义卷名不代表该胶卷的 M10V 像素处理运行了。

进一步逆向官方代码：

- `0x5320b97c` 返回固定模型对象 `0x55064dc8`，地址满足当前 ram 检查。
- `0x532b36cc` 并非无条件读硬件时钟：它先读取对象 `+0x18c` 的属性 `0x48`（有效地址为对象 `+0x2ac`），只有值等于 1 才复制对象 `+0x3c0` 的日期并返回 1，否则返回 0。
- 用官方 ARM 指令执行该 getter 与属性/日期辅助函数：属性 0、1、2 分别返回 0、1、0；只有 1 会填充日期。只替换了断言终点，没有用假时钟返回值替代 getter。
- 日志未记录属性值，不能断言实机是 0 还是 2，也不能解释其在拍摄线程为何不可用；可以确认调用失败被提升为整条效果链失败。

现有 `tests/test_gr3_m10v_capture.py` 在 `0x532b36cc` 直接写入日期并固定返回 1，屏蔽了这个真实分支。早期 `daily/gr3-800t` 捕获桥没有这个时钟依赖，这解释了独立红晕能工作、组合颗粒后却整体失效的一条具体回归路径。

修复要求：颗粒 seed 不应强依赖 UI 日期就绪状态；时间不可用不能跳过无关色彩/红晕/质感。时间戳本身需可靠日期来源、明确的不可用处理与诊断，不能用全零/假日期冒充成功。需要真实 getter 的失败分支回归，不能继续只测 mock 返回 1。

## 3. ADJ 末尾死机：遗漏第二套消费者，私有 ID 写入原厂状态

全局模型函数被修改：`0x532c2a9c` 把列表从 12 项扩为 13 项，`0x532c2c80` 把索引12映射为私有 ID128（M10V Library）。但拦截 focus/confirm/key/enter 的是 `0x531ab914`、`0x531ac24c`、`0x531ac270`、`0x531ac140` 这一套 ImageControlController 路径。

另外一套回调 `0x531a0ba0` 完全未打补丁，也调用同一组全局 count/index。真实指令链：

```
0x531a0bbc → count() = 13
0x531a0bf8 → index(12) = 128
0x531a0c20 → stock setter 0x532c26c0(model, 128)
0x532c27e8 → 0x5327b394
0x5327b3a4 → 把 128 写入原厂设置对象 +0x1c2
0x5327b3a8 → apply-all 0x532750f8
```

本次执行上传 RTOS 的真实回调、count/index、setter：**原厂 tone 字段确实被写成128**；官方 RTOS 对相同索引12只写入 Back 状态1，不修改 tone。替身范围是模型 getter、状态服务和 apply-all 后续硬件行为；不存在“用 mock setter 假装写入”的问题。

这与用户确认的 ADJ 操作入口及“列表尾部黑屏”高度吻合，是明确的集成缺陷。仍须区分：已复现错误写入，尚未执行完整相机线程/ISP/显示链到真实黑屏，故不能宣称真机故障已修复或唯一原因已穷尽。

历史 `docs/research/gr3-menu-crash-2026-10-14.md` 主要验证 `0x531ab914` 和 `0x531ac074` 的主菜单刷新；那些成功结果没有覆盖此回调。当前日志只包围已挂钩的菜单入口，ADJ 漏径也会漏日志。此次只提供 CP 两页，不能据此断言卡上不存在 MN 文件。

修复要求：明确库入口属于哪个 controller；要么完整接管 ADJ 的进入/焦点/确认/返回/退出，要么让 ADJ 保持原厂12项并提供另一条可达库入口。不能只增加全局 count。所有消费者都必须保证私有128及144+/256+胶卷 ID 不进入原厂 tone；修复名称/图标不能解决这个缺陷。

## 4. 胶卷库、机内参数与旧版菜单不是同一实现

上传模块包含65卷、换卷、颗粒、柔光、时间戳和四项800T参数逻辑，并非只有图标资源。新路径是 `M10V Library → Choose Slot / Choose Film / Grain / Soft Diffusion / Timestamp / 800T Halation`。但 ADJ 漏径无法正确进入该私有页面，功能存在于二进制不等于用户能使用。

独立800T历史有两种机制：一度复用 tone18 的五个原厂滑杆；之后通过 `scripts/build_gr3_menu_patches.py` 在详细设置表追加五项独立控制。原生库改为私有状态64字节和独立库子菜单，并未把那五项补丁一并安装。因此在原厂滤镜详细页找不到“红晕强度/扩散范围”，不能用旧版操作说明解释现包。

## 5. 画幅、水平仪、原厂负片颗粒根本没有合入这个包

`web/gr3/studio.js`：profile=native 时，prepare/build 只发 `configuration + debug_mode` 到 `/native-library/*`；profile=custom 才把 features/negativeGrainMenu 等发到 `/edit/*`。切到胶卷库会把 features 收为 film，其他项保存在 toolFeaturesDraft。后端 `node/gr3-native-library.mjs` / `gr3-m10v-native-build.mjs` 直接从官方基线构建原生库，未组合 `gr3-customization.mjs` 的补丁。

因此这是两条导出路径互斥，不是“所有功能已经叠加，只是相机不执行”。上传包27个原厂改字点与此一致。

原厂负片颗粒直接字节证据：

| 地址 | 官方与上传包均为 | 应有补丁 |
| --- | --- | --- |
| 0x53b348c0 | 9项（09000000） | 10项 |
| 0x53b3501e | 0000 | 020f：颗粒条目15 |

`node/gr3-stock-presets.mjs` 和 `darkslide-gr/darkslide/grain_menu.py` 已有对应实现，但当前原生导出没调用。它与M10V软件颗粒是两种功能，不能互相替代验收。

时间戳另有两层问题：本包默认关闭；若用户机内开启，当前日期门禁还可能让整个渲染退出。不能把“时间戳代码存在”说成实机已实现。

## 6. 历史与其他项目的可用参考

- `daily/gr3-800t`：4991772接入捕获，5bd656f修正真实JPEG前缓冲，之后有强度/色彩优化。适合复核实际捕获桥和独立参数，不应整包叠加到原生库：同一捕获挂钩、扩展区和状态所有权需先统一。
- 当前72303d8引入统一UI和原生库；f3c37c7补SD日志。现有已提交历史把多个阶段压在首次导入中，需结合 docs/research 和 builds 的产物证据，不应把文档中的旧测试都当成当前包验收。
- `gr3-film-mods/FINDINGS.md` §47–48：曾出现颗粒参数与文件标记都正确、实际没有颗粒，原因是 `0x535131c0` 处理计划门禁；v29调整后文档记录用户确认颗粒出现。这证明必须验证最终处理阶段。该项目使用追加tone25+，M10V使用五个原厂tone代理，补丁不能原地址照搬后声称等价。
- 其§50–52画幅历史还记录v32实机取景比例错误、闪烁，v33后续修正未确认实机。可参考消费路径，不把“有实现”误认为“已验证稳定”。
- `gr-custom-tool` 当前主线是GR IV；适合参考构建隔离、资源核验、配置回读，不可移植GR IV地址到GR III。
- 历史GRLife五项组合曾逐字节重建成功，见 `gr3-grlife-implementation-evidence.md`；那是另一套兼容运行时，不能证明现原生库包含同样功能。

## 7. 修复顺序与验收条件

1. 先修 ADJ 私有ID泄漏；覆盖索引11/12/13、正反向循环、确认/取消、菜单与ADJ切换，并跟踪所有原厂tone写入。
2. 拆除颗粒对日期成功的硬依赖；执行上传状态（800T+grain2）、日期不可用、日期可用、stamp开关组合，确认render事件到达及像素改变。
3. 让库入口在用户实际操作界面可达，验证换卷、四项光晕、颗粒、重启持久化。旧M10V状态覆盖新默认值也要可见。
4. 合并导出配置与补丁规划：同一最终包明确包含哪些功能；对共享代码区、资源ID、全局函数及原厂设置写入检测冲突，不用两个独立固件的“各自通过”替代组合验收。
5. 再逐项验证画幅/JPEG尺寸/取景/RAW，水平仪，原厂负片颗粒，以及与800T同时开启的场景。

本轮输出为逆向证据与复现脚本，不是可刷修复包。已有未提交800T核心优化保持原样。

## 8. 可复核产物

`builds/gr3-device-audit-20261015/`：inventory.json、logs.json、binary-diff.json、reconstruction.json、arm-probes.json，official/uploaded-rtos.bin 与 reconstructed 模块/manifest。

复现命令（已执行成功）：

```
python3 scripts/read_gr3_debug_log.py /Users/zhaoo/Desktop/M10VCP0.BIN /Users/zhaoo/Desktop/M10VCP1.BIN
.venv/bin/python scripts/analyze_gr3_device_regression.py builds/gr3-device-audit-20261015
```

新增脚本只读提取后的RTOS并写分析JSON，不生成固件。脚本使用Unicorn；GUI模型/硬件末端替身和时钟受控输入边界已写入结果。未对未修改的产品代码运行全量测试，也没有实机修复验收。

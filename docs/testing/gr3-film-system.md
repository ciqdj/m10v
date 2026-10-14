# GR III 六槽胶片研究验证（2026-10-13）

**状态：离线研究候选；不接入 m10v 导出、SD 写入或刷机。** 当前缺少机内独立参数保存、RAW 值所有权、回放与返回原厂的完整验证。

在用户本机的精确 GR III 2.10 官方包上，用 `gr3-film-mods` 固定的 v13c 六槽追加方案，以及 v16 中不依赖 GR IV 表的 RAW 显影/EXIF 两个函数构建。为了不覆盖原厂 Cross Processing 曲线，将 RAW/EXIF 新代码和表放在增长的 16 KiB RTOS 尾部。构建脚本固定上游源码散列；GR IV MultiAxial 激活表未提供，也未用假表绕过。

复现命令（需要同级 `gr3-film-mods`、`gr-custom-tool`、官方 `fwdc239b.bin` 与 Homebrew LLVM）：

```sh
.venv/bin/python scripts/build_gr3_six_appended_research.py
node scripts/audit_gr3_six_appended.mjs fwdc239b.bin builds/gr3-extension-validation/six-appended-rawdev-research.bin
```

独立回读结果：候选 SHA-256 `f809f2a5045d00c6efc58f5a3b5e6c8211adf8f301642d537c877ac27e740763`，RTOS 增长 16384 字节，只有 RTOS/ICONBIN 变化；外层与解码和校验均通过，更新器保护区和版本字与官方一致。拍摄和 RAW 显影模式数量均为18，RAW 选项最大容量21，六个新增 tone=25..30，RAW enum=13..18，MakerNote ImageTone=0x10C..0x111。首个仅追加六槽的 v13c 候选 RAW 数量仍为12，故本次明确补上该消费者。

2026-10-13 再次从目录中的官方包重建，候选 SHA 保持一致。审计增加了六个拍摄菜单消费者共用索引表的指针与逐字节内容检查：原厂十二项顺序保持为 `11,12,13,14,15,16,22,17,18,19,20,21`，后接 `25..30`。同时核对五处记录分配仍是 `0xB28`，三个 tone 存储、save-all、load、reset 和 AppData FS 读写入口均与官方字节相同。这直接证明当前研究候选**没有**独立机内胶片参数空间或生命周期钩子；不能因主机侧 `M10VFSET` 格式存在而称其已持久化。

这些检查验证了静态容量、映射表和容器，不证明相机参数写入/回读。v13c 让六款胶片共用 Standard 的九项参数；本地新增 `M10VFSET` 主机编码/解码格式能处理坏长度、CRC、重排与移除，但**没有机内 FS 读写或生命周期 hook**。v26/v27 的独立参数与 RAW 值、回放改进只有研究说明，公开源码没有构建器，当前脚本未复刻它们。未知私有 ID 的相机原生消费者也仍需逐路径证明安全回退。因此候选既不在 UI 中展示为完成，也不进入下载路由。

对官方 RTOS 的 ARM 反汇编另核对：`0x5324B338`、`0x5324B400`、`0x5324B4A4`、`0x5324B5B8`、`0x5324B6E0` 五处均为 `movw r1,#0xB28` 的记录分配；`0x5327B3A4/C4/E4` 是三个设置的 tone 存储；`0x5323F274` 为 save-all 入口，`0x5324B42C` 为 load 退出，`0x5326CC40` 为重设入口。它们提供了待验证的 hook 位置，尚不证明新代码的调用约定、FS 失败处理或断电恢复。上游 §44a 只列四处记录分配，因此第五处也必须在自有实现中解释，不能照抄数量。

进一步反汇编确定：save-all `0x5323F274` 接收记录所有者 `r0`，先通过 `0x53828014` 取得 AppData 对象，再把 key 0、key 1、key 2..8、key 9、key 10 顺序交给 `0x53826C54`；记录写入大小是 `0xB26`。AppData 写包装器最终按 `(fs, name, size, src)` 调用 `0x53825FA8`，读包装器按 `(fs, name, size, dst)` 调用 `0x53825648`。这些调用约定来自原厂 ARM 指令；但 `0x53826BDC` 的路径生成仅覆盖 AppData 的有限键，私有 FILMDATA 文件必须有独立路径和完整写入、回读、损坏恢复验证。单改主机文件格式或扩大记录分配都不足以保证安全回到原厂固件。

六款样本中的 Classic Neg 数据来自上游项目，保留其非商业共享许可边界；此研究候选仅在本机忽略目录，仓库不分发固件或拟合数据。

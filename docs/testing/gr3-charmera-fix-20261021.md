# Charmera 显示与取景修复 C03

用户本轮明确授权“修复后直接发布”，覆盖默认的等待相机验收门槛。本包状态 `RELEASE_AUTHORIZED_CAMERA_UNTESTED`，不代表相机实测通过。

基线为已上线 `c20140e2cbc48a9f13e305fd70c3830712459d77`，本次使用独立工作树，不夹带原目录中正在进行的 A/B 改动。构建沿网页同一 `prepareNative/generateNative` 链路，GR III 2.10 官方输入 SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`。

## 产物

- [C03 ZIP](../../builds/m10v-charmera-gr3-20261021-c03/m10v-charmera-gr3-20261021-c03.zip)
- [安装、复核和恢复](gr3-charmera-fix-20261021.txt)
- [影响矩阵及执行范围](gr3-charmera-fix-20261021-plan.md)

| 产物 | SHA-256 |
|---|---|
| ZIP | `e0ce7d3cd7c99b73a7e740ce861617bb201c3b4b5f25a524f0dc50de875b5e02` |
| fw/fwdc239b.bin | `24a20bb53bf943ac2d48f3bba9aaeb514cdaedfbfe2405d758ea9705f0eb174c` |
| SD/M10V/FILMS.M10 | `9d781d9bfb823f6316ee66320895bd10b71cf54718e9c45162d8f465f583f221` |

包内保存源指纹、配置、完整构建收据与清单。124个源指纹及 ZIP 每项 SHA 回读一致，135项 Hook 校验通过，`live_color=true`、HDF功能保留且初始0，画幅/水平仪/负片颗粒保留，RAW NR stock，debug关闭。现有存档优先于编译默认值。

runtime 915648 bytes，RTOS增长934656 bytes；新增颜色资源35584 bytes。组合构建和独立审计共用960 KiB上限，C03余量48384 bytes。预镜像、ROM只读、区段、指针和最终解码校验均保留。

## 根因与修改

1. 详细参数把枚举当颗粒滑杆，显示OFF刻度和单字母。使用原厂资源值行API，显示四色名称和色块，专用四色刻度保持0..3，独立校验每张RGBA和滑杆重定位。资源756..760（无SD构建750..754）不重排已有资源。
2. 胶卷库的展示函数拒绝大于288的ID，289被清为空。显式接纳Charmera，完整名称和120×196卡片恢复；分配失败使用755号小图标，不再计算越界的670+289。
3. 实时ISP配置只接纳33..78。Charmera按当前已提交槽位的颜色先合并亮度，再应用单调阶跃调色；不读取或写入RAW/live像素，不添加逐帧I/O。Still流程显式拒绝该预览近似的完成标志，保留原CPU逐对YUV二值调色与逐张冻结。

## 验证

- 新增失败复现：289槽图标为0，四种颜色的Live配置完全相同，颜色行无专用资源。修复后对应测试通过。
- 原厂详细菜单、Live Make/packer、native look、recipe交接、settings view：75测试通过。
- 胶卷/ARM、SD、设置控制器、逐张快照及RAW归属/释放/集成保护：108测试通过。
- 从最终BIN解码执行：五个新增tone各验证四种颜色、重复刷新不累积、拍摄信息不改；另执行新增tone静态快照与原厂tone隔离，共3测试通过。
- 追加Charmera四色Still完成标志/冻结验证1通过；原厂图标布局复核1通过。
- 完整 `npm test`：303通过、8跳过、0失败；独立代码审查未发现可操作问题。发布保护18项中17项首轮通过，中断回退项因本机并发负载超过5秒等待窗，单独重跑通过；没有修改其断言或超时。
- 独立工作树初期缺失本地忽略的运行时/样本，补齐后完整重跑；没有为通过测试删校验或更改已有合法行为。changelog、新SD合同和diff检查通过。发布终态见本次发布记录。

| 分类 | 结果 |
|---|---|
| changed | 可读四色参数、胶卷库名称/卡片/小图、GR III Charmera实时色调近似 |
| preserved | 47款目录/稳定ID、104字节v4存档、其他槽、原厂预设、逐张冻结、JPEG调色、RAW、HDF与既有按键 |
| known-broken | 已有A/B物理键实机反馈不由此修复；原机同场景色彩标定未完成 |
| untested | 相机刷入、LCD实际显示、帧率/切换耗时、预览与JPEG阈值一致性、实拍RAW+JPEG/连拍/重启；IIIx仅离线显示/构建回归，GR IV不新增Charmera |

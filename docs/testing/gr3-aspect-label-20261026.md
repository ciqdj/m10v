# XPan / 6x7 取景标签 — 2026-10-26

基线：`d9b5a8933dc8a162741761e039ad1646c192ae36`；分支 `daily/aspect-viewfinder-labels`。

本次用户明确要求：不用全量测试，只测试风险项和新增功能，完成后直接合并 main、发布宝塔与 GitHub。按该指令执行发布，不将直接发布授权记为相机实测通过。

## 改动与保护范围

- 新增：M10V 原生胶卷组合启用画幅扩展时，XPan / 6x7 在既有取景遮罩刷新路径绘制对应标签；原厂画幅图标339的外框逐像素保留，字形取自原厂33/258/299/609/610图标。
- 实现：60×40只读RGBA图标，原生同步绘制器；裁剪到有效刷新区域。图标ID追加到胶卷与焦段资源后，组合器绑定私有记录，未启用扩展时不绘制。
- 保留：原厂3:2/1:1/4:3显示、画幅遮罩、28–50mm焦段图标、胶卷图标、JPEG/DNG几何和AF逻辑。共享图标目录新增两项，不改既有身份。
- 影响：GR III／IIIx共用原生组合链。GR III候选实际构建和执行ARM验证；IIIx通过发布链的独立模型与CPU保留检查。GR IV源码未改。
- 未验证：真机标签位置、DISP/菜单/回放切换的刷新时序、实机半按/放大/录像及360×240显示的视觉比例；这些不以ARM仿真代替。

## 专项证据

- `tests.test_gr3_aspect_indicator`：30项通过，覆盖图标映射、可见性、两种画布尺寸及原厂外框像素/字形可重建性；包含继承的画幅行为检查。
- 最终BIN：`tests.test_gr3_aspect_indicator_final`通过，直接执行安装后的取景标签路径和原生RGBA绘制器，回读XPan与6x7全部不透明像素，检查有效断言、SP恢复及无临时图标分配。
- 最终BIN：`tests.test_gr3_aspect tests.test_gr3_aspect_dng`：24项通过，检查裁切身份、遮罩、各焦段尺寸及DNG逻辑。遮罩单元隔离图标服务；图标实绘由上一项独立覆盖。
- 最终RTOS：`tests.test_gr3_zoom_indicator_arm`：5项通过，含原厂/自定义焦段、胶卷目录、旋转、分配失败及释放。
- `tests.test_gr3_zoom_icon_style_arm tests.test_gr3_zoom_rollback tests.test_gr3_zoom_rollback_guard_arm`：6项通过。
- 候选经现有网页同源preflight/compiler/composer/auditor构建：官方输入身份、源码/配置指纹、资源读回、157个Hook、最终封包校验通过。
- 发布前执行changelog与现有部署保护检查；发布时以Actions和确切SHA的DEPLOY_OK核验。记录随包附于evidence。

先前全量测试曾运行，暴露旧资源编号/配置断言与缺失本地fixture；干净main全量为314通过、35失败、7跳过。收到用户指令后停止后续全量，不将它作为本次通过项。原始日志保留在工作树builds/aspect-label-research，未改无关测试期望。

## 候选与设备状态

- GR III / 官方2.10输入；候选 `m10v-gr3-aspect-label-r1-20261026`。
- BIN SHA-256：`130f36f30679477912ec1a9ff5e1239de2aac5954858b0511ad37b0ff71b3922`。
- `camera_tested=false`；授权状态 `USER_AUTHORIZED_RELEASE_OFFLINE_VERIFIED`。
- 来源/配置/SD库哈希及dirty源码快照在包内provenance与SHA256SUMS中。恢复与真机清单见同名txt。

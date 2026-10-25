# M10V 源码与回归导航

相对路径均指 M10V 根目录，先确认文件仍存在。这里只是路由，不是本轮已运行记录。

| 改动区域 | 源码入口 | 必查测试 |
| --- | --- | --- |
| 目录/状态/效果 | native/gr3/m10v_library.h/.c；web/gr3/native-library-state.mjs；node/gr3-native-library.mjs | tests/test_gr3_m10v_library.py；test_gr3_m10v_library_arm.py；node/gr3-film-picker.test.mjs；gr3-film-settings.test.mjs |
| 参数/设置/UI生命周期 | native/gr3/m10v_library_menu.c；m10v_settings*.c/.h；node/gr3-settings-menu.mjs | tests/test_gr3_settings.py；test_gr3_settings_controller.py；test_gr3_settings_view.py；test_gr3_settings_root.py；test_gr3_menu_readonly.py；test_gr3_m10v_adj_arm.py |
| SD/custom LUT/存档迁移 | native/gr3/m10v_sd_library.h/.c；m10v_sd_camera.c；m10v_library_camera.c；node/gr3-sd-film-pack.mjs | tests/test_gr3_sd_library.py；test_gr3_sd_camera.py；test_gr3_sd_menu.py；node/gr3-custom-lut.test.mjs；gr3-sd-film-pack.test.mjs；gr3-sd-film-routes.test.mjs |
| 捕获/首张/排队冻结 | native/gr3/m10v_library_capture.c；m10v_isp_recipe_color.c；scripts/build_gr3_m10v_library.py | tests/test_gr3_capture_snapshot.py；test_gr3_m10v_capture.py；test_gr3_native_recipe_handoff.py；test_gr3_native_fast_capture.py |
| RAW归属/释放/回退 | native/gr3/m10v_capture_raw_lifetime.c/.h；m10v_capture_lifecycle.c | tests/test_gr3_capture_raw_lifetime.py；test_gr3_capture_released_raw.py；test_gr3_capture_lifecycle_integration.py；test_gr3_capture_lifetime.py |
| 水印/胶卷名 | native/gr3/m10v_library.c；scripts/preview_gr3_stamp.py；check_gr3_stamp_sanitizers.py | test_gr3_m10v_library.py 的分段字形/角落/小图/padding/date；test_gr3_m10v_capture.py 的时钟回退 |
| HDF | native/gr3/m10v_digital_hdf.c；m10v_hdf_menu.c；node/gr3-digital-hdf.mjs | tests/test_gr3_digital_hdf.py；test_gr3_hdf_menu.py；test_gr3_shared_hdf.py；node/gr3-digital-hdf.test.mjs |
| A/B/DISP | native/gr3/m10v_ab.h；m10v_ab_camera.inc；m10v_settings_controller.c；build_gr3_settings_hooks.py | tests/test_gr3_ab_compare.py；test_gr3_settings_controller.py；scripts/probe_gr3_ab_entry.py、probe_gr3_ab_navigation.py、probe_gr3_ab_queue.py（按实际CLI/函数执行） |
| 成品组合/配置绑定 | node/gr3-m10v-native-build.mjs；gr3-native-library.mjs；gr3-integrated-components.mjs | node/gr3-integrated-export.test.mjs；gr3-m10v-native-build.test.mjs；gr3-native-routes.test.mjs；gr3-native-node-path.test.mjs |
| IIIx/IV/II边界 | node/gr3x-native-port.mjs；native/gr4/*；node/gr4-*.mjs；node/gr2-firmware.mjs | node/gr3x-native-port.test.mjs；gr3x-customization.test.mjs；tests/test_gr4_*.py；node/gr4-*.test.mjs；node/gr2-firmware.test.mjs |
| 原厂工具/开关机/版本 | node/gr3-customization.mjs；gr3-power-images.mjs；gr3-version-unlock.mjs | node/gr3-customization.test.mjs；gr3-power-images.test.mjs；gr3-power-images-http.test.mjs；gr3-version-unlock*.test.mjs；tests/test_gr3_updater_version_gate.py |
| 调试与日志 | native/gr3/m10v_debug.c；scripts/read_gr3_debug_log.py | tests/test_gr3_debug.py；node/gr3-debug.test.mjs；按真实build receipt解码 |

选择与改动相关的测试，并包括共享接口的跨机型消费者；记录skip及缺失fixture。大套件按发布风险运行，不因仅更新skill就重跑耗时约千秒的固件全套。发布功能候选前仍执行完整 `npm test` 和相关 Python/ARM/最终产物检查；不是用GRKit测试取代M10V测试。

定位具体断言：

```sh
rg -n 'def test_|test\(' tests/test_gr3_m10v_library_arm.py tests/test_gr3_ab_compare.py node/gr3-integrated-export.test.mjs
```

关注行为：失败原子提交/其他槽不变、已存配置优先、旧记录迁移、浏览零写入、原厂返回路径、ROM RX、寄存器/SP/LR/NZCV、私有ID不进入原厂tone、Fn与非DISP透传、首张与排队独立、RAW释放后禁读、stride padding、SD短读按tell判断、disabled效果不改像素、诊断不成为控制依赖。

设备验证：固定测试包hash/build_id，按变更涉及的菜单/按键/首张/连拍/RAW+JPEG/回放/水印/重启/无卡与存档恢复逐项验收。用户确认之前的离线passed不能升级成camera_passed。

## 若本次明确改变实时预览

先分别验证目标机型/target与实际pipeline，不用live_color布尔值代替执行证据。覆盖：未选/高亮/正式提交/取消后的画面；原厂/五槽/自定义卷；单色与彩色；曝光和白平衡变化；Fn参数返回、DISP/A-B和其他ADJ项；半按/单拍/连续多拍及回放返回。比较同一场景的预览、首张及后续JPEG，RAW像素保持边界；明确哪些效果仅成片可见。记录预览帧率、切换响应、拍摄耗时与内存失败回退的实际测量，不拿GRKit模型预览或ARM指令数当真机一致性/性能证明。首次移植先保留旧模式作为对照与回退。

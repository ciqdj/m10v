# GR IV / GR II 移植验证记录

2026-10-14。完整 M10V 胶卷运行体移植仍未完成；以下区分可复现的离线通过项与未通过项。

| 项目 | GR IV | GR II |
| --- | --- | --- |
| 官方内容身份识别 | 通过：1.11.10.7 | 通过：3.00 |
| 解包、严格边界、原样往返 | 通过：13 分区、2765 帧 | 通过：嵌套 UNITY、3 组件 |
| 资源/菜单读取 | 20 个原厂风格及名称图标 | 121 项卷资源 |
| 原厂自定义滤镜构建 | 五槽真实构建与回读通过 | 未开放 |
| CPU 执行研究 | 原厂描述符构造与分配 | 原厂头识别函数 |
| 原生 65 卷库、颗粒/柔光/800T/时间戳 | 尚未移植 | 尚未移植 |
| 实机刷入、启动、成像与恢复 | 未验收 | 未验收 |

## 命令

```sh
npm test
.venv/bin/python -m unittest tests.test_model_firmware tests.test_gr4_capture tests.test_gr4_official_entries tests.test_gr2_update
.venv/bin/python -m unittest tests.test_gr4_reference_build
```

最后一项使用真实官方输入、LLVM/LLD、编译器、封装器及独立读取器，新增五个原厂 Positive Film 模板槽位，校验名称、版本、原始 RTOS 可恢复及未修改分区；生成临时候选后自动清理。缺少样本或工具链时明确跳过，跳过不视为通过。

实际浏览器已检查 `/gr2/` 官方样本结果和 `/gr4/` 官方导入结果。GR4 页面成功显示 20 个原厂风格、名称和图标，未见脚本错误。截图保存在本地 `data/research/gr2/page.png`、`data/research/gr4/page.png`。

代码审查发现的未保存草稿丢失和旧检查成功报告残留问题，均用失败测试复现，再修复并通过回归。

## 剩余验收条件

GR4 需完成 request/mode 准入、RAW 区间与生命周期、完整菜单模型、持久化和时钟 ABI，才能接入 M10V JPEG 运行体。GR II 需完成修改后的数据校验算法及镜像加载、菜单、持久化和成像接口。当前不输出 GR II 修改候选，不把 GR4 原厂槽位构建标记为完整 M10V 胶卷支持。

在上述离线契约建立之后，仍需真实相机验证启动、菜单交互、JPEG 与 RAW+JPEG、DNG 预览、断电设置保留、资源组合及恢复流程。

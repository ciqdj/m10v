# 蓝凤凰 Phoenix II：EI 200 / EI 120

旧胶卷 ID 67 和 EI 200 的原有色表保持不变。`effects.filmExposure` 的 0 表示 EI 200、1 表示 EI 120；该字段仍在 104 字节 schema 4 的原位置。RED 的 0/1/2 继续表示 125/64/250，不共用档位语义。更换胶卷会重置曝光档，重选当前卷和重置公共质感则保留，五个槽位独立保存。

当前 Phoenix II 模型基于 HARMAN 官方技术资料的定性约束，并非从实测底片标定。EI 120 的显示域曝光适配是明确的设计假设：先解码 sRGB，以 `g = 200 / 120` 和 `y = g*x / (1+(g-1)*x)` 增加中间调曝光、保持白端，再编码 sRGB 并应用原有 Phoenix 显示映射。不能由已处理的 RGB 恢复场景光谱、真实负片密度或冲扫过程，因此不宣称对应真实胶片的精确曝光响应；也不改动机身 ISO 或增感冲洗。

网页和 CPU 使用相同的独立 15³ 8 bit EI 120 LUT。HARMAN 内部第五张表只经 dispatcher variant 14 调用（texture color 16）；新六卷使用 variants 8–13，不改变旧 RED/curated 索引。原厂 ISP 另拟合 EI 120 的矩阵、曲线和 12 区色相数据；8192 个独立 holdout 样本的 ΔE00 P95 为 0.758。这是原厂量化模型相对目标色表的实现误差，不是真实胶片还原误差。

原厂详细参数页为 Phoenix 添加曝光行，实际显示 200 / 120 两档；沿用原厂滑块和 immediate callback，动态范围为 0–1，保存失败恢复旧值。GR III 和 GR IV 的适配分别保留各自的控制器地址与列表 ABI。

再生成顺序：

```sh
.venv/bin/python scripts/build_gr3_harman_reference.py
.venv/bin/python scripts/fit_gr3_phoenix_exposure.py
.venv/bin/python scripts/build_gr3_curated_reference.py
.venv/bin/python scripts/fit_gr3_curated_native.py
.venv/bin/python scripts/build_gr3_isp_native_look.py --generate-profiles
node scripts/generate_gr3_sd_contract.mjs
```

还需真机验证保存重启、切换槽位、JPEG 输出、耗时和照片效果。

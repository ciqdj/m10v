# 研究与验证范围

研究日期：2026-10-21（Asia/Shanghai）。基线 commit `8a886cbfa7ca3af7726c942d4b0d367d9486acb4`，workspace version 1.1.1。

## 完成

- 联网核实、克隆独立源码，读取 build、identity、target/layout、TTL、Linux installer、relocation、插件 registry/API、处理/状态链和测试入口。
- 主机 Clang 编译并运行上游六个 C contract：GR3 的 catalog、directory、relocation、framing、picture，以及 GR4 的 picture，全部 exit 0。
- 两个 target 的 menu.c、framing.c、picture.c 共六项主机语法检查通过。
- 额外执行 selection contract 的空文件、两项合法选择、重复名、未知名四个输入，分别得到 0、12、invalid、invalid，与规则一致。

复现示例（在 checkout）：

```sh
clang -std=c11 -O2 -Wno-int-to-pointer-cast -Wno-pointer-to-int-cast -DGRKIT_HOST_ADDRESSES -DGRKIT_TARGET_GR3_210 -I runtime tests/runtime/relocation_contract.c -o /tmp/grkit-relocation-contract
/tmp/grkit-relocation-contract
```

其余 harness 的生成输入以 crates/grkit-core/tests/runtime_grf.rs 为准。直接执行部分 C contract 不替代完整 Rust suite。

## 未验证

本机 PATH 无 cargo，未安装 Rust，未执行 cargo fmt/clippy/test/deny、完整 ARM runtime 构建或打包。没有接相机、写 SD、启用脚本、刷机或验证 USB/Wi-Fi 代理，没有测量 Token/时长收益。上游支持声明不是本机实测。

## skill 场景验证

无 skill 的基线场景为 IIIx 1.60 的 M10V ADJ/拍摄迁移及 USB 在线替换。独立测试无法定位源码、共用 target 规则、静态链接和诊断机制。编写后的独立场景测试正确定位上述入口及状态 47、插件选择空/缺失和驻留生命周期；反馈的三个缺口已补充：IIIx 明确版本、47 的 index 按失败来源解释、共享 STARTUP 恢复及 scripts-off 的全局影响。结构校验与本地参考链接检查通过。后续按源码证据局部更新，不积累未经验证的设备结论。

## M10V 功能保护与发布门槛扩充

2026-10-21 对照当前M10V工作树与GRKit补充功能/存储/交互/RAW/机型基线、测试路由、28文件源指纹，以及“测试包→用户验证→main/GitHub/宝塔”门槛。原技能基线测试无法给出M10V专用能力/测试；扩充后的独立场景测试正确识别目录/存档不可直接替换、下载不等于验收、develop/main均受门槛约束，以及A/B离线通过不等于实机修复。根据反馈增加实时预览专门验收清单。

本轮只更新技能和元数据，未改功能代码、未生成新测试固件、未运行M10V全量测试、未提交/推送/部署。28个已记录业务/测试/证据文件哈希在本轮保持一致。技能结构、引用链接、安装/仓库副本一致性与本轮技能diff空白检查通过。历史测试记录不能当作当前工作树全量回归已通过。

## 蓝牙诊断扩充（2026-10-25）

GR III 2.10 实机完成 CoreBluetooth 发现／连接、型号／固件／电量／工作模式／AF 读取及 AF／模式通知订阅；收到模式变化，未捕获 AF 变化，之后连接超时。用户确认触屏只移动框由机内设置导致，28mm 当前稳定；自定义焦距双画面和卡死尚未验收。详见 [蓝牙诊断](bluetooth-diagnostics.md)。

随附 Objective-C 探针和 runner 基于该实测版本整理，已执行 Clang 编译、签名和技能结构／本地链接检查；整理后版本未再次连接相机，未修改固件、封包或发布。前文 2026-10-21 的“没有接相机”是当时的研究范围，不代表本次没有设备证据。
# 2026-10-26 GR III ISP 性能验收补充

用户确认GR III2.10 RC2修复通过并明确授权合并与发布。BIN SHA-256为
`8346ff292a57727eb57d2d6fad919d330848ad9a37117284f5396919fdbf6992`，
build_id `0c9a0164`。这是本机型／本候选的定性确认，不扩展为IIIx／IV验收，
未提供修复后计时。后续滤镜开发遵守[ISP性能契约](isp-performance.md)：普通色彩走ISP、
真实投递与本张快照完成交接、默认配置零像素工作。此前CPU色彩18.823秒是故障样本。

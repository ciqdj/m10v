# GR III 蓝牙只读诊断（macOS）

在电脑需要保持上网 Wi‑Fi、用户希望直接观察相机状态时使用。BLE 可以读取型号、公开固件版本、电量、工作模式和 AF 状态；它不是 RTOS 调试器，不能读取 LCD 寄存器、缓冲地址、任务栈或 M10V 二进制日志。双画面、缓冲退休和卡死仍需固件日志／单独实现的运行时采集证据。公开版本 2.10 不能唯一标识内部候选构建。

## 已验证范围

2026-10-25，在 macOS + GR III 2.10 实机上，原生 CoreBluetooth 探针成功完成广播发现、连接、服务／特征枚举、五项白名单读取，以及 AF／工作模式通知订阅。读到型号 RICOH GR III、电量 100%、AF `00 00`、工作模式 `03`，操作机身后收到模式 `00/03` 变化；没有收到对应 AF 状态变化，随后发生 CBErrorDomain Code 6 连接超时。因此“订阅成功”不等于“捕获到了机身 AF 活动”，更不能将无通知推断为 AF 未启动或已经卡死。

用户随后确认：半按快门可合焦；触屏只移动框的问题来自机内触摸 AF 选项，28mm 当前稳定。自定义 40/80mm 双画面／卡死没有因此验收通过。不要把这条历史观察当成当前固件状态或所有机型的能力保证。

## 使用步骤

1. 保持电脑原来的上网 Wi‑Fi，不自动启用相机 WLAN 或切换网络。让用户打开相机蓝牙、进入配对等待，并暂时断开手机 Image Sync／GR WORLD 等竞争连接。附近有多台 GR 时，只让目标相机处于配对状态；脚本连接首个匹配广播，不适合多机自动选择。
2. 运行随附脚本，使用新的输出目录。macOS 可能弹出“GR3 BLE Probe 想使用蓝牙”，由用户允许。不要绕过隐私权限、重置系统 TCC 或替用户点击授权。

   ```sh
   bash /path/to/grkit-development/scripts/run-gr3-ble-probe.sh /tmp/gr3-ble-session-unique 180
   ```

   脚本使用 Objective‑C、Clang `-fno-modules`、Foundation/AppKit/CoreBluetooth，生成带蓝牙用途说明的本地 `.app` 并临时签名。无需安装 Python 蓝牙库或修改相机固件。上次 Swift 工具链出现 `redefinition of module SwiftBridging`，采用此方式可避免该模块编译路径；不需要更改系统 SDK。
3. 查看 `events.log`。`STATE 5` 为 poweredOn、authorization 3 为已授权；`CONNECTED` 后应有服务、特征和 `READ`。`NOTIFY ... enabled 1` 仅证明订阅建立。日志时间使用 UTC，和用户操作时间对照时转换时区。原始值以十六进制保存。
4. 连接成功后让用户退出配对菜单，回到拍摄界面。先半按快门，再间隔约 5 秒触屏；记录两次各自时间、实际合焦、焦距、单双画面及是否卡住。不要用蓝牙拍照命令代替这两种机身输入，那会改变待验证链路。
5. 采集默认 180 秒，可设 10–600 秒；读请求 8 秒超时终止连接，断开后不自动重试。界面授权等待可能延迟回调，不能保证弹窗期间截止计时及时执行。按需短时重开采集，不把持续连接当作心跳或后台守护。保存原始日志和源／可执行文件哈希到私有研究目录，不把相机日志、序列号或无线密码放进技能／公开 Git。

只构建、检查脚本而不连接相机：

```sh
bash /path/to/grkit-development/scripts/run-gr3-ble-probe.sh /tmp/gr3-ble-build-unique 30 --build-only
```

随附版本从实测探针整理而来，新增顺序读取保护、超时、输出目录和隐私过滤；整理后已编译检查，完整启动与通知流程需下次实机重验，不能冒充已完成第二次设备验收。不要并行启动多个探针；保持 macOS 授权弹窗可见。

## 白名单与解释

| 特征 | UUID | 值与限制 |
| --- | --- | --- |
| 相机信息服务 | `9A5ED1C5-74CC-4C50-B5B6-66A48E7CCFF1` | 广播可能没有设备名；同时匹配此服务，避免漏发现 |
| 型号 | `35FE6272-6AA5-44D9-88E1-F09427F51A71` | UTF-8 |
| 固件 | `B4EB8905-7411-40A6-A367-2834C2157EA7` | 字符串可能含尾部零 |
| 电量 | `875FC41D-4980-434C-A653-FD4A4D4410C4` | 本次读到单字节 `64` = 100% |
| 工作模式 | `1452335A-EC7F-4877-B8AB-0F72E18BB295` | `00` 拍摄、`01` 回放、`02` BLE 启动、`03` 其他、`04` 关机传输；依据社区协议，逐机核实 |
| AF 状态 | `CDFC734E-EA21-427D-A69F-C1A0F7F1E9A3` | 两个 sint8：运行 0/1、合焦 0/1。`00 00` 仅描述该次读取，不能证明故障 |

探针只读取以上五项数据并订阅 AF／工作模式；枚举其余特征 UUID 和属性不代表读取其内容。不发送拍照、关机、时间／定位、WLAN 开关或任何未知写命令；通知订阅本身会设置 GATT 通知配置，属于诊断操作，不改变拍摄设置。未实现 BLE 文件下载、RTOS RPC 或自动重连。

## 先排除触摸 AF 设置

GR III 默认的 Touch AF 是 **AF Point（AF 点）**，仅移动框，需要半按快门才合焦。需要触屏直接合焦时，查看「自定义设置 → 自定义控制 → 触摸 AF」，使用 **AF Point+Focus（AF 点＋对焦）**；菜单中文可能随语言版本不同。先记录原值并与用户核对，不能把只移动框直接判定为裁切 Hook 故障。改变该设置后的合焦正常，也不能证明裁切坐标、LCD 退休或其他焦距通过。

## 无连接／无事件时

- 无广播：核对配对等待、手机竞争连接和 macOS 权限；按设备名过滤不充分，相机可能只广播服务 UUID。不要打印无关附近设备清单。
- 已连接却无数据：看服务发现、特征属性和读取错误；无服务／不同 UUID 不套用 GR III 的支持声明。脚本有总时限，不循环尝试未知特征。
- Code 6：表示连接超时，不等于固件死锁；核对用户操作时间、拍摄界面和关机状态，再决定是否重新配对。
- 有模式变化却无 AF 通知：保留“观测不足”的结论，依赖用户实际合焦反馈及固件日志；不要声称已定位触屏事件丢失。
- USB 另查 `gphoto2 --auto-detect`／`--summary`。本次 GR III 仅暴露 MTP/PTP 文件接口；通用驱动的 opcode 配置项不是调试能力，不能盲发厂商命令。用户不愿切换 Wi‑Fi 时继续遵守，不把 BLE 自动升级为 Wi‑Fi 会话。

## 协议来源

- [社区 BLE 协议目录](https://github.com/dm-zharov/ricoh-gr-bluetooth-api/blob/main/characteristics_list.md)
- [AF 状态字段](https://github.com/dm-zharov/ricoh-gr-bluetooth-api/blob/main/shooting/auto_focus_status.md)
- [工作模式字段](https://github.com/dm-zharov/ricoh-gr-bluetooth-api/blob/main/camera/operation_mode.md)
- [理光 GR III 官方 FAQ：触摸 AF 默认只移动点](https://www.ricoh-imaging.co.jp/english/support/qa/gr-3/index.html)

社区协议为逆向资料，特征可用性以实际服务枚举和设备行为为准。现有 GRemote 的 `ios/Runner/Native/RicohBluetooth.swift` 可参考 CoreBluetooth 状态机，但其 bootstrap 包含无线凭据读取，不直接用于这条只读 AF 诊断流程。

# M10V 迁移与诊断

以下是开发方法，不代表 M10V 已适配，也不授权额外设备操作。

## 迁移

先在官方基线加载只读页面，再迁移一个不改变图像所有权的功能。复用 GRKit menu host，避免两套 ADJ 管理器同时运行。

列出 M10V 的 Hook 地址/原指令/调用链、代码和数据区域、设置记录、共享缓冲生命周期、文件和 cache 操作；与 GRKit target、components::Layout、patch、ABI 对照。

| 检查 | 问题 |
| --- | --- |
| Hook | ADJ、tuning、JPEG、图标是否同址或重复处理？ |
| 尾部 | 是否延长 RTOS？有无未计入 image end 的数据？ |
| 状态 | HTData/APData、STATE 和默认值迁移如何隔离？ |
| 缓冲 | 谁读写？主图/缩略图是否别名？shot 对应哪个 record？ |
| ABI | A32/Thumb、结构/返回值/寄存器契约是否一致？ |
| 启动 | STARTUP.TTL 是否已有逻辑？覆盖会否释放旧数组？ |

GRKit 会拒绝部分已修改固件；重定位不会串接其他 MOD。选择官方固件加合并 runtime，或实现经验证的共同 core/调用链；不能移除 guard、独立叠装后声称兼容。

像素效果接入 PictureSet 的去重 planes，保留主图、screennail、thumbnail、422/420、pitch 和可见范围。shot ring 按 shot settings pointer 保存 record，不简化成全局最后一张指针。缓存/生命周期改变须真机验证。

## 诊断

需要保持电脑上网 Wi-Fi 并直接连接相机时，先读 [蓝牙只读诊断](bluetooth-diagnostics.md)。其中包含 macOS 探针、AF 状态解释、触摸 AF 默认配置和 USB/MTP 的能力边界；BLE 连接不等于获得 RTOS 调试接口。

重启前先保存 INSTALL.ERR 全文、INSTALL.OK、MODULE.BIN 元信息、PLUGINS.TXT、构建清单和机身信息；启动会清理旧结果/锁。记录已有 MOD。

| 状态/现象 | 入口 |
| --- | --- |
| 无 MODULE.BIN | ModeSet、STARTUP、PLUGINS.TTL、Linux 挂卡和 SCAN；数秒启动延迟正常 |
| plan 存在但无结果 | INSTALL ready 检查、数组分配和锁；看 not_ready/retry |
| 1 / 2 | /dev/mem 打开 / 映射失败 |
| 3 | 独占创建锁/结果失败；不在运行中删锁强装 |
| 10 / 11 | 脚本数组数目/尺寸、堆范围、重叠 |
| 12 / 14 / 26 / 39 | not_ready 可重试，逐项读源码，不统一判为不支持 |
| 16 | Hook 当前字节不符，含已装入口或外部 MOD |
| 21 | alias cache 同步失败 |
| 23 / 24 | 发布失败，回滚报告成功 / 回滚也失败；均非成功 |
| 30 / 31 | 目录读取 / 记录错误 |
| 37 | SCAN 与 INSTALL 发现内容不同，两阶段之间不能更新卡 |
| 43 / 44 | PLUGINS.TXT 非法、重复或过长 / 读取失败 |
| 45 | guard 指出尾部占用冲突 |
| 47 | 重定位失败，读取后续报告 |

以上以当前 installer.c 为准。47 后最多 8 行，每行四个十六进制值：reason、index、pinned address、count/value。reason：1 startup 不符；2 无匹配/来源；3 多匹配；4 非 B/BL；5 分支目标窗口不符；6 区域越界；7 来源不一致。index 的对象取决于失败点：reason 4/5 和部分 6 使用 source index，不能一律当作 symbol/window index。对照 runtime/relocation.h 的具体 relocation_fail 调用和 crates/grkit-build/src/relocation.rs。

保留 macOS ._ 与 exFAT workaround：8.3 GRF 名、坏目录项有限跳过、第二遍目录扫描。桌面文件系统正常不能证明可以删除这些逻辑。

## 状态与生命周期

- STATE.TXT 是 key/value 十进制行对，经相机文件 API 写入，避免 Linux 与相机同时写照片卷。
- filecreate 不截断、rename 不覆盖：先写 TMP，再删 TXT，再 rename；仅 TMP 存在允许恢复。
- TTL 越界读及无换行末行可阻塞，保留按长度读取和手工解析。
- 脚本异常退出释放数组；没有 RTOS 回调排空及撤 Hook 协议，不支持强杀后重装。
- SD 运行不代表已有 USB/SSH/ADB、网络代理或任意 RTOS RPC。

## 设备验收和恢复

设备动作处于用户授权范围时，使用确切机型的 resources/INSTALLATION*.md；保留已有 SD 脚本，不覆盖共享 SCRIPT。启用脚本是持久设置，运行代码通常在关机后消失，两者分开。

按改动选测试：冷启动/无卡、安装结果、ADJ 原五项、新入口、预览/提交、Fn 返回、单拍/连续多拍、JPEG/RAW+JPEG、回放放大、缩略图/元数据、重启后状态。缓存/生命周期变更覆盖相关拍摄与重启。原厂/候选对照使用相同场景、卡和格式；模拟指令数不是相机毫秒。

正常移除先关机，只移除自己拥有的文件，恢复自有的 STARTUP include 改动；有其他脚本时不删整个 SCRIPT。禁用脚本用对应 scripts-off 包，但它是全局开关，也会停用其他 SD 脚本，须说明并遵循用户范围。启动挂死可依 recovery，在非固件升级时断电拔卡、无卡重启；仍失败按指南回放启动。设置重置会丢失个人配置，先告知后果；不移动镜筒，不在正式固件更新时断电。取卡启动不是救援保证。

[上游安装](https://github.com/ahonn/grkit/blob/8a886cbfa7ca3af7726c942d4b0d367d9486acb4/resources/INSTALLATION.md) · [恢复](https://github.com/ahonn/grkit/blob/8a886cbfa7ca3af7726c942d4b0d367d9486acb4/resources/RECOVERY.md)

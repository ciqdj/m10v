# 启动链路与源码导航

源码基线：`ahonn/grkit@8a886cbfa7ca3af7726c942d4b0d367d9486acb4`。路径相对 GRKit 根目录；固定链接前缀为 `https://github.com/ahonn/grkit/blob/8a886cbfa7ca3af7726c942d4b0d367d9486acb4/`。

## 端到端链路

| 阶段 | 实际机制 | 源码入口 |
| --- | --- | --- |
| 固件输入 | 官方容器哈希校验、解码和 RTOS 内存视图 | `crates/grkit-build/src/firmware.rs::verify_firmware`, `target.rs` |
| 编译 | processing/menu/framing 组件、patch 校验、生成 hooks/payload 头、链接 Linux 安装器 | `crates/grkit-build/src/lib.rs::build_runtime/build_image`, `components.rs`, `loader.rs::header` |
| SD 包 | runtime 和 effects 分开构建，再合成含机型 ModeSet 和指南的 ZIP | `crates/grkit-cli/src/main.rs`；用下方命令定位 core 的 package 实现 |
| 开启脚本 | ModeSet 的 `[SCRIPT_EN_MODE EN]` 与 DEVELOP.MOD，MENU 开机执行；设置持久化 | `crates/grkit-core/src/runtime.rs::activation_files/modeset_files`, `camera.rs` |
| 启动 | `SCRIPT/STARTUP.TTL` include `SCRIPT/PLUGINS/PLUGINS.TTL` | `runtime.rs::runtime_files_for/loader_for` |
| Linux 请求 | `lcmd_resp on`，`lcmd sh /media/storage1/SCRIPT/PLUGINS/SCAN.SH` | `runtime.rs::loader_for` |
| SCAN | 扫描 GRF，写 MODULE.BIN 分配计划；TTL intdim 分配 registry/图标数组 | `runtime/installer.c::scan/discover`, `runtime.rs::loader_for` |
| INSTALL | INSTALL.SH 调 INSTALL.BIN --install；映射 /dev/mem，检查地址和数组 | `runtime/installer.c::_start/install/relocate`, `runtime/relocation.h` |
| 发布 | 记录/图标初始化、先 payload 后入口 patch、缓存同步、失败回滚 | `installer.c::publish/sync_alias/install`, `grkit-build/src/lib.rs::build_image` |
| 驻留 | RTOS 菜单/成像，TTL 持有数组并通过相机文件 API 保存选择 | `runtime/menu.c`, `processing.S`, `framing.c`, `picture.c`, `runtime.rs::state_script` |

Linux 安装器为 freestanding ARM Linux ELF：armv7-linux-gnueabi、直接 syscall、静态链接，不要求 ARM libc/sysroot。mmap2 映射范围由生成头的 MAP_BASE/MAP_SIZE 指定；不是通用设备写内存方案。

Shell 包装器最终 exit 0，因此 lcmd 返回或 Shell 退出码 0 不等于安装成功。读取 INSTALL.OK、INSTALL.ERR 和 GR_MODULE_* 输出。

## 相机身份

| camera | runtime target | ModeSet | 构建输入 |
| --- | --- | --- | --- |
| gr3 2.10，含 HDF | gr3-2.10 | 00078350.588 | 官方 GR III 2.10 fwdc239b.bin |
| gr3x 1.60，含 HDF | gr3-2.10 | 00078490.609 | 构建仍用已 pin 的 GR III 输入，package 选 IIIx |
| gr4 1.11，含 HDF | gr4-1.11 | 00078560.636 | 官方 GR IV 1.11 fwdc248b.bin |

IIIx 共用 runtime 源于上游比较已知 RTOS 镜像，不能推广到其他版本。公开 build 入口严格校验 Target.firmware_sha256；不能因共用 runtime 随意传 IIIx BIN。

GR III 输入 SHA-256：`d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`。
GR IV 输入 SHA-256：`a2f664dfca034059eb0fd6e18ab08684c326b4a034d85c164dad7e1ec9b5655f`。

同公开版本可有不同内部构建。installer 使用掩码窗口及引用关系重定位：唯一匹配、分支目标一致、符号来源一致、边界合法。启动 literals 给出 image end 和 data/BSS；tail 随 image end 移动。tail 可含未初始化 DRAM 或前次代码，不能用全零判空。移动 tail 不解决其他 MOD 的入口冲突。

本 commit 的网页/指南有实验性 GR IV Monochrome 路径，而 Rust camera::CAMERAS 仍是 gr3/gr3x/gr4。先查各入口实现，不能凭网页推断 CLI 接受新 camera ID。HDF/IIIx 的兼容声明与具体机身测试覆盖分别记录。

## 定向检索

```sh
rg -n 'fn (build_runtime|build_image|header|loader_for|runtime_files_for|state_script)' crates
rg -n 'static int (scan|install|relocate|not_ready)|/dev/mem|sync_alias|publish' runtime/installer.c
rg -n 'PLUGINS|point_of|guards|relocatable|FIRMWARE\(' crates/grkit-build/src runtime
rg --files crates/grkit-core/src | rg 'packag|camera|runtime|abi|plugins|modules'
```

优先读函数级源码。网页 architecture 可能被重写或缓存，命令和契约以当前 checkout 为准。

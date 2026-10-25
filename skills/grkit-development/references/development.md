# 插件开发、构建与验证

基线见 [chain-and-source-map.md](chain-and-source-map.md)。先读 CONTRIBUTING.md、对应插件和 runtime/plugin.h。

## 扩展点

| 需求 | Point | 示例 |
| --- | --- | --- |
| ADJ 页面、提交/预览 | menu.page | runtime/plugins/guides/page.h、image-control/page.h |
| 胶片矩阵/曲线/参数 | tuning | image-control 与 GRF |
| 取景线框/蒙版 | viewfinder.overlay | guides、framing |
| 实际裁切/输出尺寸 | capture.aspect | framing |
| JPEG 前像素处理 | picture.encode | date-stamp、image-control/selective.c |
| 原厂颗粒 | pipeline.grain | grain |

插件仅 include ../../plugin.h；固件函数/地址由 core 服务及 target adapter 提供。Module 为页面回调；Layer 为取景绘制；Encoder 为 wanted/encode，host 在缓存同步之间调用。Plane 含 pitch、裁切范围与 chroma 半高标志，不是连续 RGB。

## 新增插件

1. 在 runtime/plugins/<id>/ 写 page.h 和需要的 handler C，定义 <ID>_PAGE、<ID>_TILES。
2. 在 crates/grkit-core/src/plugins.rs::PLUGINS 注册 id、points、needs_effects、words、state、tiles、artwork、handlers、layers、encoders；同步数组长度。
3. 状态放 registry words，保存键用 Slot::Own；不要占用原厂设置或手算 header 空洞。通用 ABI 改 abi.rs。
4. 补 artwork、menu_text、web/src/i18n.ts，按需更新指南。新增核心 Hook 同时更新 components::point_of、目标布局和重定位输入。
5. 生成后看 diff，不手改 runtime/abi.h、runtime/generated/、web/src/generated/。

```sh
GRKIT_UPDATE_GENERATED=1 cargo test -p grkit-core --test generated
```

当前上限：32 插件、64 插件 header words、首图标块 40 slots、菜单文字 8192 bytes、20 effects（产品限制）。实际剩余容量查 registry 与 build，不把上限当作余量。

processing 为 A32；menu 为 Thumb-2 C -Oz；framing/picture 为 A32 C/汇编。保留指令集状态、寄存器和调用约定。构建拒绝可写静态数据、段溢出、未归属 Hook；menu 栈帧上限 256 bytes，framing 1536 bytes。freestanding 无除法 helper，按 core 契约使用 divide。

## 构建实例

在 checkout 执行。Rust 至少 1.92，Clang/LLD 支持 ARM。cargo 缺失时报告，不静默安装全局工具。路径替换为实际值；输出选择不存在的新目录，builder 会拒绝覆盖。

```sh
cargo build --locked -p grkit-cli
target/debug/grkit doctor --clang clang --lld ld.lld
target/debug/grkit effects build --source effects --out build/effects-dev
target/debug/grkit build --target gr3-2.10 --firmware /private/fwdc239b.bin --out build/runtime-dev --clang clang --lld ld.lld
sh .github/scripts/install-guide-tools.sh build/guide-tools
sh .github/scripts/build-guides.sh target/debug/grkit build/guide-tools build/guides
target/debug/grkit package --camera gr3x --build build/runtime-dev --effects build/effects-dev --plugins guides,date-stamp --guide build/guides/gr3x/en.pdf --out dist/GRKit-dev.zip
target/debug/grkit verify dist/GRKit-dev.zip
```

指南工具会下载字体/Typst；纯 core/host 测试不需要。仅改效果可复用 runtime，重建 effects/package；改 C 后先重建 CLI，因为 CLI 内嵌源码，旧可执行文件不会读取新 C。GR IV 同时改 target、官方输入、camera 和 guide。

产物含 sd/、objects/、build.json；清单记录工具链、源文件/固件/输出哈希、组件尺寸和扩展点 patch 数。本基线 source_revision/source_dirty 为 null；另存 Git revision、dirty 状态、命令和 ZIP 哈希，不能宣称清单已完整保存 Git provenance。

## 验证

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
GRKIT_REQUIRE_NATIVE_TESTS=1 cargo test --workspace --locked
cargo deny --locked check
GRKIT_CLANG=clang GRKIT_LLD=ld.lld cargo test -p grkit-build --locked synthetic_ -- --ignored
GRKIT_TEST_FIRMWARE=/private/fwdc239b.bin GRKIT_CLANG=clang GRKIT_LLD=ld.lld cargo test -p grkit-build --locked pinned_firmware_build_is_reproducible -- --ignored
```

cargo deny 需要相应子命令。GRKIT_REQUIRE_NATIVE_TESTS 避免缺 C 编译器时跳过。ARM build 测试默认 ignored，普通 cargo test 成功不等于跑了固件构建。

crates/grkit-core/tests/runtime_grf.rs 为 host C harness 入口：GRF、catalog、directory、relocation、menu、framing、picture、selection；picture 覆盖两 target。grkit-build/src/tests.rs 覆盖 build/relocation。主机映射/缓存计数不等于硬件缓存一致性和时延。

批量算法用主机原生，小样本 ARM 检查指令/ABI，真机检查任务调度、照片和耗时。缓存键须包含源码、固件、工具链和输入，不能只用公开版本号。

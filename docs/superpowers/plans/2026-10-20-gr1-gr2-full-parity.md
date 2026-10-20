# GR / GR II Full Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use native execution in this chat unless the user selects delegation. Steps use checkbox syntax for tracking.

**Goal:** 对齐 GR3/GR4 当前固件功能和页面操作，仅允许以底层证据支持的机型限制豁免。

**Architecture:** 复用现有工作台、胶卷语义和纯算法；UNITY 容器共享，GR/GR II 的输入身份、更新校验、加载映射、资源、ABI 和原生编译独立。先完成共通底层和 GR II，再完成 GR；每阶段提供可独立验证的结果。

**Tech Stack:** Node.js 20+、Python 3、Capstone、Unicorn、现有 LLVM/LLD ARM 工具链、C/ARM、原生网页 JS。

**Spec:** `docs/superpowers/specs/2026-10-20-gr1-gr2-full-parity-design.md`

## Global Constraints

- 机型 ID 为 `gr1`、`gr2`；官方输入为 `bin/rg1_v051.frm`、`bin/rg2_v003.frm`，精确 SHA 取 spec，不接受未知版本地址补丁。
- 当前基线为 `a3773e4`；46 款可选胶卷，五个活动槽；保持历史 ID。
- 尚未定位接口、校验未解、实现困难、性能未测均不构成豁免。
- 不关闭 bExecVerify/bCompareCsum 来代替校验重算；不猜注入空间或复制 GR3/GR4 地址。
- RAW CFA 保持原始内容；取景与 RAW 再开发遵循当前 GR3/GR4 范围。
- 官方样本、提取资源和候选二进制保持 Git 忽略；不自动推送、部署、写 SD 或操作相机。
- 本计划与设计已于 2026-10-20 获用户批准，当前会话直接实施；研究候选和离线通过不能标记为实机完成。

## Review Focus

- 相同 b01firm6/b01firm8 组件名不能让错机型输入通过身份检查（Task 2）。
- 实际样本存在时旧路径不得让真实集成测试静默跳过（Task 2）。
- 修改校验必须覆盖头声明的真实载荷，而非外层 padding 或嵌套包错误范围（Task 3）。
- 大端 ABI/协议、非对齐像素和最后一个分块不能损坏内存或 SD 状态（Tasks 4–6）。
- 导入新来源、撤销、取消构建后旧预检和下载不得仍被使用（Task 8）。

---

### Task 1: 固化功能对照清单

**Files:** Create `docs/testing/gr1-gr2-parity.json`, `scripts/check_unity_parity.mjs`; read `web/gr3/`, `web/gr4/`, `node/gr3-native-library.mjs`, `node/gr4-m10v-native-build.mjs`, `node/gr4-native-routes.mjs`, `native/` and spec.

**Interfaces:** JSON schema `m10v-unity-parity/v1`; each row `{id, baseline_files, models: {gr1,gr2}}`; each model row `{status, implementation_files, evidence_files, automated_checks, browser_evidence, hardware_status, limitation}`. CLI `node scripts/check_unity_parity.mjs` checks required fields; `--complete` rejects researching rows or unsupported claims without limitation evidence.

- [x] Enumerate every existing control and builder option, including film name imprint, named LUT, exposure variants, power images, version strategy, SD operations, drafts and cancellation; group using the spec without dropping small options.
- [x] Implement the checker; exercise a missing baseline ID and a `proven_unavailable` row without evidence; both must fail, while an honest research ledger passes the structural check.
- [x] Record all current GR/GR II rows as researching except proved inventory/header operations; run the checker and commit this independently reviewable ledger.

### Task 2: 双机型严格解析与真实样本回归

**Files:** Create `node/unity-firmware.mjs`, `node/unity-model-profiles.mjs`, `node/gr1-firmware.mjs`, `node/gr1-firmware.test.mjs`, `node/unity-firmware.test.mjs`; modify `node/gr2-firmware.mjs`, `node/gr2-firmware.test.mjs`, `node/model-firmware.mjs`, `node/model-firmware.test.mjs`, `scripts/analyze_gr2_firmware.mjs`; create `scripts/analyze_unity_firmware.mjs`.

**Interfaces:** `decodeUnity(data: Buffer, depth?: number)` preserves the current return shape; `inspectUnityModel(data: Buffer, model: 'gr1'|'gr2') -> Inventory`; `readUnityModelComponent(data, model, name) -> Buffer`; wrappers preserve `inspectGr2`/`readGr2Component`, add `inspectGr1`/`readGr1Component`. Profile fields include exact input/component hashes and resource directory offset/count from the research record.

- [x] Add failing tests: GR 5.01/119 resources at 0x654000, GR II 3.00/121 at 0x786000, corrected +512 payload offsets; same-name wrong-model components and a one-byte changed official image are rejected.
- [x] Run `node --test node/gr1-firmware.test.mjs node/unity-firmware.test.mjs node/gr2-firmware.test.mjs node/model-firmware.test.mjs`; confirm failures identify missing interfaces or old sample path.
- [x] Extract the existing codec without semantic changes; add exact profiles/wrappers and root sample paths; support explicit research extraction without enabling writes. Assert header/resource overlap, nested depth, duplicates, truncation and both byte-exact roundtrips.
- [x] Re-run the focused command. Both provided samples must execute real integration cases with no sample-path skips; compare extraction SHA to the research record, update ledger and commit.

### Task 3: 修改校验与加载映射证明

**Files:** Create `scripts/analyze_unity_update.py`, `scripts/analyze_unity_runtime.py`, `tests/test_unity_update.py`, `tests/test_unity_runtime.py`; modify `scripts/analyze_gr2_update.py` only as a compatibility wrapper once equivalent coverage passes; update research record and ledger.

**Interfaces:** `analyze_update(component: bytes, model: str) -> dict` returns identity-locked header/verify/checksum evidence; `analyze_runtime(component: bytes, model: str) -> dict` returns proved file-to-runtime segments, startup operations and original instruction hashes. Reports distinguish candidates from contracts; neither exports a firmware writer.

- [x] Port the three header cases to independent model profiles: GR entry 0xA0053994, copy 0xA009DB2C, compare 0xA009D72C; GR II entry 0xA0057684, copy 0xA00A027C, compare 0xA009FE7C. Verify wrong component identity fails before emulation.
- [x] Follow official verification call sites and data reads to identify checksum coverage, initialization, finalization, block and tail behavior; execute original checksum instructions against synthetic buffers. Save exact disassembly and caller evidence; do not mark checksum proved based only on matching examples.
- [x] Add original-value assertions for all four components: 0x7C565038, 0x7B62E1A9, 0xA3A80234, 0x826A5E33. Compare CPU results on byte mutations, 0/1/3/4/511/512/513-byte lengths where caller permits them, and a mutation outside the covered interval. Invalid caller lengths must be rejected.
- [ ] Follow startup copy/zero operations for each load record; prove aux semantics and component roles; exercise copied data, untouched sentinels and entry selection. Do not infer runtime mapping from header field names alone.
- [ ] Run `.venv/bin/python -m unittest tests.test_unity_update tests.test_unity_runtime`; publish reproducible CPU limits and maps, update ledger and commit. If an algorithm/map is unresolved, retain researching status and continue reverse analysis; dependent writes remain unavailable.

### Task 4: GR II 原生服务 ABI 与大端构建

**Files:** Create `native/gr2/m10v_model.h`, `native/gr2/m10v_model.c`, `scripts/build_gr2_runtime.py`, `scripts/analyze_gr2_native_contract.py`, `tests/test_gr2_native_contract.py`, `tests/test_gr2_runtime_build.py`.

**Interfaces:** `analyze_gr2_contract(official: bytes) -> dict` emits exact original bytes, calling convention and ownership for allocator/free, cache, filesystem, clock, UI and capture services. `build_gr2_runtime(official: bytes, configuration: dict) -> dict` returns runtime bytes, linked sections and contract digest; it does not package a download.

- [ ] Trace services from actual callers, virtual tables and state updates in b01firm8/cp1 as established by Task 3; document code architecture and floating-point support instead of assuming GR3 toolchain flags.
- [ ] Add CPU tests for register/stack preservation, allocator failure, short reads/writes, clock errors, startup-loaded code bounds and original continuation; assert unproved service profiles are rejected.
- [ ] Implement a model-local bridge using proved contracts; compile big-endian objects and audit ELF endianness, relocations, undefined helpers and section ranges.
- [ ] Run `.venv/bin/python -m unittest tests.test_gr2_native_contract tests.test_gr2_runtime_build`; record only the tested contracts, update ledger and commit.

### Task 5: GR II 菜单、SD 与持久化

**Files:** Create `native/gr2/m10v_menu.c`, `native/gr2/m10v_storage.c`, `tests/test_gr2_menu.py`, `tests/test_gr2_storage.py`; modify the GR II builder and contract analyzer; reuse shared resources only through explicit conversion.

**Interfaces:** `gr2_menu_open/close/event` implement entry/lifecycle through model-local callbacks; `gr2_load_state`/`gr2_save_state` use explicit byte serialization with the existing shared semantic configuration. Exact C parameter types are fixed by Task 4 contract evidence before these symbols are exposed.

- [ ] Add CPU behavior tests for five slots, all current catalog IDs, per-film detail availability, physical keys, focus, back/exit, constructor failure and original-menu restoration.
- [ ] Add storage tests using shared SD fixtures with explicit endian conversion: valid package, corrupt length/CRC, unknown renderer, no card, short read/write, interrupted journal update and restart recovery preserve the last valid state.
- [ ] Implement GR II menu ownership, names/icons/fonts, per-film parameters and SD persistence; verify final serialized bytes with an independent reader rather than the writer's structures.
- [ ] Run `.venv/bin/python -m unittest tests.test_gr2_menu tests.test_gr2_storage`; update each delivered ledger row and commit.

### Task 6: GR II JPEG、质感、水印与原厂工具

**Files:** Create `native/gr2/m10v_capture.c`, `native/gr2/m10v_customization.c`, `scripts/build_gr2_customization.py`, `tests/test_gr2_capture.py`, `tests/test_gr2_customization.py`, `tests/test_gr2_renderer.py`; modify GR II contract analyzer and builder.

**Interfaces:** Capture consumes the shared catalog/config semantics through proved GR II image descriptors; customization maps named semantic options to exact original-byte patches. Builders return changed ranges and evidence IDs, rejecting any option without a contract.

- [ ] Establish mode admission, dimensions/stride, planes, ownership, cache, cancellation and RAW ranges from official capture calls. Add full-resolution and boundary-size CPU fixtures, allocator failure and protected RAW sentinels.
- [ ] Port current film colors/LUTs, all supported texture/exposure controls, clock/date and film name imprint; compare scalar shared-algorithm fixtures after explicit pixel/endian conversion. Measure worst-case RAM and processing cost; optimize without silently dropping effects.
- [ ] Independently trace and implement recipe defaults, native names/icons, grain availability, RAW NR, ratios/65:24, level, power images and version policy. Test getter/setter/reset and unchanged original fallback for each, including combination range conflicts.
- [ ] Run `.venv/bin/python -m unittest tests.test_gr2_capture tests.test_gr2_customization tests.test_gr2_renderer`; unresolved features remain researching rather than unavailable. Update ledger and commit only established implementations.

### Task 7: GR II 完整封装与独立审计

**Files:** Create `scripts/build_gr2_m10v_firmware.py`, `scripts/verify_gr2_m10v_candidate.py`, `node/gr2-native-library.mjs`, `tests/test_gr2_candidate.py`, `node/gr2-native-library.test.mjs`.

**Interfaces:** `build_gr2_candidate(official: bytes, configuration: dict, output: Path) -> dict`; `verify_gr2_candidate(official: bytes, candidate: bytes, configuration: dict) -> dict`; verifier independently decodes fields/checksum/configuration, checks original continuation and unchanged ranges. Node bridge uses existing job cancellation/source-binding conventions.

- [ ] Add failing tests for minimal candidate, every exposed feature combination, changed source, bad preimage, bad checksum, stale configuration and cancellation; failures must not leave a final downloadable file.
- [ ] Implement checksum-preserving-policy packaging with the Task 3 algorithm, exact bounds and atomic final output. Prove accepted output filename from the camera update lookup path; never guess a GR3 filename.
- [ ] Run `.venv/bin/python -m unittest tests.test_gr2_candidate` and `node --test node/gr2-native-library.test.mjs`; independently recover original bytes and untouched components, update ledger and commit.

### Task 8: GR/GR II 页面完整操作与服务接入

**Files:** Create `node/adapters/gr1/index.mjs`, `node/gr1-native-routes.mjs`, `node/gr2-native-routes.mjs`, `web/gr1/index.html`; modify `node/adapters/gr2/index.mjs`, `node/server.mjs`, `node/model-firmware.mjs`, `web/gr2/index.html`, `web/shared/navigation.js`, shared workbench bootstrap and SD page routing; create `node/unity-routes.test.mjs`, `node/unity-workbench.test.mjs`.

**Interfaces:** `/gr1/` and `/gr2/` reuse the existing workbench flow with model-specific endpoints and isolated draft keys. Adapter capability responses contain status/can_read/can_build/evidence/reason per feature; GR native build remains unavailable until Task 9 passes. Do not duplicate the current read-only studio as a claim of full parity.

- [ ] Add route/state tests for model recognition regardless of filename, wrong-model imports, official root sources, draft isolation, source replacement invalidating preflight, undo/redo, cancel and old download rejection.
- [ ] Wire both models into the real workbench, film catalog, LUT/power-image controls, source/config import/export, preflight/save confirmation, job status and SD export. Keep unproved writes gated per feature.
- [ ] Run `node --test node/unity-routes.test.mjs node/unity-workbench.test.mjs node/navigation.test.mjs node/model-firmware.test.mjs`; exercise both routes in a browser from import through all available controls and GR II verified download, recording console/network failures and screenshots.
- [ ] Update ledger/browser evidence and commit. GR route may show a research state until its own runtime passes; do not reuse a GR II build for GR.

### Task 9: GR 5.01 独立原生实现

**Files:** Create `native/gr1/`, `scripts/analyze_gr1_native_contract.py`, `scripts/build_gr1_runtime.py`, `scripts/build_gr1_customization.py`, `scripts/build_gr1_m10v_firmware.py`, `scripts/verify_gr1_m10v_candidate.py`, `node/gr1-native-library.mjs`, `tests/test_gr1_native_contract.py`, `tests/test_gr1_menu.py`, `tests/test_gr1_storage.py`, `tests/test_gr1_capture.py`, `tests/test_gr1_customization.py`, `tests/test_gr1_candidate.py`.

**Interfaces:** Same semantic and report interfaces as Tasks 4–7, with model-local `gr1_` symbols and exact GR identity. Shared test fixtures contain no GR II fixed addresses or C object layouts.

- [ ] For every GR II contract, independently trace the equivalent GR function, caller, object fields, resource format, load range and original bytes. Add tests that reject a substituted GR II profile even when symbols and names match.
- [ ] Implement and test GR services, menus, persistence, rendering/textures/watermarks, customization and packaging using the independent contracts; run the same behavioral fixture matrix and per-model full-resolution limits.
- [ ] Run `.venv/bin/python -m unittest discover -s tests -p 'test_gr1_*.py'`; independently audit complete `.frm`, unchanged components and state/config readback; enable only passed capabilities.
- [ ] Exercise GR HTTP/browser download and SD workflow; update ledger and commit.

### Task 10: 全功能验收与交付

**Files:** Update `docs/testing/gr1-gr2-parity.json`, create `docs/testing/gr1-gr2-acceptance.md`; update `README.md`, guide/support matrix and changelog using the repository's current format.

- [ ] Run `npm test`, focused GR/GR II Python suites and affected existing GR3/GR4 suites; record test counts and skips separately, and recheck independent final candidate readback.
- [ ] Run `node scripts/check_unity_parity.mjs --complete`; every baseline feature must have implementation evidence or a proved platform limitation. Research gaps keep the task incomplete.
- [ ] Review all changed code and generated audits; repair material findings with focused regressions; verify git diff excludes official/extracted binary resources.
- [ ] Record a separate per-model hardware checklist: stock recovery, boot, menu/focus/back, all film controls, JPEG/RAW+JPEG, bursts/cancellation/storage pressure, restart/SD failures, clock/orientation, level/ratio, power screens and same-scene color. Without hardware, leave these pending and deliver only explicitly labelled offline candidates.
- [ ] Report exact implemented coverage, limitations and unverified hardware items; do not declare 100% complete until the ledger and required acceptance evidence are closed. Commit local source/docs; no push or deployment without scope authorization.

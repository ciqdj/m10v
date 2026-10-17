# GR III → GR IIIx native differential port

## Scope and source identities

This port consumes a GR III candidate whose feature/runtime/composition audits have already passed. It does not replace those audits. `auditGr3Candidate` additionally checks the source candidate container, section boundaries and permitted RTOS/ICONBIN edits. Both source images pass `inspectOfficial` with exact full-file SHA-256 pins:

- GR III 2.10: `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`.
- GR IIIx 1.60: `708e79f3b7b96a7e1581b4acf4c412233050a1832718ef7f06c8397db1b431c7`.

Both decoded RTOS payloads have 17,520,064 bytes. An exhaustive byte comparison finds exactly **31 different bytes in 19 aligned words**. Official section order, offsets and sizes match (the inspector reports sizes; the port computes each cumulative offset and checks equality). ICONBIN and RES match in full. CPU differs and is deliberately preserved as a complete IIIx section, including its checksum, project ID and version. Every other non-RTOS/non-ICONBIN section also comes unchanged from IIIx.

The candidate must retain the GR III outer header and version. Apply any future IIIx version adaptation separately, after the port; this API rejects already version-unlocked GR III inputs.

## All RTOS differences

Values below are four bytes in file order; addresses use RTOS load base `0x53000000`. Each **entire aligned word** is protected, even where only one byte differs. If a GR III candidate changes any protected word, porting fails before output. The instruction meanings describe the immediate encoding, not an inferred high-level hardware contract.

| RTOS offset / address | GR III → GR IIIx bytes | Meaning and preservation risk |
|---|---|---|
| `0x200c` / `0x5300200c` | `49490000` → `49497800` | ASCII model suffix `II` → `IIx`; retain IIIx identity. |
| `0x2030` / `0x53002030` | `4c020000` → `61020000` | Project 588 → 609; retaining III would identify the wrong body. |
| `0x2034` / `0x53002034` | `0e320100` → `9a320100` | Opaque build scalar 0x0001320e → 0x0001329a; exact date encoding is unproven, so retain IIIx metadata. |
| `0x2038` / `0x53002038` | `020a151b` → `013c0b11` | Big-endian component version 2.10.21.27 → 1.60.11.17. |
| `0x2064` / `0x53002064` | `313a3238` → `313a3330` | ASCII build-time substring; preserve original IIIx timestamp. |
| `0x2068` / `0x53002068` | `3a333420` → `3a353020` | ASCII build-time substring; preserve original IIIx timestamp. |
| `0x2078` / `0x53002078` | `4c024c02` → `61026102` | Repeated project ID; preserve IIIx project marker. |
| `0x6b62ec` / `0x536b62ec` | `e25700e3` → `e45700e3` | ARM `MOVW r5,#2018` → `#2020`; model-specific constant, application meaning unproven. |
| `0x6b6574` / `0x536b6574` | `022042e2` → `042042e2` | ARM `SUB r2,r2,#2` → `#4`; model-specific arithmetic, application meaning unproven. |
| `0x81fe4c` / `0x5381fe4c` | `930fa0e3` → `610200e3` | ARM load immediate 588 → 609 into r0; project/version reporting code. |
| `0x81fe54` / `0x5381fe54` | `0e0203e3` → `9a0203e3` | ARM `MOVW r0,#0x320e` → `#0x329a`; date/build scalar low half. |
| `0x81fe6c` / `0x5381fe6c` | `0a0200e3` → `4f0fa0e3` | ARM load immediate 522 → 316; packed public version 0x020a → 0x013c. |
| `0x81fe74` / `0x5381fe74` | `0200a0e3` → `0100a0e3` | ARM `MOV r0,#2` → `#1`; major version. |
| `0x81fe7c` / `0x5381fe7c` | `0a00a0e3` → `3c00a0e3` | ARM `MOV r0,#10` → `#60`; minor version. |
| `0x81fe84` / `0x5381fe84` | `1b0501e3` → `110b00e3` | ARM `MOVW r0,#0x151b` → `#0x0b11`; packed internal build. |
| `0x81fe8c` / `0x5381fe8c` | `1500a0e3` → `0b00a0e3` | ARM `MOV r0,#21` → `#11`; internal version field. |
| `0x81fe94` / `0x5381fe94` | `1b00a0e3` → `1100a0e3` | ARM `MOV r0,#27` → `#17`; internal version field. |
| `0x81fe9c` / `0x5381fe9c` | `0e0203e3` → `9a0203e3` | ARM date/build scalar immediate, as above. |
| `0xd62314` / `0x53d62314` | `e3070000` → `e5070000` | Scalar 2019 → 2021; probable year/resource data, application meaning unproven. |

The data/build scalar at `0x2034` is not relied upon for any address relocation. Uncertain semantics are a reason to retain the exact word, not to replace it with GR III data.

## Hook and absolute-address evidence

The common native build's 61 patch sites comprise 22 main hooks, five ISP hooks, 13 detail sites, nine icon sites, ten settings sites and two resource-bound sites. Their preimages are identical between these two exact official RTOS images: every differing word is enumerated above, and none belongs to those sites. Additional aspect/level/negative-grain/RAW-NR patches are transferred only if their complete GR III delta avoids all 19 protected words. Runtime growth is copied byte for byte, so linked branches, pointers, image resources, settings code, debug code and SD-library implementation retain their original addresses.

Absolute calls and data addresses within the RTOS preserve their target locations because the entire original 17,520,064-byte extent is retained at the same virtual base; appended runtime allocation does not shift stock RTOS addresses. The GR IIIx original instructions/data are identical outside the enumerated model/version words. This proves matching hook preimages and unchanged stock byte layout; it does **not** prove that every stock function has identical effects on distinct lens/CPU hardware. In particular, the two non-version arithmetic constants remain IIIx-specific, and stock CPU interactions execute the complete IIIx CPU payload. No CPU code is transplanted.

## Output and independent readback

`portNativeToGr3x(gr3official, xofficial, gr3candidate)` returns `{candidate, receipt}`. It reconstructs decoded intent from the actual complete GR III diff and RTOS growth, preserving IIIx-specific words/sections. It uses the grown GR III candidate's frame boundaries but only reuses a compressed frame when its output **and the preceding 8,191 bytes** match the target. Other frames become literals. It copies the IIIx outer 128-byte header and footer identity fields, repairs decoded and outer sum32, and enforces a file size below 128 MiB.

`verifyGr3xNativePort(gr3official, xofficial, gr3candidate, xcandidate)` revalidates both exact official inputs and the common candidate, reconstructs expected intent again, freshly decodes the IIIx output, then compares **every byte of every section and the decoded trailer**. It also checks the complete outer header, footer identity, padding, bounds and checksums. A supplied receipt is never trusted or accepted as verification input. CPU preservation means byte equality against the IIIx original CPU block, not merely matching its project field.

Generated fixture tests run without ignored release files: `node --test node/gr3x-native-port.test.mjs`. They exercise native-like growth, model-word overlap rejection, unrelated-section rejection, resource transfer, full IIIx CPU preservation, outer identity and cross-frame history safety. Physical IIIx update acceptance, recovery and every native feature require device validation; `camera_tested` remains false.

## 集成与验证结果

网页两个原生导出入口、调试、DSP包头及已知版本模式均已按机型开放。GR IIIx 使用公共1.60.11.17基线；常规版本适配只抬DSP包头，CPU整区不改。配方、原厂预设等旧定制流程也先执行原GR III构建与独立审计，再按同一型号保护移植。仅修改原厂参数的零扩容路径显式允许增长0，原审计默认仍要求正增长。

实际IIIx全扩展调试固件与无需配置文件的CLI导出通过，正确输出fwdc243b.bin。最终IIIx BIN执行5项ISP ARM检查、2项拍摄日志检查通过。Node全量243项首次发现两项（旧SD导出拒绝预期、零扩容适配条件），已修正；其后相关16项回归全部通过，独立UI/机型导入24项通过，真实HTTP/组合导出8项通过。发布保护Python15项通过。以上不包含IIIx实机启动、刷写或成像验收。

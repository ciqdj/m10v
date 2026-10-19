# GR III V9: Still ingress and shared HDF

Local test branch only. No push, deployment or flashing.

## Device evidence

Desktop fwdc239b.bin SHA256 e27d66322560752cc9c7d824d141674bac32602a178036142a2c6d8ed401a59a, build7e993f7b. Six supplied CP/IO/MN pages decoded without CRC rejection into /private/tmp/gr3-v8-latest-device.json. Complete retained captures show native mask0, CPU stages1, grain0 and leak0. Phoenix total17452ms/color17451ms;5207 total20054ms/color20053ms;Gold total14699ms/color14699ms. Retained preceding color stage18111ms has no complete film prefix. The samples do not establish missing files.

## Root cause and correction

Stock constructor5350f564 stores the Develop vptr at recipe+96c. Stock setup5350eb34 stores sourceRecipe+1a8 at destination+99c, and5350eb30 stores SI at destination+9a0. Since the process reads context+30/+34, context=destination+96c. The native completion gate incorrectly required recipe+970, rejecting normal still frames and falling back to24MP CPU color. Historical ingress notes and hand-built fixtures shared this4-byte error.

The corrected gate retains same-recipe ownership, ShootingInfo, sequence and state equality. It does not authorize completion merely because a profile was selected. Regression now executes original5350eb10..eb38 setup instructions. The previous delivered BIN fails27 native-application assertions with status1; the corrected final BIN passes. Cross-owner completion remains rejected.

Color applies at original Still Make before subsequent processing, rather than after JPEG output in CPU. This restores the intended shared source for JPEG and immediate review, but LCD timing/color remains a physical-camera acceptance item. No separate QuickReview buffer is painted or forcibly released.

## HDF integration

Standalone HDF keeps its existing16-byte tail and eight hooks. Combined native/live/HDF uses only the trace allocator50f0 and the three explicitly reserved RAW-token words50e4..50ef for ready/strength/SI. The RAW lifetime header/control fields50c0..50e3 and color snapshot4a08..50bb remain disjoint. Factory initialization zeroes all storage; RAW transitions preserve reserved words.

Both post-mutex producer adapters snapshot HDF via its existing validated journal. ISP callbacks do no filesystem work. Request gating and original Clarity coefficient rows remain unchanged. HDF plan/execution settings run within the existing native-grain helper, avoiding two replacements of535033d8/53503aa0. HDF completion remains independent of whether native grain planning succeeds. The HDF menu moves to TopMenu+19bc after the live cache193c..19bb. Combined menu owner bytes1b7c. No new DMA, pixel loop or competing allocator.

HDF defaults off; enable MENU > 设置 > HDF 模拟. Existing HDF journal is retained. Live preview still displays native color only; this change does not claim live HDF/halation.

## Acceptance boundary

Final BIN must pass delivered Still/Live/HDF, readonly menu, capture/RAW guards and deferred review checks; Node independently audits100 unique hooks. These verify ARM code and mocked OS/hardware boundaries, not actual ISP pixels, SD persistence or sustained physical bursts. Expected benefit is removal of the measured15–20s CPU color pass when native completion is accepted. Actual end-to-end latency and blackscreen recovery require the next camera logs; no measured speedup percentage is claimed.

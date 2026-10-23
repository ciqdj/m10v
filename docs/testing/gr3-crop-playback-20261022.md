# GR III crop/playback candidate r3 · 2026-10-22

Status: USER_VALIDATED (2026-10-22). User feedback: “发布github和宝塔，测试OK”. Accepted GR III 2.10 r3 BIN and ZIP identities are recorded in `gr3-crop-playback-user-acceptance-20261022.json`. The original delivered package remains unchanged. Verification below describes the offline work before device acceptance; release integration evidence is recorded separately.

BIN SHA-256: `4c3dea9ecae2c79c5e53978f525874611d11d016c4beb692f5c57b4775d75621`.
Official input: `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`.
Git base: `c988e7a907d22fa68a8412a656f3c8b0bb40ff1a` plus the preserved dirty workspace. Exact native/integration/config fingerprints, individual source hashes and source snapshot are in evidence/provenance.json; HEAD alone does not describe the candidate.

## Changes and protected behavior

- Crop overlay: masked XPan/6x7 uses the same original native 3:2 focal-crop source in AF/common refresh and consistent live dimensions. Final JPEG/DNG ratios, IDs, dimensions and tags are preserved.
- JPEG bridge: an authenticated owned per-shot selected tone is consulted before rejecting a lagging stock SI carrier. Ordinary stock frames, invalid/foreign snapshots and RAW-only requests remain gated.
- Playback: CPU color fallback also processes the two independent already-resized secondary JPEG sources. Matching aliases are processed once; partial/protected aliases fail closed. YUV420 uses a bounded two-row chroma stripe; visible padding is preserved. Optional spatial effects remain on the main image in this fallback path.
- Memory: main planes/scratch, thumbnails and stripe protect the complete applicable recipe allocation (stock, standalone HDF or extended lifecycle metadata), RAW backing and current metadata. Stripe additionally excludes original preview planes.
- Defaults: fresh settings, switching films and resets keep grain/halo/leak off; stock slider default markers and Python/JS export defaults agree. Existing valid journals retain user values. Switching to a custom LUT does not inherit another film's leak gain.
- Compatibility: exact previous 47-film record digests and custom renderer contract are accepted. LUT/interpolation/pixel algorithms were not changed. Unknown or corrupted records are still rejected.

Stable film IDs/data, five slots, native-completion fast path, HDF menu (initial strength zero), RAW lifetime checks, original controls and journal priority remain. Unrelated existing A/B code has not acquired new device acceptance from this work.

## Verification

Production source was frozen for final verification. Later edits only corrected Python test preparation; their fingerprints and reasons are recorded in evidence. The delivered BIN remained byte-for-byte unchanged.

- Complete Node source suite: `npm test -- --test-concurrency=4 node/*.test.mjs`, all 100 source test files, 300 cases: 292 passed, 0 failed, 8 optional fixture skips. Historical copies under builds/ were excluded. Skips concern Python backup, GR II images and supplied GRLife comparison images; GR III official input/build checks executed.
- Actual r3 BIN: 33 crop/DNG, playback/fallback/alias/RAW-safety, Still/Live submission checks passed. Runtime extracted from the BIN matched its manifest hash.
- Actual r3 BIN HDF: 11 functional checks passed, including shared allocator, immutable per-shot settings, RAW/color metadata isolation and native processing success/failure. Debug-only HDF log-event assertion was run separately with the current-source debug fixture; all 12 HDF checks passed there.
- Preservation cohort: 257 planned Python/ARM cases covered through the broad run and focused re-runs, with no unresolved failure/skip. The initial broad run had stale test assumptions (automatic halo), four null icon-view fixture errors and missing local fixtures. Full method names and initial diagnostics are retained in `evidence/validation-logs/preservation-initial-with-fixture-failures.log`; every affected method was re-run after correcting test preparation. Capture's 17 checks passed after explicitly enabling the effect under test; native detail's 34 checks passed after initializing the original IconView type. Original pixel/failure/ABI assertions were retained. The 20 remaining menu/stock-file-handle checks passed with the pinned RTOS and delivered BIN supplied.
- `git diff --check`, generated SD contract check, final configuration/source binding, ZIP CRC and artifact/hash readback passed. Composition verified 136 hooks; RTOS growth 957264 bytes remains below the existing 960 KiB budget.

Reproduction logs prove the old failures, including metadata overwrite at recipe+0x50c0 and stripe alias with preview planes. The independent reviewer rechecked the revised allocation/alias guards and found no remaining important issue. Baseline/current UI diagnostics independently identified the old fixture's missing IconView vptr; test changes do not replace the native View bounds method with a success stub.

These checks execute ARM adapters/native leaves with explicit OS/ISP/hardware boundaries. Actual focus smoothness, saved JPEG/preview consistency, first-shot transitions from Standard/Vivid/B&W, physical cache coherency, burst latency and SD durability still require this exact candidate on the camera. No speedup percentage is inferred from emulation.

## Device acceptance and recovery

Use the accompanying README.txt. Verify both crop ratios with every focal crop, repeated half-press/release and focus points; JPEG and RAW+JPEG; immediate playback, thumbnails and zoom; first shot after changing films, including stock-to-film transitions, and repeated captures; manual effects/reset/restart; original controls and RAW-only.

Existing journal values intentionally survive the upgrade. To check the new off defaults on an existing roll, reset that roll's effects in camera, then enable only desired effects. Do not delete personal state or replace a custom card library with the bundled default pack.

No device installation has been performed here. Recovery uses the previously accepted firmware and a complete power cycle, retaining personal state/card data. User has now explicitly accepted this candidate and authorized GitHub/main/Baota publication. Device acceptance is user-reported; the assistant did not operate the camera.

## Release integration

Integrated on production `5db685d3d12e202e3359bee2512d6653be1599c0` in a separate worktree. Kept the production timeout fix and additional regression audits. Rebuilt through the normal web export pipeline: BIN, runtime, SD pack and configuration are byte-identical to accepted r3. Source/fingerprint exceptions and readback hashes are in the acceptance JSON. The accepted ZIP was not rewritten.

Fresh integration checks: 301 Node cases (291 passed, 0 failed, 10 optional local-fixture skips); 35 delivered/native ARM checks; 24 deployment Python checks; 3 changelog checks; generated SD contract and diff checks passed. The server smoke build intentionally enables debug and explicit stress-test settings; it is separately validated by Actions and does not change web defaults or expand camera acceptance.

# GR III 2.10 independent SD film library

Implementation branch: `daily/gr3-sd-film-library`. This is an offline-verified candidate, not a camera-qualified release. GRLife pages/images supplied by the user informed the interaction requirements only; no GRLife code, format, keys or services are used.

## Original firmware evidence

Official firmware SHA-256: `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`.
Decoded RTOS SHA-256: `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`.

`python scripts/analyze_gr3_sd_library.py RTOS.bin --out original-io.json` verifies the original image hash and executes its real master read/seek/tell wrappers plus concrete filesystem driver. Only media syscalls, mutex leaves and error translation are substituted. A request for 4096 bytes returns boolean success for actual reads of 4096, 1024 **and zero** bytes. Therefore the adapter checks absolute seek and tell before/after every read; success alone is insufficient.

| Interface | Original address / layout |
| --- | --- |
| SD manager | getter `0x535847d8`; filesystem member `+0x14` |
| Master vtable | `0x53d252d0` |
| Open / close | `[7] 0x53593e90` / `[8] 0x53593cec` |
| Read | `[9] 0x5359279c` (boolean, not byte count) |
| Seek / size / tell | `[11] 0x53592974`, `[12] 0x535948c4`, `[13] 0x53592a60` |
| Driver exercised | `0x53d2201c`; real read `0x53589a68`, media leaf `0x5389e624` |
| AppData manager | getter `0x53828014`; member `[2]` then `[0]` |
| AppData write | `0x53825fa8`; variable payload length, primary F: and H: backup |
| AppData raw size / load / release | `0x5362e160`, `0x5362e294`, `0x5362d478` |
| AppData header check | `0x538253e8`; eight-byte header, original checksum |

The ordinary AppData reader `0x53825648` copies the requested length without proving the actual payload length. New 12 KiB snapshots instead precheck raw size 12296 before loading, recheck actual size, run the original header validator, require payload size 12288 and pointer `raw+8`, then compare every byte. The original variable-length writer has no observed 64-byte cap. **Physical partition quota, write latency and durability are not established by disassembly or emulation.** Private snapshots are immutable per supported film ID, up to 33 × 12296 bytes per primary/backup volume. Allocation/write/readback failure prevents the subsequent slot update. The pre-stat/load pair is not an atomic filesystem operation; no other M10V code writes those immutable files concurrently.

## Pack and compatibility contract

`SD/M10V/FILMS.M10` contains a 4096-byte header and one 12288-byte record per selected film. Header carries model 239, schema/capability version, exact file size, ordered unique IDs and record CRCs. Each record carries name/group, recipe parameters or tables, RGBA icon, reserved zero bytes and CRC. Generated SHA-256 contracts bind all record bytes to the supported renderer revision. Header count is bounded at 256; current export accepts only the platform's 33 films, IDs 33–65.

This is a **closed renderer-version library**: complete records are exported and persisted, but rendering continues through the existing immutable ROM implementation selected by saved ID. It does not interpret arbitrary new SD color algorithms or render directly from the snapshot. New/changed recipes require regenerated contracts and matching firmware. This preserves existing JPEG rendering, grain, softening, halation, timestamp, and old configuration semantics.

## Camera path and isolation

An optional `M10V_SD_LIBRARY` build adds `SD Film Library` to the existing `M10V Library` controller. Choose Slot selects one of five existing real tone slots; the SD menu has eight films per page, Previous/Next, Back and Done. Private menu IDs never go to stock tone setters. The currently focused film identity is rechecked on confirmation, then the selected record is read and authenticated, the SD file is closed, the complete snapshot is saved/read back, and only then the existing slot journal is updated. Other slots/effect settings remain untouched. Capture has no new SD read or handle dependency.

The Python builder defaults to the existing non-SD mode. The web GR III builder enables SD support; GR IIIx remains unchanged. Native resources end at 914 with SD (910 without); the aspect extension receives the following resource ID (915 / 911). Both are verified in the byte-exact composition audit. The 512 KiB allocation limit remains enforced.

## Validation boundary

Node codec/API/build/composition tests, host parser tests, linked ARM camera/menu tests, and original-wrapper probes cover corruption, short reads, absent/failed IO, pages, invalid slots, changed selection identity, oversized/truncated snapshots, persistence failures and preservation of other settings. Browser testing covers all/clear/subset and download. These are not physical-camera tests.

Before release, test GR III 2.10 on actual supported SD filesystems: cold boot, all 33/subset packs, all five slots, replacement/reboot/card removal, missing/truncated/corrupt files, full internal storage, interrupted writes, repeated paging, JPEG+RAW capture and all existing effects/extensions. Confirm menu responsiveness, internal free space, image results and fallback after power loss. Do not claim GR IIIx SD support, arbitrary external recipes, or hardware acceptance from this candidate.

## Final offline verification (2026-10-16)

- `npm test`: 187 tests, 181 passed, 6 skipped, 0 failed. The skipped tests require optional Python-backup/800T/GRLife comparison fixtures; they are not evidence for this implementation.
- `.venv/bin/python -m unittest tests.test_gr3_m10v_library tests.test_gr3_m10v_library_arm tests.test_gr3_sd_library tests.test_gr3_sd_menu tests.test_gr3_sd_camera`: 45 passed.
- `node scripts/generate_gr3_sd_contract.mjs --check`: passed; `git diff --check`: passed.
- Independent review: corrected pre-allocation snapshot length check; no remaining concrete findings. A regression exposed fixed aspect-resource IDs, now derived from the audited resource range and covered by full composition tests.
- Actual browser download: two selected IDs [33,34], ZIP CRC verified, unpacked payload audited as 28672 bytes. All-current export has 33 records and 409600 bytes before ZIP overhead.
- Candidate generated through the same web pipeline: SHA-256 `941dd5fe3ecc403bc98684a0c5fc9bbe8990354962601775bf0f0da3f0adc2c0`, 30984332 bytes. Runtime 482848 bytes; RTOS growth 485472 bytes; 34 verified hooks; only RTOS changed. Status remains `OFFLINE_VERIFIED_EXPERIMENTAL_CANDIDATE`.
- Ignored local evidence directory: `builds/sd-library/` (logs, original IO probe JSON, candidate/receipt/manifest, browser screenshot and all-33 ZIP). No flash or deployment performed.

When the renderer algorithm changes, maintainers must revise the SD schema/capability contract as well as rebuilding record hashes; current hashes authenticate record bytes, not an independently delivered executable renderer.

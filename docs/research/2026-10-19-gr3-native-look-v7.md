# GR3 native color look module, V7

`m10v_isp_native_look.[ch]` is a linkable per-shot parameter producer and applier. It supports film33..68, including RED EI125/64/250. It never reads image-size pixel buffers. Existing full-resolution texture, halation, diffusion, leak and stamp stages remain the caller's responsibility. This is a new native color generation, not CPU LUT equivalence and not a measured film-stock calibration.

## Integration contract

Keep recipe allocation and ShootingInfo ownership unchanged. Store the complete library snapshot, generation/sequence, exact ShootingInfo pointer and carrier tone in the existing recipe record. At the original StillMake completion boundary, check the recipe's exact ShootingInfo and carrier tone (12 or 18..21). Construct a local 1600-byte `m10v_isp_native_look`, then:

```c
m10v_isp_native_look_prepare(&look, film, exposure, generation);
int applied = m10v_isp_native_look_apply(&look, stock_gamma, owned_frame, cs);
/* Only after applied && matches(...) may the recipe record APPLIED. */
```

Prepare each time the original StillMake reconstructs frame banks. Do not reuse an APPLIED look after stock has rewritten the same frame address. If using local storage, copy the completion fact into the recipe record only after successful apply; CPU-side completion must additionally match the exact original ShootingInfo, tone, generation and immutable full library snapshot. A global bit or current live library selection is insufficient. Keep CPU color fallback for rejection and unsupported films1..32; skip color only, retaining every non-color effect.

Exposure is 0=EI125, 1=EI64, 2=EI250 for RED; zero for all other films. Profile preparation may run repeatedly without changing global state. Failed writes leave the frame untouched; rejected/READY records never satisfy `matches`. Caller memory must be valid and frame allocation at least0x9000 bytes. This C API cannot validate unmapped pointers.

## Color definitions and evidence

Films34..65 preserve existing exact table parameters, composed relative to the current frame CCA/CSP and initialized stock gamma. Films66/67 use the existing `gr3-native-film-fit` parameters: continuous12-sector transforms, all five native levels identical, stock gamma followed by channel curves, relative pre/post matrices. Sector parameters are reconstructed losslessly from108 signed coefficients into the original six-record writer ABI at0x536df55c. Frame gamma uses the original table packer at0x536e89ec. Only frame-owned banks change; the shared initialized gamma/tuning objects remain byte-identical.

Existing random65536-sample model comparisons against current CPU cube: 5207 P95 ΔE00=4.553 (see manifest for exact value), Phoenix II P95=0.60445. These are model-domain fit errors. Hardware pixels and complete camera behavior are unverified. A creative native generation is explicitly permitted to differ from the old LUT.

RED uses the existing bounded per-EI relative matrix/curve/post definitions as native creative profiles. Their earlier synthetic-reference P95 ΔE00 values are EI125=5.5752, EI64=6.3865, EI250=8.1484. They are not full extracted-stock-gamma model comparisons and cannot substantiate CPU equivalence or a camera visual match. New800T retains mild contrast264, saturation238, lift1, bend3, and a declared blue/cyan midtone correction. It is a representable creative definition, not a recovery of the prior YUV mapping.

ARM probes modify original user controls77d/77e/780/781/782/784 to8. Their changes survive native composition. Those controls change CCA, CSP, gamma or non-color banks, not sector banks. This validates preservation of these exposed controls in the tested original firmware fixture, not unknown firmware controls. Stock WB/tuning memory is not mutated.

## Bounds and validation

Six frame profiles now use48 bytes each: unchanged signed matrices, three initial uint16 curve values and three uint16 offsets into a1849-byte shared bitstream. Each delta-of-delta uses2bits for0/+1/-1, or2bit escape plus8bit absolute original delta. All256 curve knots remain exact; no curve reduction, quantization change or effect removal. Two sector arrays still use216 bytes each. Total static profile data2569 bytes, versus5280 before compression. All18 full curves are unique, so whole-curve dictionaries cannot save space. Ordinary RLE saved848 bytes before decoder cost, and16/32byte dictionaries increased storage; the exact differential codec was selected instead.

Standalone ELF includes legacy data already present in the main library. Code/data fell43914→41626 bytes, saving2288 bytes after decoder overhead. Subtracting the already linked legacy tables/helper33746 gives7880 incremental bytes including frame+multiaxis writers; if frame writer is already linked, increment5668 bytes. Final production combined link remains authoritative. Frozen hashes captured by executing the precompression ARM implementation verify every decoded1572-byte target and every complete0x9000-byte frame for all six profiles, including RED's three exposures and800T. Sixteen ARM tests pass after compression; see builds/gr3-native-look-v7/compression-report.json and compressed-arm-tests.log.

Apply reconstructs a3712-byte multiaxis target in a separate noinline helper for66/67, after the frame gamma packer has returned. Actual original ARM instruction execution observes apply high-water3872 bytes for66/67 and2260 bytes for33/68, versus5988 bytes for every film before separation. With the caller local look1600, peak is5472 bytes for66/67 and3860 bytes for33/68, plus the caller compiler frame. Evidence is saved in builds/gr3-native-look-v7/stack-before.json and stack-after.json. Production integration must verify the actual task stack and combined linker budget. This module does not activate firmware hooks, reserve production RAM, or promise a measured speedup/one-second playback.

Validation: run `.venv/bin/python -m unittest tests.test_gr3_isp_native_look tests.test_gr3_isp_frame_color tests.test_gr3_isp_multiaxis -v`. Tests execute original ARM instructions with Unicorn; they validate API, generation/film/exposure identity, all36 supported films and RED exposures, exact packed profile decoding, full sector bank equality with the original writer, isolation, invalid input rejection and user control preservation. They do not emulate ISP hardware pixels.

Build: `.venv/bin/python -m scripts.build_gr3_isp_native_look --out builds/gr3-native-look-v7`. `--generate-profiles` explicitly refreshes the checked-in lossless header. Original RTOS SHA256 must equal8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67. 5207 spectral-derived profiles retain the MIT Jan Lohse source notice and third_party/spectral-film-lut/LICENSE.

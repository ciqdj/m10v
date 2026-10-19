# Original full multi-axis register writer

`native/gr3/m10v_isp_multiaxis.c` adds a bounded caller-owned target and invokes the **original** `0x536df55c` serializer against the caller's frame + `0x120`. It does not touch shared tuning objects or construct hardware jobs. It is not activated by any production hook.

Original Still Make calls `0x536e4470`, which calls Calc `0x536df484` and tailcalls serializer `0x536df55c`. The source object is six pointers. Actual original ARM memory-read traces established these complete source extents:

| Offset | Native source | Bytes | Accepted field bits |
|---|---|---:|---|
| +0 | 16 boundaries | 32 | 12 each |
| +4 | 20 selectors | 20 | 4 each |
| +8 | 60 matrices of 9 words | 2160 | 12 each |
| +c | 40 matrices of 9 words | 1440 | 10 each |
| +10 | mixed control | 42 | see control_mask |
| +14 | final matrix of 9 halfwords | 18 | 9 each |

The target is 3712 bytes. Signed coefficients retain native field bit patterns; the C module rejects nonzero reserved bits instead of truncating them. Geometry names above describe serialization, **not yet a proven color partition or coefficient binary point**.

Control byte masks were established by injecting every individual source bit and executing the complete original serializer against a zero frame. Boundary, selector, and final matrix masks were measured the same way. Matrix widths are also visible in the original generated BFI instructions. Differential tests fill all complete banks with seeded random valid native bit patterns, initialize destination frames with random bytes, execute both the adapter and original serializer, and compare all 0x9000 output bytes. Inputs remain unchanged. Invalid reserved bits and overlapping source/destination leave the destination unchanged.

Calc input `r1` points at the original temporary tuning context. It reads context+c as the shared record and context+94 as a custom-record flag. In the default branch, shared record+8 and+c are holders whose +10 pointers select the 60- and 40-matrix blocks. Record+0/+4 provide boundaries/selectors; +10 is direct control; +14 is final matrix. In its enabled branch Calc copies the complete 2160-byte matrix block to object+18 and overwrites two 180-byte ranges from context+dc and context+100; it also uses local control/selector storage. Those overlapping context ranges and hardware partition semantics require further investigation before target fitting.

Builder `scripts/build_gr3_isp_multiaxis.py` checks the locked official RTOS hash, emits a separate ELF/bin and no patches. `tests/test_gr3_isp_multiaxis.py` runs ARM CPU emulation only. These tests do not emulate R2Y pixels, establish native-domain target fidelity, or establish a physical timing gain. Arbitrary 15-cube LUT representability and 5207/Phoenix fidelity remain unproved; this module must not replace the full CPU LUT on that basis alone.

## Existing camera evidence and new complete-chain fit

Subsequent inspection found relevant **existing** physical evidence in sibling `gr3-film-mods/FINDINGS.md` sections 29–33b. That evidence supersedes treating the sector geometry as wholly unknown: original GR IV active bounds/control copied to GR III enabled twelve hue regions, with five matrix levels each. The probe chart matched predicted markers on 167/172 colored patches away from edges (corrected gain correlation 0.98). The v16 camera/model comparisons averaged DE00 0.69 versus 0.79 without sectors. These are prior experiment records, not new camera measurements from this task.

The active bounds are `(1298,750,0,0;1448,843,0,0;1298,750,0,0;1205,843,0,0)`. The 20 selectors are `(0,1,2,2,2;3,4,5,5,5;6,7,8,8,8;9,10,11,11,11)`. Group selection uses Cb/Cr quadrants and ratio `2048*x/(x+y)`, not evenly spaced angle sectors. This formula was independently implemented after inspecting `gr-custom-tool/gr4_editor/numeric/model.py`; no GPL implementation was copied. All five levels repeat the same matrix, so unknown level-selection semantics cannot change fitted output.

`scripts/fit_gr3_native_film_targets.py` now jointly optimizes a relative input matrix, twelve seam-continuous neutral-preserving sector matrices (36 free parameters), monotone 33-knot correction curves, and post matrix. It extracts the actual Standard gamma from the original tuning object in CPU emulation. Input RGB is mapped through the **explicit reference-model inverse Standard gamma**, then the fitted native chain. This is not a recovery of scene radiance from JPEG or a claim of measured current film calibration.

Quantized evaluation includes Q13 relative input and Q9 relative post parameters composed and rounded into the actual Standard signed12 CCA and signed9 CSP banks, Q10 signed12 sector coefficients, and exact existing frame-helper gamma correction indexing and rounding. CCA/CSP evaluation uses the default Standard fixture; runtime application must validate each actual frame, not assume these matrices are global. Gamma packer/hardware pixel interpolation itself remains outside the CPU reference model.

Reproducible command: `.venv/bin/python scripts/fit_gr3_native_film_targets.py --train 8192 --holdout 65536 --iterations 1600`. The 8192 random training colors plus three repeated 256-gray ramps use seed 52076731. The independent 65536-color holdout uses seed 67185207. These target the **current full candidate 15³ tables**, whose 5207 display adapter and Phoenix interpretation remain declared assumptions.

| Target | Median DE00 | P95 DE00 | Max DE00 | Numerical fidelity gate |
|---|---:|---:|---:|---|
| 5207 candidate | 1.8404 | 4.5529 | 15.8826 | FAIL |
| Phoenix II candidate | 0.2803 | 0.6045 | 1.5823 | PASS |

Thresholds fixed in the script: median <=0.7, P95 <=2, maximum <=6. The optimizer reached its 1600-iteration budget for both; scores evaluate the actual returned quantized model rather than claiming optimizer convergence. The failed 5207 fit does **not** prove native hardware cannot fit it more accurately; it proves this fitted candidate must not replace the full LUT. Both activation gates remain false because the new complete chain and targets need physical validation. New generated artifacts are `native/gr3/m10v_native_film_fit_targets.h` and `native/gr3/native-film-fit-targets.json`; neither is wired into production.

Moving color ahead of existing CPU spatial effects also changes leak order and halation source selection. Preserving each effect's quality and intended order is an additional integration requirement, even when the native color target passes the numerical gate. This work does not disable effects or call the changed ordering equivalent to the existing render.

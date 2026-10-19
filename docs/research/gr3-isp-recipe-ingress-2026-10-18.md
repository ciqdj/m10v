# GR III per-recipe ISP ingress and observer

This module establishes bounded per-frame ownership and configuration selection. The default observer deliberately preserves original ISP output and keeps complete CPU film processing. It does not claim to accelerate arbitrary3D LUTs or full spatial effects. The user's latest report says blackscreen eventually recovers and JPEG/DNG file counts agree; this work does not establish lost files.

Locked RTOS SHA256: `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`.

## Proven original context

`BEStillRecipe` vptr `0x53d0fc90`, original allocation0x4778. The sole factory at53523db0 calls allocator5351091c at53523e0c then constructor5350f160 at53523e1c. The coordinated trace allocator grows this to0x50c0: traceR+4778/656bytes, colorR+4a08/1716bytes, final4bytes alignment. Color header40bytes, target1572bytes, full validated state104bytes. No invented RAM address or mutable appendRX object is used.

Develop config `C=R+96c` has C+30=sourceRecipe+1a8, C+34=ShootingInfo and C+38=input config. This is populated at5350eb10..eb34; other5350e624 dispatch branches also populate the same fields. This source recipe can differ from the destination config owner; derivation follows C+30 rather than subtracting96c from arbitrary C.

DevelopMacroProcess vtable begins53c627b8. Its process53501c38 receives context via message+8 at53501c60 (r6). At53501d04..1d2c, the metadata initializer receives r0=module,r1=module+40 R2Y info,r2=module+8314,r3=C. Default initializer535059ec reads C+34/C+38, stores info+82d0=ShootingInfo at53505afc and info+82ac=0 at53505b1c. Therefore this real Develop call uses stage0, unlike earlier manually initialized stage1 research fixtures. It does not identify all stage0 calls as LiveView.

At53501d50..1d68, ImageTuningFactory selector3 returns the stock Still object, and virtual+1c invokes Still Make536dd8f0 with r1=module+40. The installed53501d68 BLXr3 adapter has access to C in callee-saved r6. It derives sourceRecipe=C[30]-1a8 and validates recipe vptr, allocation trace magic, state header, SI identity and frame tone. Its pre-helper binds the frame/tuning only until the displaced original call returns. Post-helper clears these transient pointers. No unused R2Y info field is repurposed.

Color-space conversion in original536dc474..494 uses shot+7be==1. The original context at the gamma call is a temporary Still Make stack object, so the recipe hook does not retain it after return. Experimental application reads color space from the same original shot.

## Producer placement and locks

Factory wrapper53523e84 acquires the RecipeManager mutex at53523ea0 and releases it at53523ed8. Both callers in5351ae2c also hold BE owner+a74: acquired5351ae9c/released5351aed0, or acquired5351b050/released5351b064. Filesystem load is therefore excluded from the locked factory.

Optional producer patches are5351aed4 and5351b068, each originally `ldr r2,[r4,#0xf0]`. They execute after both original mutexes release, read the newly created recipe from BE owner+f0, call camera_library_load once for that recipe, then copy the complete validated104-byte state into its tail before queueing. A previously initialized snapshot is reused. The adapters preserve original GPRs, SP/LR and CPSR, then execute the displaced recipe load into r2. Full global filesystem lock ordering and real-camera timing still require hardware validation; the established local contract is specifically post the two backend/recipe mutexes.

The ISP hook never invokes SD/filesystem services. CPU fallback must call `m10v_isp_frame_recipe_state(recipe,out)` to consume exactly the saved sequence/slots/effects/stamp. If producer load fails, no valid snapshot is published; the caller must retain its explicit error/fallback behavior.

## Modes and return status

`build_gr3_isp_recipe_color.build(..., observer=True, producer_snapshot=True)` emits three checked patches. Observer records status7 (OBSERVED) and leaves all original color banks unchanged, including films66/67/68; the CPU full LUT/effect chain remains required. The default builder does not enable producer patches unless requested. A matching0x50c0 owner allocation manifest is mandatory.

`observer=False` is an experimental hardware-parameter application mode. It supports only matrix/curve/post model IDs34..65 through the exact production table decoder, then the existing bounded frame writer. IDs outside this representation are status6 (UNSUPPORTED); no3D LUT is fitted or silently approximated. Parameter reachability does not prove JPEG pixel equivalence because the hardware matrix sits in a different processing domain. This mode must not be the default quality-preserving production path.

Statuses:0 empty,1 ready,2 applied,3 rejected,4 SI/owner mismatch,5 reserved busy,6 unsupported,7 observed. Only experimental status2 means parameters were applied. Status7 must never skip CPU processing.

Original gamma536e9000 copies some stack bytes into cache fields. A naïve wrapper that changes its SP changed cached bytes320c/3221 despite identical tables. The separate gamma probe adapter was corrected to execute original gamma at its exact original SP. The Develop adapter similarly pops its preparation workspace before displaced BLXr3; original main Make sees its original SP. Its result registersr0-r12, LR and callee-saved VFP remain preserved.

## Executed verification

`tests/test_gr3_isp_recipe_color.py` compiles the exact production state validator and legacy table decoder, runs the actual installed callback and original stock Still Make in ARM Unicorn with ROM read-only, and covers all five slots/stage0 and1, same tuning recovery, queued state sequence stability, invalid CRC/foreign owner/SI mismatch/unsupported3D LUT, in-flight reselection rejection, both post-mutex producers, complete GPR/CPSR/VFP preservation and observer output byte equality. Filesystem loading is replaced only at its explicit camera_library_load service boundary in producer ABI tests; these are not physical SD or hardware ISP pixel tests.

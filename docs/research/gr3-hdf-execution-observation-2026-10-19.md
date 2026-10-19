# HDF final-JPEG no-effect: targeted observation

User confirms V9's other behavior works, and HDF strongest has no visible effect in final JPEG playback. There are no new device logs attached to this report; previous Desktop paths no longer exist. Do not infer a new device root cause from the previous build's logs.

Static checks retained the existing original Clarity function5367c158, native range and coefficient row shims, per-recipe HDF journal, settings planning and execution adapters, and same-recipe/SI checks. These checks do not prove hardware effect execution. Prior tests called the producer/gate/settings in isolation and proved values, rather than observing the original digital-filter result for HDF independently of grain.

The HDF ready word now retains diagnostic bits:1 snapshot loaded,2 gate passed,4 settings written,8 original digital-filter success with the expected HDF parameter,16 original failure or changed parameter,32 SI gate rejection,64 context ownership rejection,128 settings load failure. Control checks still use bit1; diagnostic failure bits cannot enable HDF. No tuning coefficients, film tables, photo dimensions, buffer allocation/free, DMA, waits or storage ownership change.

The original digital-filter postcall53503ab4 already invokes recipe_grain_done; the HDF observation now runs before the native-grain early return, including grain off. It records the unchanged original result and verifies the still-current clarity parameter. This is a whole digital-filter return, not a direct measure of ISP pixels or a calibrated optical HDF effect.

At existing preencode phase193, the same recipe-owned trace flush emits event198/tag48444601 with packed flags/strength and SI. No extra filesystem call is added in ISP. Decoder attaches this as lifecycle_profiles[].hdf. Actual final-BIN test executes producer/gate/settings/done and the existing lifecycle flush, confirming the full record. This does not fabricate native completion or alter CPU fallback.

Validation:44 delivered ARM/menu/decoder checks plus1 added actual flush check;26 standalone HDF/menu/profile/lifecycle decoder checks;2 Node preparation and real server export tests;100 independently audited hook sites. The old final BIN fails the new HDF completion-observability test as expected. Sources and final RTOS runtime hashes are checked before packaging.

Local diagnostic candidate only; no publication, deployment or flashing. Next hardware evidence: same film/scene, HDF off then strongest, each confirmed with OK. Collect six CP/IO/MN pages, HDF journal M10VHD0.BIN/M10VHD1.BIN, ideally both original JPG files. That distinguishes setting load/gate rejection/parameter write/native return from an executed parameter model with no expected visible effect. No hardware fix is claimed yet.

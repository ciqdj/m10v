# GR III 28–50mm production integration · 2026-10-26

Production/source base: `9cded6efd7a1bf48643c5b5a74a68a4a3959189c` (GitHub main/develop and live Baota HEAD agree). User accepted candidate BIN `99794ec21804aa15f83319e7bba05d67ba4b79780e6d296f909e87f33b1a8442` and authorized main/GitHub/Baota release. User additionally requires all other behavior from current main and future iterations to start from latest main; recorded in grkit-development.

Integrated only crop feature and its shared entry points. Kept current main film directory, ten-slot selection, state ABI, controller tail allocation, packed artwork, model import behavior and deployment workflow. Existing IDs0..781 remain; focal IDs moved to782..854 without changing artwork. Eight validated crop functional source hashes retained. No >50mm/private LCD/AF/tracking/auxiliary pipeline is integrated.

Integrated local BIN SHA256 `89ba8c6aab70a8a52a8f9476c40cfbdd4f0b9538c01c709b0f28014cb2c7982e`; 157 verified hooks. This differs from device candidate due to current-main film/runtime integration and collision-free icon IDs. It is offline integration evidence, not new camera acceptance of unrelated main features.

Checks: five final packaged ARM widget/blitter/rotation/OOM/directory tests passed; 40 targeted settings/crop checks passed with five fixture-dependent skips; 44 targeted Node configuration/catalog/settings/save-gate/deployment tests passed; 24 Python deployment/codec checks passed. Changelog2026.10.26.1 and skill validators passed. Official preimages, package decode/readback and excluded experimental hook sites passed. Fixtures adapted to current main controller offsets and28..50 range; no crop implementation changed to satisfy fixtures.

Full regression skipped per user instruction. Additional UI-contract run: eight tests pass and one existing GR II homepage wording assertion fails (`只读检查` versus production `实验第一版`); main homepage remains byte-identical and is outside crop scope. No unrelated UI rollback introduced.

# Final product UI verification

Verified on 2026-10-11 against the loopback Node service.

## Product structure

- `/` presents GR III and GR IV as separate product workspaces.
- `/gr3/` and `/gr4/` use the same black product bar, camera switcher, three-column desktop layout, panel geometry, color tokens and responsive behavior.
- GR III and GR IV both use a left function navigation, center editor and right firmware/build/history rail.
- GR III navigation switches between firmware information, crop preview and shutdown-image editing without reloading; backup/recovery and modified-firmware export stay in the right rail.
- GR IV retains the complete latest-reference workflow: filters, XMP, icons, calibration, crops, shutdown images, project import/export, toolchain, builds, history and rollback.
- GR IV's project menu also exposes an immutable original-firmware backup after a firmware has been imported.

## Rendered checks

- Desktop: 1440 × 900 for GR III and 1280 × 900 for GR IV.
- Narrow: 490 × 849 for both workspaces.
- Observed document width matched viewport width at 490 px for both pages; no horizontal overflow.
- GR III and GR IV browser consoles contained no errors after navigation and menu interaction.
- GR III function navigation and GR IV project menu opened successfully.

## Firmware-backed check

The exact supplied `fwdc239b.bin` was imported through the rendered GR III UI:

- model/public version: `GR III / 2.10`
- internal version: `2.10.21.27`
- size: `30,391,780` bytes
- partition rows: `14`
- UI status: structure verification passed; no script error was shown

The GR III shutdown-image workflow also exported a rebuilt `fwdc239b.bin` through the rendered page. The exported package retained internal version `2.10.21.27`; container checksums, decoded checksum, CPU checksum, section layout, JPEG readback and non-target ranges were verified by the export path.

No GR IV official BIN was available, so GR IV import/build and camera behavior remain outside this UI verification record. The editor and route contracts were tested without inventing sample or hardware results.

# m10v Final Multi-Model Product Design

**Status:** Proposed for implementation  
**Reference:** `gr-custom-tool` commit `549591db6ee7809fa7617c3637296ddc79b34f59`  
**Models in this release:** GR III and GR IV; GR II remains an unsupported placeholder

## 1. Product outcome

m10v becomes a local desktop-class firmware product rather than a diagnostic
dashboard. A user starts at a concise model home, enters a dedicated GR III or
GR IV workspace, completes the supported workflow without using raw HTTP APIs,
and can always distinguish source backup, offline verification and hardware
verification.

The release is complete only when every advertised capability has a visible,
usable UI path and a tested loopback API path. A status card that merely says a
backend exists is not feature completion.

## 2. Product structure

### 2.1 Product shell

- A restrained full-height shell with model switcher, current-project identity,
  persistent evidence badge and one primary action per screen.
- `/` is the product home and recent-project entry, not a long test report.
- `/gr3/` and `/gr4/` are isolated workspaces with their own terminology,
  filename rules, version policy and capability gates.
- Shared visual tokens cover typography, color, spacing, dialogs, notices,
  empty/loading/error states and responsive layout.
- The UI does not show inactive research controls beside production-ready
  controls. Blocked capabilities appear in a dedicated evidence panel.

### 2.2 GR III workspace

- Import the exact supported official `fwdc239b.bin` and show identity,
  internal/public version and section report.
- Export and validate a computer-side original-firmware backup; rehearse restore.
- Prepare only an exact official file on a removable SD card with readback.
- Show discovered shutdown resources and safe browser previews.
- Preserve the imported internal version for every GR III candidate path.
- Keep modified-firmware export locked until the existing GR III executable,
  checksum, camera-acceptance and recovery gates have evidence.

### 2.3 GR IV workspace

The GR IV workspace exposes the complete feature set of the pinned latest
reference release:

- Firmware import and strict container/layout inspection.
- Filter list, search, factory/custom identity, enable/disable and ordering.
- Add/remove filters from templates; name, icon and native parameter editing.
- Full Look/Profile XMP import and conversion status.
- Offline calibration and Windows Lightroom Classic bridge selection.
- Three bundled GR IV DNG samples, held-out selection and calibration execution.
- Custom crop creation, naming, geometry preview, confirmation, ordering and
  deletion.
- Shutdown item creation, image upload/replacement, contain/cover fit, preview,
  16-item limit, ordering and deletion.
- Save/resume local edits plus JSON edit-backup import/export.
- LLVM/LLD discovery, validation and persisted configuration.
- Build settings, explicit risk acknowledgement, candidate generation,
  manifest download and `fwdc248b.bin` download.
- Local build history, detail inspection, open as source and rollback candidate.
- The known `allow_older` version-gate option and its factory-reset warning.

The first generated GR IV version from `1.11.10.7` is `1.11.10.10`; later
versions use the matching local maximum plus one. This policy never applies to
GR III.

## 3. Reference integration

- Vendor the current reference Python core, native sources, product UI assets,
  Lightroom bridge, calibration JSON and three DNG files.
- Record every included file hash and source commit in provenance.
- Preserve GPL-2.0-only attribution and third-party notices.
- Do not require the sibling `gr-custom-tool` checkout at runtime.
- Add a deterministic sync command; any local divergence after sync fails the
  provenance test.
- m10v-specific work is limited to the multi-model shell, namespaced transport,
  shared backup/evidence surfaces and branding. GR IV domain rules remain owned
  by the reference core rather than being reimplemented in JavaScript.

## 4. API and process architecture

- Node remains the only loopback listener and session-token authority.
- GR IV Python executes as a bounded child worker under Python 3.12.
- All GR IV reference endpoints are exposed below `/api/gr4/`; no operation is
  reachable only through an internal method.
- Binary uploads use bounded request bodies and content-addressed files.
- Worker paths remain confined to the GR IV data root; symlinks and escapes are
  rejected.
- Builds run in private staging and publish only after the reference readback
  and manifest checks pass.
- Downloads resolve an opaque project/build identifier, never a client path.
- Worker stdout is a one-message protocol; diagnostics use stderr. Extra output,
  timeout, nonzero exit or oversized output fails closed.

Required GR IV API groups are status/settings, firmware import, project
get/save/import/export, filter add/remove/icon/XMP, crop preview, shutdown item
and image, calibration state/register/run/output, toolchain save, build,
history/open/rollback and typed downloads.

## 5. Backup and recovery contract

- Every imported firmware is immutable and addressed by SHA-256.
- Each model can download the exact imported original independently of edit
  state or build history.
- Project backups contain drafts and references, not an undisclosed replacement
  for the original BIN.
- Restore verifies the original hash before reopening the project.
- UI copy always says computer-side original/package recovery; it never implies
  camera Flash/NAND recovery or no-brick safety.

## 6. Evidence model

Four labels are used consistently:

1. `source_verified`: vendored source matches recorded hashes.
2. `reference_verified`: behavior passes the pinned upstream tests.
3. `sample_verified`: an exact imported firmware completes decode/build/readback.
4. `hardware_verified`: a recorded camera run completed the stated behavior.

This release has a real GR III official sample and no supplied GR IV BIN. GR IV
must therefore stop at `reference_verified` until the user imports a compatible
file. No UI text may imply sample or hardware verification before that event.

## 7. Visual direction

- Quiet photographic-tool aesthetic: warm neutral canvas, near-black chrome,
  restrained brass accent and high-contrast content panels.
- Desktop layout uses a narrow model rail, functional list, focused editor and
  contextual build/history rail. Mobile collapses to model and function tabs.
- Dense technical hashes and manifests are secondary details, never the first
  screen.
- Empty states explain the next action. Errors stay next to the affected
  control. Long-running work uses a blocking progress surface with a concrete
  operation name.
- GR III and GR IV share brand and navigation but never share unsupported form
  controls.

## 8. Acceptance criteria

### Automated

- All existing GR III Node tests remain green.
- The complete applicable upstream GR IV test suite passes from the vendored
  tree; unavailable hardware/firmware fixtures are named skips, not passes.
- Browser contract tests cover every visible GR IV workflow and verify that no
  advertised action lacks a server route.
- Provenance, path confinement, version policy, immutable backup, interrupted
  build and download-authorization regressions pass.

### Rendered product

- Home, empty GR III, imported GR III, empty GR IV, imported GR IV filter/crop/
  shutdown, setup, build result and history views are inspected at desktop and
  narrow widths.
- There are no placeholder cards, raw JSON editors, broken controls, horizontal
  overflow or test-oriented copy in the primary UI.

### Evidence handoff

- The final report lists exact commands, pass/skip counts and the running URL.
- It separately states source/reference, sample and hardware evidence.
- GR IV sample/build acceptance remains pending if no GR IV firmware is supplied;
  this does not permit hiding or disabling the completed UI workflow.

## 9. Non-goals

- Automatic camera flashing.
- Claiming recovery from a bricked camera.
- Reusing GR IV offsets, version allocation or update-policy patches for GR III.
- Enabling GR II without a separately verified adapter and sample.

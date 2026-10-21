# GR III film timing and preview cache — 2026-10-21

Source: HEAD `c988e7a907d22fa68a8412a656f3c8b0bb40ff1a` plus the existing dirty workspace and this repair. GRKit reference checkout was verified clean at `8a886cbfa7ca3af7726c942d4b0d367d9486acb4`; no GRKit migration is involved. User confirmed GR III. Official GR III 2.10 RTOS SHA256: `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`. Final official BIN hash, complete source/config fingerprints and output hashes belong to the candidate receipt/provenance, not HEAD alone.

## Root cause evidence

Original ARM `5351ae2c` loads the current `BE owner+f0` at `5351ae44`. If nonnull it acquires the BE mutex, submits that recipe through `5352197c` at `5351aea8`, returns it to RecipeManager, clears f0 and acquires the next recipe through `53523e84`. Only then does it reach the old film-snapshot Hook at `5351aed4`; the empty-current branch reaches the other old Hook at `5351b068`. Startup `5351da3c` also calls the same routine to reserve the first buffer. Both former sites therefore freeze the **next waiting buffer**, before the user's next film selection.

`SlotSwitchTests.test_reserved_next_recipe_does_not_freeze_the_previous_exposures_film` installs the actual patches, executes either original reservation boundary, switches the validated film cache and UI property, then runs the original submission prologue. Before the repair it freezes film33 where the submitted shot requires66. Afterward the current recipe freezes66/tone18, while a subsequent UI selection cannot retarget that already frozen recipe.

The new Hook is at `5351ae44`, before the BE and RecipeManager mutex acquisitions and before current-recipe queueing. Null current recipes do nothing. It preserves all GPRs, SP/LR, NZCV, d0-d31 and FPSCR; the independent Node auditor checks each wrapper instruction and the exact original preimage. The existing shared HDF reservation Hooks stay at their original sites and no longer freeze the film recipe there.

Preview cache belongs to the extended TopMenu allocation. Its constructor initializes an empty cache; durable load/store publishes it, and destruction clears it. Previously normal LiveView enter did not create/load that cache, so opening the film library could be the first action that makes color available. The existing native LiveView UI enter adapter now obtains the retained TopMenu and loads saved state only if the cache is unavailable. The constructor and ISP callbacks still perform no filesystem IO. Storage failure leaves the cache unavailable and can retry at the next normal UI entry; ready caches do not reload on each return.

## Impact and preservation

| Area | Previous behavior | Candidate behavior | Evidence / migration |
| --- | --- | --- | --- |
| Film selection | Next buffer could retain previous film | Current recipe freezes before submission | Original ARM reservation/submission regression; no journal/schema migration |
| Queued photos | Recipe owns independent settings | Same contract | Later UI/cache changes cannot retarget a frozen recipe; CPU fallback keeps recipe state |
| Live preview | Empty cache until a menu/load action | Normal UI entry prepares durable cache | ARM cache/loader/publisher tests; no per-frame filesystem IO |
| RAW / grain / HDF | Existing ownership and processing | Preserved | Related lifecycle/handoff suites; HDF reservation timing unchanged |
| Slots / SD / custom / stamps / UI | Current dirty-workspace feature set | Preserved | Full Node suite and selected Python/ARM preservation checks; no IDs or effects refitted |
| Hardware scheduling, LCD and pixels | User reports failures | Requires candidate acceptance | No camera attached; no hardware performance or pixel-equivalence claim |
| A/B DISP | Existing unresolved device report | Not claimed fixed | Separate known issue |

## Validation

The two new behavioral regressions were observed failing before the production repair, then passing afterward. Local logs and pre-repair file copies live under `builds/gr3-film-timing-20261021-baseline/`; `task-delta.patch` isolates changes to files that already contained edits before this task.

Executed checks:

- Core capture/live/native suites: 43 tests, with one shared-HDF fixture class initially unavailable. Covered slot switching, capture snapshots, native handoff/fast capture and appended recipe contracts. Log `arm-regression.log`.
- Expanded reservation/UI-entry/ABI tests: 6 passed, including startup null recipe, non-LiveView zero IO, temporary filesystem failure, cache destruction/reinitialization and adversarial FP-register clobber in the loader. Log `expanded-boundary-tests.log`.
- Preservation suites: 124 passed, covering RAW lifetime/released RAW, capture lifecycle, controller/root/ADJ, SD install/custom/error atomicity, library state/migration and stamps. `M10V_GR3_ORIGINAL_RTOS` explicitly pointed to the pinned official RTOS, avoiding missing-fixture skips. Log `preservation-regression.log`.
- Exact delivered BIN: 5 passed. Both real reservation sites leave the film snapshot empty; all five appended tones freeze on the real submission prologue; later UI changes cannot retarget them. Original installed Still Make receives the frozen film's native banks even when ShootingInfo still names another carrier, and ShootingInfo bytes remain intact. Also verifies startup/no IO, preview UI initialization and independent auditor rejection of a tampered submission wrapper even with its runtime hash repaired. Log `delivered-bin-tests-final.log`.
- Exact delivered shared HDF: 11 passed. This closes the initial missing-fixture skip, including shared allocation, untouched RAW/color state, native grain coexistence and all HDF strengths. One debug-event-drain test was intentionally not selected because the delivered candidate has debug disabled; no debug-mode device observation is claimed. Log `delivered-hdf-tests.log`.
- Initial full `npm test`: 301 passed, 2 failed, 8 skipped. `original M10V web workflow binds all five slots and timestamp into audited firmware` still expected130 Hooks while the no-HDF design now has129 (two reservation Hooks replaced by one submission Hook); its exact-count assertion was updated with the reason. `CLI rejects invalid configured ports instead of silently picking a random port` hit its5-second process timeout during the heavily parallel run, then passed in isolation (3/3 deployment tests). No server code or timeout was changed.
- A subsequent automatic-discovery run was stopped after it discovered an unrelated `builds/.../source/` mirror and failed on that mirror's absent GR IV sample. The authoritative final run explicitly enumerates every `*.test.mjs` under the active `node/` tree (99 files, including nested adapter/platform tests), with concurrency2. That run completed311 cases:302 passed,1 failed (the same web workflow now reached its second old130-Hook assertion, in the debug export),8 skipped. Both debug-off and debug-on no-HDF exports correctly have129 checked Hooks. The debug assertion was then updated for the same design change and the complete route file was rerun separately; see the final addendum below. No production/native code was changed to resolve these assertions.
- Independent read-only review found no blocking defect; verified stock current/next recipe ordering, pre-mutex placement, ABI/FP preservation and the retained TopMenu ownership route. `git diff --check` passed.

The checked initial BIN is `052142b1d13f8749cccef5503c78232a43dfd7532d27d37695c684500cd76db3`, 32,110,232 bytes, 136 verified Hooks. Its source fingerprints still match current native sources. Repackaging evidence does not change the firmware; the final deliverable is checked again against this identity.

Final addendum: the complete `node/gr3-native-routes.test.mjs` rerun passed2/2, including its normal/debug/version-unlock/configuration-binding exports and separate HDF-zero feature case (`native-routes-final.log`). Together with the active-source full run (302 pass /1 superseded count-assertion failure /8 skip), no unresolved test failure remains. The eight skipped tests require optional Python backup, GR II or legacy GRLife fixtures; they do not cover the changed submission/preview paths. The full99-file suite was not repeated after this test-only assertion update. The final candidate keeps the same native code; the receipt's preview-scope description was corrected to match UI-enter initialization, and final packaging adds current source/tests, validation evidence and license notices.

Candidate status: **WAITING_FOR_USER_VALIDATION**. No main merge, GitHub push, camera installation or Baota deployment is performed. Installation, exact-device steps and rollback are in the accompanying README. LiveView transition timing and sustained shooting still require the user's identified BIN on physical GR III.


## User acceptance and release integration

Status advanced to **USER_VALIDATED** on 2026-10-21 (Asia/Shanghai). User confirmed GR III: “测试通过了，换卷首张和实时取景都正常，合并 main、推送 GitHub 并部署宝塔。” The accepted BIN SHA256 is `052142b1d13f8749cccef5503c78232a43dfd7532d27d37695c684500cd76db3`; ZIP SHA256 is `88542ba3303e594f1d5fb1323a1296a040c6add9ab7503f10853fd9887f60aff`. Acceptance covers the reported first-shot and LiveView faults; it does not certify every effect, A/B operation or other camera model.

Release integration starts from main `a5742282b66516405cfe984b4d0974d1e06ae6f4`. Only candidate-snapshot differences and related regression/acceptance documents are overlaid in an isolated worktree. The approved snapshot includes native A/B comparison/exit dependencies that were absent from that main revision; retain their exact bytes rather than silently changing the approved firmware. Original dirty workspace edits remain untouched. Source/config fingerprints and a byte-identical rebuild must match the accepted candidate before push. Production retains existing deployment resource limits and three-model checks.


Integrated rebuild evidence: the release worktree generated the exact accepted BIN and runtime bytes with136 independently checked Hooks. Logical configuration, extension options, official input hash and native source fingerprint match. The complete integration/config fingerprint differs because current main has newer comments in `node/gr3-native-budget.mjs` (the sole differing integration source outside the approved source snapshot); both versions export exactly `MAX_NATIVE_RTOS_GROWTH=960*1024`. Those current-main comments were retained. This is source-description metadata only, not a changed build option or runtime. Accepted native-source fingerprint: `b624e5ab4574df65c41d7bd4113adb24563a4e02bd72b54a14da1c7ec424a847`; rebuilt integration fingerprint: `786a57c5c71c5d9b576003d933c3b3cf6b09cefcd4c7453fb00a4dd26e531479`; rebuilt plan fingerprint: `62e73e14e86a8414e1730ea07af78f31f3294171d548220e77f97e16485e3306`. This difference does not extend the user's camera validation to other configurations.


Release-stage verification:167 Python/ARM/deployment-control tests passed, including the delivered firmware path, recipe snapshot and FP ABI, original still handoff, Charmera still safety, UI ownership/A-B navigation and bounded deployment/rollback controls. Independent release review rechecked exact BIN/runtime/manifest/config/SD identity and all approved source-snapshot files with no blocking finding. The fresh release worktree initially lacked a local ignored GR IV calibration fixture; it was restored as a regular local file and its pinned provenance test passed2/2. The complete Node suite was restarted after restoring that fixture; no fixture or RAW data enters the commit. The installed server deployment script SHA256 matches origin/main, so no administrator script replacement is required.

Final release-tree Node run: `npm test -- --test-concurrency=4` completed311 cases:301 passed,0 failed,10 optional-fixture skips (`builds/film-timing-release-node-final.log`). Python release checks completed167 cases with0 failures. Changelog validation and `git diff --check` passed. The ignored GR IV fixture remains local and was not staged.

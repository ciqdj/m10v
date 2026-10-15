# Task 1 — native 800T five-control detail integration

## Implementation

- New `native/gr3/m10v_detail.c` uses only the unified `m10v_camera_library_load` / atomic `m10v_camera_library_detail` journal owner. No current-record allocation growth, private tail, legacy M10V8CFG file, tone18 gate, or duplicate persisted state.
- Actual stock detail model byte `0x198` maps tones `[12,18,19,20,21]` to the five library slots. Each resolution checks that slot's validated film ID is33, shooting visibility, original setting/type bounds, and normal detail mode.
- New IDs18–22 mean gain/spread/threshold/grain/soft, with ranges8/8/8/3/3. Stock tone storage never receives them. `m10v_library_menu.c` hides the obsolete profile page and offers only three halation pages; existing separate grain/soft pages remain.
- Four original table consumers resolve dynamically: visibility0x531afa24, count0x531afacc, row0x531affa8, selected item0x531b01f8. The selected-item shim takes its UI fromr4 because r0 already holds the selected index. All three shim variants preserve caller registers, flags, stack, and the stock saved-LR contract.
- Every stock table/list is cloned with its entire prefix intact; the new five rows append only in the dynamically selected800T table. Non800T uses the untouched original table, including separately selected negative-grain extension sites.
- Two exact relocated stock slider constructors preserve original delegate ownership and callback0x531b0fd0. A null allocation guard prevents constructing a delegate at0. Captions reuse the unified resource descriptors; no second global caption interceptor competes with existing extensions.
- Atomic reset passes all five values to the unified backend once, after the original stock reset. A failed callback restores the committed slider value with the original non-notifying stock setter, displays resource824, and returns through the original callback frame without the success redraw that would otherwise overwrite the error caption. Menu log event70 records item, previous value, requested value, slot and persistence result.
- Runtime Python/Node inventories include the new source and root's energy header. Node audits only a fixed set of11 extra stock patches, independently fixed shim opcodes, every cloned stock list prefix/caption, relocated stock slider instructions and null guards. It rejects changed runtime code even when the manifest's runtime hash is recomputed.
- New exact integration rejects GRIIIx native preparation/build/audit; the native catalog advertises only GRIII. Other model import and nonnative functionality is unchanged.

## Lifecycle finding and scope

Disassembly confirms0x531b0fd0 immediately tailcalls the original detail callback0x531b0bac. This implementation persists each actual slider callback, matching the user-approved stock immediate-update behavior. Original confirm0x531b0aa4 and cancel0x531b0aec retain their stock exit routes and do not add another private write or rollback. This is **not** a deferred-confirm transactional UI. Tests execute those stock exits after a successful callback and verify the already committed private state remains. SD/reset failure does not publish a partial five-control state because the root-owned atomic backend performs one journal transaction.

All snapshots embedded in the builder are from exact officialGRIII2.10 bytes and are independently compared to freshly decoded official bytes by the Node auditor. No production build depends on `/tmp` snapshots. The new ARM tests decode the repository's official firmware themselves.

## Verification evidence

1. Initial RED: `python -m unittest tests.test_gr3_native_detail -v` failed specifically because runtime manifest had no `detail` integration.
2. Additional RED exposed failure feedback being erased by the stock redraw; failure-only callback epilogue made the regression pass.
3. Additional RED required GRIIIx preparation to return400; old behavior returned200.
4. Latest focused detail run:14 tests passed. Cases execute real tone-to-kind selection, stock count/selected-item/setup/current/callback/row/confirm/cancel code, all five carrier tones, per-field ranges and values, atomic reset, failure restoration, null allocation, invalid inputs, private profile reachability, and register/flag preservation. Filesystem/hardware services are substituted; these are offline ARM tests.
5. Native Node build/audit test passed, including changed-shim/recomputed-hash and changed-caption rejection.
6. ADJ/redraw regression run:28 total,3 passed and25 skipped because historical decoded user/fixed/diagnostic artifacts are absent. The3 fresh-build ADJ regressions passed, including stale private-mode detail lookup.
7. Full `npm test` was run:182 total,173 passed,3 failed,6 skipped. Failures were:
   - `native RAW NR export independently reads back off and threshold together with old extensions`: a fingerprinted energy source changed during concurrent implementation; rerun on stable final tree required.
   - `original M10V web workflow binds all five slots and timestamp into audited firmware`: expected hook count34; now45. Updated assertions and GRIIIx rejection expectation. Focused rerun pending below.
   - `native 800T uses the same capture chain as texture and timestamp`: old textual assertion expected `m10v_halation(&halo`; root owns replacing this with the new energy implementation contract.

## Remaining validation boundaries

- Root must run the final combined suite on a stable tree and create/read back the delivery artifact with selected extensions.
- The new test harness substitutes journal services to exercise stock lifecycle dispatch; root's independent backend tests provide actual journal/readback/migration semantics. No real SD card or camera was connected.
- LCD reachability, physical key behavior, perceived menu latency, power-cycle persistence and camera JPEG output remain pending real-camera validation. Dynamic list decisions currently read the shared journal through its authoritative backend; no extra menu cache was introduced.
- Save failure in the regular callback retains its error caption. Reset invokes the original caller's remaining lifecycle; any later user navigation/redraw can replace that caption as normal.

Final focused web route rerun on the stable source tree passed (1/1,33seconds), covering normal/debug firmware export, explicit GRIIIx rejection,45 independently verified native hooks, and RAWNR/old-extension composition. `git diff --check` passed before commit.

## Review correction — caption resource IDs

Independent review found the five caption IDs were each one resource too high. Added a RED test decoding actual embedded UTF16 runtime descriptors (it showed Spread/Gate/Profile/Soft/Timestamp), then corrected builder and independent Node expected IDs to `[862,863,864,827,828]`. New decoded captions are exactly Gain/Spread/Gate/Grain/Soft Diffusion. Focused detail suite16/16 and Node native build/audit1/1 pass after correction.

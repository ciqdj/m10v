# Independent camera settings implementation plan

> Execute inline with superpowers:executing-plans; independent read-only firmware investigations use dispatching-parallel-agents.

Goal: two real standalone Chinese camera settings pages, preserving the rebuilt 800T and SD storage.
Architecture: verified stock root registration -> owned page controller -> bounded settings state -> existing validated journal/SD backend. Drawing uses proven native primitives only.
Spec: docs/superpowers/specs/2026-10-16-camera-settings-design.md

- [x] Reverse stock root menu registry, activation, drawing and disposal. Record exact addresses/preimages and executable evidence. Do not ship guessed hooks.
- [x] Add native independent page state and regression tests: five slots, browse/cancel, identity revalidation, write failure, all timestamp fields. No ImageControl model padding dependency.
- [x] Bind verified stock settings entries and owned page drawing/key lifecycle; render horizontal five icons and Chinese footer, timestamp form. Remove SD entry from ImageControl once independent path is verified.
- [x] Test actual ARM registration/callback, original behavior, 800T, SD/JPEG; run build audit and fresh review. Generate matching artifacts only once integration passes.

Review focus: failed allocation; card changed after focus; write failure; invalid/empty catalog; exit/reentry and stock menu ownership. Hardware results cannot be inferred from mocks.

Ledger: baseline d858556. Independent registration and drawing investigations dispatched read-only. Existing timestamp supports all screenshot enumerations; no render-format expansion required. Previous ImageControl-based implementation remains baseline until real settings integration is proved.

Outcome: implementation and offline tests complete; actual LCD/input verification remains outstanding, not inferred from emulation. See docs/testing/gr3-independent-settings-20261016.md for the initial Node failures and successful reruns. Review found no supported P1/P2; removed meaningless base[7] write.

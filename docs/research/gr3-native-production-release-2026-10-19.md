# GR III native production promotion

User accepted the latest camera test and explicitly authorized merging main and publishing GitHub/Baota. Source includes27876bf,4c11ab5,9700593,5dfe3d4. Acceptance refers to this test camera, not all bodies/formats/cards.

## Public export integration

Previously the validated native/live combination required an internal live_color:true option that the web route did not supply. Public GR III film prepare/generate now default to that same native pipeline, independently of debug_mode. Explicit internal live_color:false remains available for isolated legacy comparisons; GR IIIx and HDF-only retain their model routes.

The builder now allows native ownership with logging disabled only when native color, native grain, per-recipe snapshot and the single lifecycle allocator are all enabled. Profiling remains debug-only. Release links the two required diagnostic sink symbols as exact MOV r0,#0;BX LR leaf functions. Independent Node readback verifies those instructions and absence of SD log filenames, rather than merely trusting manifest.debug_mode. No photo buffers, effect parameters or native completion identities are weakened. The header always declares sink APIs for the release-owned pipeline.

Generate uses plan.live_color when invoking the ARM builder and checks the installed snapshot hook against the plan. Public API tests check actual live_view_base.film_color_preview, not only the requested plan name.

## Validation

Production combined HDF BIN:bdac500c27252fcdc3f53a80226ab5287c1275354c5a464bdcfc0763d321293d;100 audited hooks.45 final-BIN native/Live/HDF/readonly-menu/decoder checks pass;1 release no-op sink check passes;5 actual release CPU-bypass/halo/leak/fallback checks pass. Relevant Node plan and actual server export tests, full native public routes, changelog/deploy controls and Python deployment protection are required before pushing. No speedup percentage is inferred from local ARM timing.

Changelog2026.10.19.10 records promotion; previous2026.10.19.9 has source evidence because its Actions deployment failed on SSH timeout. The current release must obtain its own DEPLOY_OK and public health checks before reporting online.

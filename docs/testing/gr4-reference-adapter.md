# GR IV reference adapter verification

The adapter vendors the crop, shutdown, container, history, rollback, build,
version allocator and known update-policy core from `gr-custom-tool` commit
`549591db6ee7809fa7617c3637296ddc79b34f59`.

## Evidence boundary

- Evidence level: `reference_verified`.
- Real GR IV input sample in this repository: none.
- Hardware flash, boot, menu and recovery validation: not tested.
- The first generated build from `1.11.10.7` is `1.11.10.10`; later builds use
  the highest matching local record plus one.
- The optional `allow_older` mode changes only the eight byte-exact comparison
  branches recognized by the reference core. It is not a hardware acceptance
  guarantee.
- The imported original is retained by SHA-256 and can be downloaded unchanged.

## Verification commands

```sh
node scripts/sync_gr4_reference.mjs /Users/zhaoo/Desktop/code/zhaoo/gr-custom-tool
node --test node/adapters/gr4 node/gr4-runtime.test.mjs
(cd vendor/gr4 && TMPDIR=/private/tmp ../../.venv/bin/python -m unittest discover -s tests -p 'test_*.py')
npm test
```

The vendored 114-test reference suite covers codec framing/container checks,
crop registry rules, shutdown asset preparation, the low-version comparison
policy and version allocation. Fixture-dependent native compiler cases remain
explicit skips when no redistributable GR IV firmware fixture is present.

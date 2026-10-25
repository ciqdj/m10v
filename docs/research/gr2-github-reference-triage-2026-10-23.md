# GR II GitHub reference triage — 2026-10-23

User requested faster progress through existing GitHub work. This changes the
research order, not the approved GR II→GR2013 scope or M10V preservation rules.

## Refreshed repositories

- FRAME-GR2: https://github.com/Lyle-xub/FRAME-GR2
  - Inspected checkout384cd8849ff93a69800c4c64886404262524f389, cloned at
    `/tmp/m10v-frame-gr2-reference-20261023`.
  - Current tree has README/docs/SVGs, no firmware implementation source or
    root reuse license. It is a public release/documentation repository, not
    an available source implementation to transplant.
  - Search-index HTML still showed WN3. The actual checkout identifies
    WNX-L1/App1.0.6; use pinned source instead of cached search summaries.
  - Pinned release description:
    https://github.com/Lyle-xub/FRAME-GR2/blob/384cd8849ff93a69800c4c64886404262524f389/docs/firmware/WNX.md
  - Author reports early-loader copy/zero optimization and still-unconfirmed
    occasional extra lens extension. This is a useful target for differential
    analysis, not proof that our loader/capture is verified.
  - Latest published .frm expected SHA256, per author's document:
    c8fb8602b92bc7e4727080b538e6530b45fdf527aeb385a1d41f97a3687dbdbe.
    Download URL:
    https://github.com/Lyle-xub/FRAME-GR2/releases/download/v1.0.6/rg2_v003.frm
    Downloaded `/tmp/m10v-frame-gr2-wnx-l1-reference.frm`:14664108 bytes,
    SHA matches the published digest. It is a research input only.
  - Priority: compare decoded official/released load maps, early startup and
    hook ranges; then use changed ranges to locate parameter/aspect/RAW paths.
    Public feature claims are leads. Do not replace M10V's catalog/slots/state
    with this project's16-slot product, or distribute its binary as our work.

- ricoh-gr2-boot-screen-mod:
  https://github.com/lc2425150/ricoh-gr2-boot-screen-mod
  - Inspected checkoutd99b561620973c29e86c65ea74aa12f777f4edeb, cloned at
    `/tmp/m10v-gr2-boot-reference-20261023`.
  - Has actual Python/web tool source, TTL examples and original-resource/job
    table research. Previously used UNITY facts remain valid reference leads;
    no update to this revision since the earlier inspection.
  - `web-tool/LICENSE` is MIT; no root license was found. Do not assume that
    this grants the same scope to every tools/docs file.
  - Boot gating/job handler/resource addresses can shorten targeted searches.
    Tool still explicitly does not recalculate the update checksum, so it
    does not solve our remaining full-loader handoff/firmware packaging work.
    Claimed SD filecopy parameter order and recovery behavior are unverified.

- grfs: https://github.com/jkbrzt/grfs
  - Public Python/MIT implementation of read-only GR II HTTP photo access.
    Useful when integrating Wi-Fi file access; not a loader or ISP port.

## Execution adjustment

1. Prioritize published GR II firmware diff and source-derived target maps
   before further blind disassembly. Check input identities and preserve a
   separate provenance record for third-party artifacts.
2. For each remaining feature, inspect existing source/reference coverage
   first, then validate the relevant original instructions on our exact GR II
   official sample. Do not redo established container/checksum/allocator facts.
3. Run affected verification during research; reserve the full GR II suite for
   native integration milestones.213 tests/614s is the latest full checkpoint
   (031235e); repeated full runs per small read-only probe are unnecessary.
4. Retain all existing M10V functionality. A reference implementation is an
   acceleration aid, not a replacement specification or hardware acceptance.

No external scripts/apps/firmware were executed or installed on a camera.
GitHub API discovery hit an unauthenticated rate limit; normal git clones
succeeded. Release download throughput was low, so the initial transfer is
bounded and must be resumed/verified before binary comparison is reported.

## First reproducible binary comparison

`node scripts/compare_gr2_reference.mjs bin/rg2_v003.frm /tmp/m10v-frame-gr2-wnx-l1-reference.frm data/research/gr2/implementation/frame-wnx-l1-diff.json`

The reference executable is6762496 bytes (official6132308), and its update
checksum verifies as2385570292 with all four verification flags enabled.
Same logical records/destinations have915 changed bytes in246 runs; this count
excludes appended/moved payload. Early entry remainsA0020400.

Record0 grows fromA46C4 toEB638 bytes. Its staging tail overlaps record1 by
290360 bytes. The first comparator rejected that overlap; a regression fixture
now requires reporting stage overlaps separately and comparing identical logical
records, rather than silently mapping the staging tail as record1's final code.
This does NOT relax M10V's production load-map/ownership checks.

The early ARM instruction atA00206C8 branches toA00C4C00 instead of loadingr0.
The staged loader has21 copy/zero descriptors atA00C4D00..A00C4DFC. Data decoding
(not executing its loader/code) resolves the sparse destinations and SHA of each
output. Its copied groups includeA0798000/C000, A0804000/5A000 and small gaps
between original modules. Record14 moves toA07A4000 and grows to53EC8 bytes.
The heap literal changes toA085E000. Boot order, cache and final ownership still
need original-path analysis; these values cannot be pasted into M10V.

Selected reference hook locations/targets (Thumb bit retained) give focused
next targets, rather than another full-image disassembly:

|Original entry|Reference target|Research relevance|
|---|---|---|
|A00E1158|A085D625|Indexed effect property reads|
|A03A0378|A0842789|Indexed UI property writes|
|A013B4F0|A079ED0D|ISP engine boundary|
|A03AD0C6|A079F301|Original effect-page controller|
|A03A4AD0|A07FF871|Original text lookup|
|A0398F20|A081A04D|Original draw dispatcher|

The indexed property reader/writer branches check bases2E/46/5E/76/8E/A6/BE/D6.
These are leads for finding the original numeric parameter contracts, not
permission to transplant the reference's storage or menu semantics. Our original
23-control getter/setter probe independently passes at explicit property I/O
boundaries. Four comparator behavior tests plus existing container/checksum
checks pass together (8 tests in4.160s); no full firmware suite was repeated for
this read-only analyzer. No third-party code or camera installation was executed.

## Original property-array follow-up

The reference's indexed-property hook led to original metadataA00DD8AC and
indexed getterA00E1158→A00E10B0. A new original-code probe supplies a no-alias,
no-observer scalar property bank and executes all24 indices of all8 groups,
including signed32-bit patterns. Each group has width4/count24, reads exactly
scalar property(base+index), and index24 returns80000001 without reading the
scalar bank. No original function effects are substituted. Test passes in1.480s
(`/tmp/gr2-effect-arrays-green.log`); this is an ABI proof, not saved defaults.

Official numeric descriptors/text lookup distinguish the group captions:
2E Saturation(text129),46 Contrast(130),5E Sharpness(132),76 Vignetting(134),
8E Hue(145),A6 Toning Effect(138),BE Clarity(133),D6 Brilliance(158).
In particular, do not labelBE high/low key orD6 Clarity by analogy withGR III.
Numeric descriptor examples: A043A8E0 (Saturation/property2E/tone2), A043B970
(Clarity/BE/tone16), A043BA30 (Brilliance/D6/tone17). These static field/name
facts guide further range/default analysis; GR III's additional high/low-key
and separate highlight/shadow controls are not yet implemented or proven
unavailable onGR II.

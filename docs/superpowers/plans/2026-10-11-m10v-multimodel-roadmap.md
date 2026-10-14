# m10v Multi-Model Firmware Platform Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver one local firmware editor that supports GR III and GR IV through isolated model adapters and leaves an evidence-empty GR II extension point.

**Architecture:** A loopback Node service owns security, projects, storage and the web application. Model adapters implement one versioned protocol; GR III remains native Node, while GR IV runs the tested Python 3.12 reference core behind a JSON bridge. Four phase plans produce independently testable increments.

**Tech Stack:** Node.js 20 ESM, browser HTML/CSS/JavaScript, CPython 3.12, Pillow 12.3.0, Unicorn 2.1.4, ARM LLVM/LLD.

**Spec:** `docs/superpowers/specs/2026-10-11-m10v-multi-camera-firmware-platform-design.md`

## Global Constraints

- GR III output preserves all input version fields; GR IV uses the reference `.7` to `.10+` allocation policy.
- Never share firmware offsets, instruction bytes, version logic or checksum rules across adapters.
- GR IV without a user sample is `reference_verified`, never sample- or hardware-verified.
- GR II contains no guessed firmware facts and cannot build.
- Candidate generation never writes a camera or SD card.
- Filters are outside scope.
- Existing official-package backup remains honest about computer-only recovery.
- The parent repository is heavily dirty. Do not run `git add .`, commit, branch or push during execution. At each phase record scoped paths and a proposed Conventional Commit; execute Git commands only after the user selects a publication mode and confirms the exact commands.

## Execution Order

1. [Multi-model foundation](2026-10-11-m10v-multimodel-foundation.md)
2. [GR IV reference adapter](2026-10-11-m10v-gr4-reference-adapter.md)
3. [GR III editable firmware adapter](2026-10-11-m10v-gr3-editable-adapter.md)
4. [Cross-model product integration](2026-10-11-m10v-multimodel-product-integration.md)

Each phase starts only after the previous phase's full suite is green and its interface review is clean. A later phase may not weaken an earlier adapter's verifier to make a fixture pass.

## Whole-Program Completion Gate

- Run `npm test` in `m10v` with zero failures.
- Run `PYTHONPATH=. /opt/homebrew/bin/python3.12 -m unittest -v` in `m10v` with zero failures.
- Run the vendored GR IV reference suite with Python 3.12; sample-dependent skips must be named and must not be reported as passes.
- Run both GR III evidence scripts against `fwdc239b.bin` and preserve exact source SHA-256 `d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4`.
- Run JavaScript syntax checks for every edited ESM/browser file.
- Render and operate import, project edit, build, history, backup and download flows at narrow and desktop widths.
- Verify no failed or unverified candidate is downloadable and no candidate enters the official-package backup.
- Update README, usage guide, GPL notices and third-party provenance to match the shipped behavior.

## Publication Checkpoint

After all four plans are complete, present the repository-mandated publication menu. Any commit must use explicit `m10v/...` paths rather than broad staging.


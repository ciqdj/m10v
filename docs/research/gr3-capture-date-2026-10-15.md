# GR III capture date and isolated stamp failure

Official GR III 2.10 decoded RTOS SHA256: `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`.

## Official date layout

The existing capture topology supplies the shooting metadata pointer at `context+0x34`, also checked against `recipe+0x44c8`. The compiled GRLife capture implementation independently reads its date through the same pointer. The following official code proves the field meanings, without inventing an RTC address:

- `0x534322d8` receives metadata in `r2`. `0x53432338` calls `0x536bd838`, loads its result's `+4` pointer, and calls `0x536b6510` to fill an official date structure.
- `0x5343235c` stores the year at metadata `+0x944`; `0x53432360/64` store month/day at `+0x946/947`.
- `0x53432368` calls `0x536b5f40` to calculate weekday and `0x53432378` stores it at `+0x948`.
- `0x5343237c/80/84` store hour/minute/second at `+0x949/94a/94b`.
- Another official producer, `0x534fa22c`, performs the same writes through `[object+0x5a0]` at `0x534fa298..0x534fa2ec`.
- Official consumer `0x5359c010..0x5359c078` reads these date/time fields and reconstructs the official date via `0x536b5ec4`.

The adapter now prefers this per-capture date. The metadata address and protected overlap extent are checked through `0x94c`. It validates Gregorian calendar dates including leap years, hours, minutes, and seconds. When capture metadata is invalid, it tries the existing UI getter at `0x532b36cc`. A failed or invalid fallback disables only the stamp in a stack copy and recomputes that copy's state CRC. Persistent configuration is untouched. The grain seed always has the existing `state.sequence ^ Y-plane-address` base; valid dates mix in the original date fields, but date failure cannot abort grain or the shared render path.

Debug event `120` (`capture.clock`) fields are: `a=context`, `b=status`, `c=requested stamp mode`, `d=source address`. Status `4` means capture date (`d=shooting+0x944`); `1` means UI date; `2` means UI unavailable; `3` means UI date invalid. For statuses 1–3, `d` is the UI service pointer. Status 2 or 3 is followed by normal render events 110/111, rather than capture return -7.

## ARM regression boundary

`tests/test_gr3_m10v_capture.py` now loads the official getter, property accessor, date-copy, weekday conversion, and capture-date producer instructions directly from the official firmware. The producer's runtime clock provider is substituted with a controlled date; the UI getter itself is not mocked. Assertions and external allocation/filesystem/cache services remain test boundaries.

Regression tests first failed with the original -7/-1 exits for unready/invalid UI dates. The capture-metadata test first failed because the adapter reported unavailable UI date despite valid officially produced metadata. It now verifies 800T + grain + soft + stamp pixels against the native renderer with a 2024-02-29 capture date, both when UI date is unavailable and when it differs. Tests also check persisted stamp settings remain unchanged and unavailable dates do not suppress halation or texture pixels. Debug builds assert clock status and that render events follow.

This proves compiled ARM behavior and the official field ABI, not actual device clock initialization, JPEG encoding, or camera stability. Camera testing must check visible timestamp and event 120 source status on real captures.

## Final integrated firmware regression

The capture suite can execute the relocated runtime extracted from the actual final firmware, instead of compiling its own runtime:

```sh
M10V_CAPTURE_BIN=builds/gr3-integrated-device-test/fw/fwdc239b.bin \
  .venv/bin/python -m unittest tests.test_gr3_m10v_capture
```

It decodes the candidate, extracts the runtime using `evidence/M10V-runtime-manifest.json` beside the candidate's `fw` directory, and requires its SHA256 to match the manifest. Override the manifest location with `M10V_CAPTURE_MANIFEST` if necessary. Diagnostic cases require a debug-enabled candidate. External allocation/cache/filesystem/log-output boundaries remain substituted; capture date selection and image effects run from the final candidate's bytes at their final addresses.

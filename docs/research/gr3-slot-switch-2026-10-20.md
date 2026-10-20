# Configured-slot switch: frame SI lags committed selection

User reproduction: switch between two already configured film slots. The old
implementation selected both Live colour and the first still's slot from cached
ShootingInfo tone at +0x77c. Original Live Make reads the same stale frame metadata;
repeating the setter is not supported by evidence (the original setter has no
same-tone early return).

The stock active-tone getter is 0x532bd6b4 -> singleton 0x53525d5c -> 0x53549ee8
-> 0x5355155c. The singleton guard is 0x553458ac and pointer 0x553458b0; constructor
0x53543198 installs vptr 0x53d1a528 and the config wrapper at backend+0x518.
The wrapper retains two buffers; 0x5355198c swaps the committed pointer. This
module borrows the committed tone with guard/vptr/address checks and a bounded
pointer recheck, without initializing the singleton, taking locks, mutating SI,
performing filesystem I/O, or retaining backend pointers. A detected transition
or unavailable backend falls back to frame SI. It is a best-effort read, not a
cross-thread transaction or a hardware timing guarantee.

Live uses that current tone to select the preview cache's slot. Still ingress
freezes the selected tone once in its own recipe, alongside the existing library
snapshot. A later UI switch cannot retarget a queued photo. The original raw SI
and tone remain the completion identity; native colour, native grain and CPU
fallback derive their slot from the frozen selection. `tone`/`selected_tone` share
the original four-byte header word; total size and subsequent offsets remain
unchanged. The factory still initializes the entire recipe extension.

Only carrier frames (12,18,19,20,21) receive an override: the stock base patch
neutralizes only those frames. Other ImageControl frames retain their original
routing even if the UI is newer. This fix addresses switching configured slots,
not a promise of frame-zero behaviour when entering custom films from stock.
GR IIIx shares the still path; real-time custom colour remains GR III only.

`tests.test_gr3_slot_switch` executes original stage-1 Live Make and packers with
five distinct films. It covers a complete slot cycle, invalid backend tone fallback,
first still ownership, a later UI switch, producer re-entry, wrong raw-tone completion
rejection, unmodified SI, and actual CPU fallback when native colour did not run.
Stage-0 device backend services and ISP pixels are not emulated. Existing recipe,
grain, Live, RAW topology and firmware composition tests cover adjacent contracts.
Physical GR III / GR IIIx switching, LCD timing and JPEG output still need camera
validation; ARM parameter-bank equality is not a device-quality measurement.

Release verification (2026.10.20.2): 79 scoped Python/ARM checks passed, plus the
final three-test distinct-slot suite including CPU fallback. Full Node run had
279 passed, four skipped and two source-fingerprint failures caused by concurrent
native edits; the affected composition/HDF files plus changelog were rerun after
source freeze: eight tests passed, including debug/release extension combinations.
GR III and GR IIIx release candidates independently built and read back. No
physical camera was connected or flashed.

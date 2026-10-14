# Exact GR III 2.10 JPEG capture contract

Baseline RTOS SHA256 8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67, decoded VA 0x53000000, /tmp/m10v-800t-analysis/rtos.bin. Original investigation plus the 2026-10-13 adapter correction. Original ARM execution is evidence; hardware calls remain untested in the revised candidate.

## Concrete config creator

`JpegEncodeMacroProcessConfig` vptr is **0x53d0fbe0**, RTTI 0x53d0fa10, name 0x53d0fa1c. Constructor loads vptr literal 0x5350fde0 at 0x5350f548 and stores it at recipe+0x9b8 at 0x5350f5ec. The earlier speculation that this was recipe+af8 is wrong (that is a different config).

Recipe setup dispatcher 0x5350e624, case6 0x5350ea50 builds the actual config. It first calls 0x536a3d84 to copy the low descriptor recipe+70 to recipe+110. Let R=recipe and C=R+9b8:

| C field | value set | instruction VA |
|---|---|---|
| +30 | R+1a8 (common config/status object) |5350ea84|
| +34 | *(R+44c8), ShootingInfo |5350ea7c|
| +38 | *(R+5c), BeStillRequestConfig |5350ea74|
| +3c | R+b0 main JPEG YCbCr descriptor |5350ea8c|
| +40 | R+d0 secondary descriptor |5350ea94|
| +44 | R+f0 secondary descriptor |5350ea9c|
| +48 | R+110 copied source descriptor |5350eaa4|
| +4c | R+130 encoded output control |5350eaa8|
| +50 | R+148 encoded output control |5350eaac|
| +54 | R+160 encoded output control |5350eab0|
| +58 | R+178 encoded output control |5350eab4|

Only setup case6 populates these fields among ordinary aligned ARM instructions found in recipe code. This is a concrete creator/consumer chain, not type-name inference. It does not rule out dynamic writes, Thumb code or other recipe classes elsewhere.

## Exact independent JPEG/RAW encoding split

0x535047d4 gets C from message r1+8 into r4. Its hook 0x535048e8 precedes sending message opcode 0xc0000003 to JpegCodecPipeService. The stack parameter (fp-5c) is:

```
+00..0c src[4] = {C->3c, C->40, C->44, C->48}
+10..1c out[4] = {C->4c, C->50, C->54, C->58}
+20 enabled main = request->c
+21 enabled secondary1 = 1
+22 enabled secondary2 = 1
+23 enabled extra = request->d
+25 policy = request->d
```

Service vtable 0x53d53e90.. has handler0x53663ec8 (the +8-adjusting thunk 0x53664664). Handler branches opcode3 at0x53663f08 ->0x53663f68. It loads all src/output pointers. At0x53663fb4 it tests enable+20; nonzero takes0x53664394 and calls encode0x53663ba4 with src0/out0 at0x536643ac. At0x53663fdc it tests enable+23; nonzero takes0x5366437c and calls0x53663ba4 with src3/out3 at0x5366438c. Separate descriptors do not prove distinct physical backing.

The latter extra JPEG is consistent with the observed full-size DNG JPEG preview, but the exact container-storage label is not proved merely by this codec service; do not claim the service itself writes DNG. The captured DNG's full-size preview and CFA are different sample entities.

## Request flags proven by creator and RAW consumer

BeStillRequestConfig constructor0x53512adc uses vptr0x53d0fe60 and allocates0x3c bytes at0x5350fc48. Its named SetupRecordImageFormat function is0x53513284, debug string0x53d0fe70. It reads ShootingInfo+0x7b5 and creates flags:

* 0 -> request+c=1, request+d=0 at53513388..53513398
* 1 -> request+c=0, request+d=1 at5351339c..535133a8
* 2 -> both1 at5351336c..53513378

Subsequent shooting/scenario conditions can override these flags. Therefore the runtime flags are preferable to assuming the input enum alone.

RAW config vptr0x53d0fc30/RTTI0x53c62d80 `26RawCodecMacroProcessConfig`; config R+a50 is configured from the same status, ShootingInfo and request. RawCodecMacroProcess handler0x53506de0 gets it from message+8. At0x53506e68 it loads cfg+38; at0x53506e6c loads request+d;0x53506e74 returns if0; otherwise0x53506e80 calls raw encode0x5350680c. This proves +d gates RAW encoding independently of +c main-JPEG encoding.

RAW source cfg+4 is R->60 (setup0x5350e888..5350e894). Raw encode reads cfg+4 at0x53506894. Raw module handler sets its dimensions pointer from cfg+30->88 at0x53506e20..53506e34. Raw encode reads its first two u16 at0x5350682c/34 and calculates their product*2 at0x53506844/50. Use that as the raw input interval for an enforceable runtime nonoverlap check; this proves the declared encoder input extent, not arbitrary hidden hardware prefetch outside that extent.

## What +4c+10 means

C+4c points to encoded-output control, **not** a low YCbCr descriptor. 0x53663af4 reads out+10 as a byte and passes it through the JPEG hardware request block (stack fp-32 at0x53663b30). It is initialized1 with other output-control objects in the recipe constructor (5350f364 etc). It is a coding parameter; its exact named enum remains unproved. Checking it==1 selects one configuration, but neither proves exclusive buffer ownership nor JPEG-only capture mode.

## Runtime contract the adapter can actually enforce

Fail closed before dereferencing invalid pointers (RAM bounds/alignment/range-overflow checks required):

1. At this exact hook, retain original registers and flags; read C from saved r4. Require C vptr0x53d0fbe0. Derive R=C-9b8 and require C+30==R+1a8, C+34==*(R+44c8), C+38==*(R+5c), C+3c==R+b0, C+48==R+110, C+4c==R+130. Require request vptr0x53d0fe60 and request+c==1. This restricts mutation to the proven main-JPEG source for this still recipe.
2. Require intended ShootingInfo tone at+77c (pre-existing upstream anchor; not freshly re-proven here). Restrict low descriptor format1, third address0, width6000/height4000 (or explicitly accepted dimensions), stride>=width, allocatedHeight>=height, origin offsets0, aligned Y/chroma, independently valid and nonoverlapping plane intervals. Do not require chroma==Y+stride*allocatedHeight: the stock allocator leaves a gap. Read addressMode at +1c as a byte; +1d..1f are padding. Check each stride*allocatedHeight capacity and RAM extent.
3. To support RAW+JPEG while blocking CFA writes, require the two proposed write intervals entirely disjoint from raw input [*(R+60), +2*rawDim0*rawDim1], where rawDims=*(C->30+88). Use the currently valid recipe source and status dimensions directly. Do not require R+a54 or R+a80: constructor zeroes these, and RAW Setup7 populates them after JPEG Setup6 in the supported planner. Check all arithmetic safely.
4. If the desired contract also preserves DNG previews, require nonoverlap from both backing intervals of descriptor C+48. The descriptor object differs, but its backing may alias. If this fails, skip; do not claim preview isolation from distinct descriptor addresses alone.
5. Most conservative limited mode: additionally require request+d==0, admitting current JPEG-record requests only. This deliberately skips RAW+JPEG/RAW-only; it is a support restriction, not evidence that all stock buffers are disjoint.
6. Perform writes synchronously before original send, retain no pixel pointers after return, clean+invalidate actual modified ranges then tailcall original. Original service only starts this main encode after send. The static chain does not exclude other earlier hardware readers (quick-view/direct-view) or prove the producer cache state; those remain hardware/integration concerns.

## Lifetime and unproved claims

The stock function retains descriptors on its stack across send and waits on its event after return at0x53504944. Service returns callbacks on the original object. The hook is before enqueue/dispatch, so the new adapter may finish its work before this encode begins; it must not retain these pointers beyond the call. This establishes local temporal ordering for this encoding transaction, not exclusive global ownership.

Unproved: complete lifetime/reference-counting of all backing allocations; physical aliasing under every recipe, crop, RAW development and shooting mode; other hardware readers before send; exact enum for output-control+10; guarantee every service extra JPEG corresponds to DNG; exhaustive configuration writers/callers (aligned ARM scan is not whole-program proof); cache/hardware timing on real camera. A runtime bounds/nonoverlap gate can make alias rejection concrete even when universal static non-alias proof is unavailable.

## Follow-up: local producer, wait barrier and lifetime

This supersedes the earlier uncertainty about the local producer transaction, and the preview-preservation guard is optional: the approved effect contract permits DNG developed previews to acquire the same effect while CFA/interpretation metadata must remain untouched.

### Producer and normal alias

BackResizeMacroProcess vptr0x53c62618, RTTI0x53c62678, name0x53c62684. Its module handler0x534ff4ac calls0x534fea68 to decode its message action, then tailcalls0x534ff294. Its config B=R+904 is configured by5350e6a4..6ec: B+3c=R+70 (developed source), B+40=R+b0 (main JPEG source), B+44=R+90, B+48=R+d0, B+4c=R+f0.

The prior Develop stage (module4, handler0x53501c38) reads its output-Y/chroma from its config+18/+1c at53501f04/53501f10. Recipe config0x5350eb10 loads R+74/R+78 at5350eb84/eb8c and stores them into Develop config+18/+1c at5350ebc8/ebcc. These are exactly descriptor R+70's first two backing pointers.

BackResize first copies R+70 into module scratch descriptor module+8a48 via0x534fec98/0x534fecb4.0x534fecf0/0x534fecfc read copied Y/chroma;0x534fed10..2c apply common crop offsets. The ordinary0x534fed34 branch writes those pointers into destination R+b0 at0x534fee18/0x534fee20. Thus **ordinary main-JPEG and extra-JPEG developed source buffers alias**, possibly with a crop offset. They are not two independent full image allocations. A separate branch0x534fedd0/0x534fedd4 can select a supplied buffer and needs its own runtime geometry/extent acceptance.

BackResize processing dispatch0x534febc0 sends its hardware work;0x534fec24 waits for its completion event,0x534fec30 clears that event.0x534ff44c calls this synchronized hardware routine before returning to the generic module dispatcher. This is a concrete local processing-completion boundary.

### Module completion and scheduler wait

Recipe mode is R+18; sequence pointer R+1c.0x5350f070 invokes planner0x53512a38;0x5350f074 stores its sequence,0x5350f078 stores mode.

Scheduler0x5351fc6c reads sequence kind and module ID from R+1c/R+14. For kind1,0x535200f8 invokes dispatch0x5351ea9c.0x5351eb74 sets up config;0x5351eb90 gets config;0x5351eb94 stores it in module message+8;0x5351ebec sends that message.0x53520090 advances the sequence index to the following kind10 waiting entry. Kind10 recognition0x5351ff38 leads to0x5351ff18 removing the recipe from the active queue rather than dispatching its next module.

Generic module receiver0x53505c8c invokes concrete process handler through vtable+20 at0x53505d78. After that handler returns,0x53505e28 invokes the owner's return-config callback. BEStillImageProcess callback thunk0x5351f8e8 adjusts this-2c and enters0x5351f420.0x5351f560 calls0x5351ad30; completion records R+20+module at0x5351adcc where applicable, then0x5351adf0 reactivates the recipe via0x53522754 (parallel branch uses0x5351adbc). Owner completion is therefore after the producer's hardware-event wait, and the waiting recipe cannot start the next consumer through this scheduler before that completion.

### Executed planner evidence and supported local modes

`planner-probe.py` now accepts `--rtos` and `--output`, rejects a different baseline hash, executes the original ARM planner for all15 input modes, intercepts only assertion logging, and checks the producer/JPEG/wait/cleanup order for the restricted set **0,1,5,6,7,8,12**. Each original planner invocation reached the return sentinel; no instruction-budget timeout was accepted.

| recipe mode | BackResize index | JPEG index |
|---|---:|---:|
|0|32|35|
|1|28|30|
|5|28|31|
|6|32|35|
|7|11|13|
|8|11|13|
|12|17|19|

Every listed mode has kind10 directly after producer module5, kind10 directly after JPEG module6, and cleanup kind3 for module5/module6 later than the JPEG wait. The live sequence index can already refer to the waiting entry by the time the worker runs; do not insist that R+14 equals the JPEG dispatch index at the hook. Reject other modes for this restricted experimental adapter. The numbers are firmware recipe modes, not camera UI/file-format enum names; this report does not invent their named shooting-mode equivalents.

Reproduce:

```
.venv/bin/python builds/gr3-800t-reverse/capture/planner-probe.py \
  --rtos /tmp/m10v-800t-analysis/rtos.bin \
  --output builds/gr3-800t-reverse/capture/planner-probe.json
```

The planner's own setup and append routines execute; ISP/IIP/JPEG hardware and real callback delivery do not. Scheduler/event/lifetime claims above are static byte-chain observations, not simulated hardware verification.

### Sufficient experimental local contract

With exact recipe topology and restricted mode set, current descriptor/allocated extent validity, CFA input nonoverlap, scratch/metadata nonoverlap, synchronous adapter execution before original JPEG send, and stock cache maintenance after CPU writes, the local contract is closed: the relevant producer has finished its processing transaction; the upcoming JPEG consumer sees the adapter's synchronous modifications; this recipe's subsequent cleanup comes after JPEG completion. No pointers may survive the adapter call. Main/extra developed preview aliasing is intentionally allowed and recorded separately. Global concurrency/hardware cache correctness still requires real-camera validation.

## 2026-10-13 allocation and phase correction

The user flashed the first candidate successfully but reported no halation with RAW+JPEG, selected800T and highlights. Replaying the original constructor RAW-zero stores and JPEG Setup6 exposes the obsolete RAW-config gate. This does not require changing the effect strength.

`scripts/analyze_gr3_800t_capture_allocation.py` executes stock descriptor constructor and allocation instructions at 0x5350db3c. The helper 0x536a2f10 alone is stubbed to 160×120; allocations are inspected as addresses without pretending to execute hardware. For 6000×4000, stride6016, plane capacity is 24064000 bytes and separation24930368, leaving gap866368; 2992×2000, stride3008 has gap433216. BackResize preserves the padded plane pointers in its ordinary path. Descriptor +1c is set by strb at 0x5350f224/0x5350f290 and copied by ldrb/strb; dirty padding must not reject valid addressMode2.

The revised adapter checks each plane separately against CFA and metadata, checks scratch against both planes, and performs cache maintenance separately on actual touched spans. Native entry moved to 0x540bb6b8; 1652-byte adapter ends0x540bb6b4, core2376 ends0x540bc000 exclusive, within the original extension page. Regression cases combine real pre-JPEG RAW state, padded planes, preview alias and dirty enum padding. Real camera cache behavior and visible halation still require retesting.

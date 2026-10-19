# Actual stock pool release boundary

Locked GR III 2.10 RTOS SHA256 is `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`.

The existing recipe release diagnostic189 observes the outer `53521d14` helper returning, including branches which never free a backing. The new optional hook observes the distinct stock call `53521e14 -> 536a248c` returning. At its continuation `53521e18`, original callee-saved registers still contain recipe r4, buffer ID r5, and backing r6; r0 is the pool dispatch return. The original instruction is `str r5,[sp,#8]`.

`536a248c` obtains pools E and F through `536abf18`. It tests backing membership via pool vtable+18, then tail-dispatches the matching pool's vtable+c. Null and unrecognized backing branches assert and return zero. Consequently a zero result alone cannot prove successful release, physical reuse, or SD completion. The event is intentionally named `pool_dispatch_return`, not release success.

`build_gr3_pool_release_trace.build(out,base,mark,rtos=None)` assembles a separate appendRX module, rejects wrong SHA/address/instruction/allocated writable data, and returns a one-patch manifest. The hook branches from53521e18, pushes registers/flags on its own transient stack, calls the existing bounded recipe-owned mark API, restores all registers/flags and SP, executes the displaced store, and branches to53521e1c. The stock pool call executes unmodified with its exact original SP and arguments. There are no file operations, backing dereferences, frees, waits, owner globals, or forced clear operations in the hook.

Integration requires the existing expanded recipe allocation and `m10v_save_trace_recipe_mark` export. Event184 is `(recipe,buffer_id,backing,pool_dispatch_return)`. Like other trace marks, it can be dropped when the bounded owner trace is full/busy. Existing worker drains remain responsible for moving records to their established logging sink. This module does not add an automatic global drain or imply callback filesystem safety.

Linked ARM validation (`.venv/bin/python -m unittest tests.test_gr3_pool_release_trace -v`) passes: exact mark arguments including fifth stack argument, caller/result GPR and LR preservation under clobbering mark stub, NZCV preservation, SP restoration, displaced store, and checked stock instruction. This is CPU/ABI validation, not a hardware capture result.

The promising `DevelopFileProcessError` lead was inspected: call53524244 targets5369be28, a four-instruction status reset (`[r0+9]=0`, `[r0+c]=0`). Its other caller53694e44 also clears error/event status. It is neither a file writer nor backing release; no save-success hook was placed there. Actual BE file-completion event ownership, correlation to the source recipe, and successful SD output remain unknown. The older WriteStillFile hook has no events in the supplied hardware logs and cannot be treated as covering the capture path.

## Further actual BE file-path evidence

The BE manager callback is53694874, with `(manager,opcode,payload)`; the entry saves manager r4 and payload r5. Opcode41000 branches536950e4. It reads the request's frame slot from manager+1214, calls53694490 to consume status byte payload+4 and error word payload+8, updates the corresponding manager+slot*3c+7c status bit08000000, and signals08000000 for statuses<=2 or10000000 for status3.53694490 treats status0 as success and status1/nonzero as errors, except manager+11d9 can suppress errors. These are stock semantics, not media durability guarantees.

Frame slot stores to manager+1214 occur53697858 and536978ec in function53697658. Its sole direct caller is5350b380 in virtual function5350b2fc. That outer function's original r1 is retained in r5; it constructs a stack descriptor at fp-4c from context fields+3c,+71,+80,+82 and calls53697658(manager,descriptor,0). The inner function dispatches the service at manager+9a0 virtual+1c, waits08000000, issues a second metadata request, waits18000000, closes via manager+998 virtual+24, and checks mask4. Error strings are `OPEN ERROR`53d5902c, `META DATA ERROR`53d59044, and `CLOSE ERROR`53d59064. Descriptor byte+10 receives2/4/6 on those respective failure paths and0 on success. Its boolean-like function result is distinct from that stage status byte.

This proves a much stronger file-stage observation boundary than the inactive534e WriteStillFile hook, but not its mapping to BEStillRecipe:5350b2fc has no aligned direct callers and its retained r1 context has not been proven to be a recipe or to contain one. Installing a mark hook using that value as a recipe would be unsafe. No such speculative hook is implemented.

## Retirement drain gap

The current lifecycle consumer drains only at phases190,192,193. Phases191 and194 return without draining. A pool release after the last192 therefore appends184 to a recipe-owned trace with **no guaranteed later consumer**. Recipe retirement can discard it. The optional hook must not be represented as durable release evidence until a proven deferred owner and later safe flush boundary are connected. This update adds no filesystem operation in pool release or destructor. Moving records into an unowned heap block, guessed manager slot, or shared appendRX global would create an unresolved lifetime/ownership problem rather than guarantee delivery.

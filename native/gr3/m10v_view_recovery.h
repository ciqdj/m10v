#ifndef M10V_VIEW_RECOVERY_H
#define M10V_VIEW_RECOVERY_H
#include <stdint.h>
#define M10V_VIEW_SNAPSHOT_MAGIC 0x37575653u
#define M10V_VIEW_MODEL 0x55067958u
#define M10V_VIEW_FACTORY 0x55063914u
#define M10V_VIEW_MODEL_VPTR 0x53b4e7b0u
#define M10V_VIEW_QUICK_VPTR 0x53b41380u
/* These attestations must come from real owning-thread/native-completion
 * boundaries. Store handler return alone supplies NONE of them. */
#define M10V_VIEW_UI_THREAD 1u
#define M10V_VIEW_OWNER_COMPLETE 2u
#define M10V_VIEW_SAVE_COMPLETE 4u
#define M10V_VIEW_QUICK_INACTIVE 8u
#define M10V_VIEW_NORMAL_STILL 16u
#define M10V_VIEW_REQUIRED 31u
#define M10V_VIEW_OBSERVE 0u
#define M10V_VIEW_CAN_REQUEST 1u
#define M10V_VIEW_ALREADY_RUNNING 2u
#define M10V_VIEW_REQUEST_ACCEPTED 3u /* never means visible/complete */
#define M10V_VIEW_REQUEST_REJECTED 4u
#define M10V_VIEW_TRACE_CAPACITY 16u
/* Scalar copies only; no retained external pointer. */
typedef struct {
 uint32_t magic,model,model_vptr,quick,quick_vptr;
 uint32_t actual,pending,inflight,shooting2f,shooting30,shooting31;
 uint32_t quick_state,timer_review,timer_wait,quick_flags;
} m10v_view_snapshot;
typedef uint32_t (*m10v_view_read_fn)(void *,uint32_t,uint32_t);
typedef uint32_t (*m10v_view_start_fn)(void *,uint32_t,const uint32_t *);
/* Reader arguments are context, address, byte width (1 or 4). This interface
 * allows bounded ROM/host fixtures. A caller must serialize on the UI thread
 * for coherent state. No original lazy-initializing accessor is called. */
uint32_t m10v_view_snapshot_read(m10v_view_snapshot *,m10v_view_read_fn,void *);
uint32_t m10v_view_snapshot_camera(m10v_view_snapshot *);
uint32_t m10v_view_recovery_decide(const m10v_view_snapshot *,uint32_t);
/* Re-reads current state immediately before entry. start==0 calls the actual
 * original StartLiveView(0x5323830c). Its function object is empty and lives
 * through the synchronous call. Caller must be on the model-owning UI thread.
 * Do not invoke from Store/BE worker; there it is snapshot/data-only. */
uint32_t m10v_view_recovery_request(m10v_view_snapshot *,uint32_t,m10v_view_read_fn,void *,m10v_view_start_fn,void *);
typedef struct { uint32_t boundary,time,payload; m10v_view_snapshot state; } m10v_view_record;
typedef struct { uint32_t count,dropped; m10v_view_record records[M10V_VIEW_TRACE_CAPACITY]; } m10v_view_trace;
/* Caller-owned, single-writer boundary collector. No FS, lock, allocation,
 * global mutable state, buffer ownership change, or UI control mutation. */
uint32_t m10v_view_trace_append(m10v_view_trace *,uint32_t,uint32_t,uint32_t,const m10v_view_snapshot *);
#endif

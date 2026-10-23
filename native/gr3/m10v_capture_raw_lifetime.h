#ifndef M10V_CAPTURE_RAW_LIFETIME_H
#define M10V_CAPTURE_RAW_LIFETIME_H
#include <stdint.h>
#define M10V_CAPTURE_RAW_TOKEN_OFFSET 0x5110u
#define M10V_CAPTURE_RAW_TOKEN_BYTES 48u
#define M10V_CAPTURE_RAW_RECIPE_BYTES 0x5140u
#define M10V_CAPTURE_RAW_REJECT 0u
#define M10V_CAPTURE_RAW_LIVE 1u
#define M10V_CAPTURE_RAW_RELEASED 2u
/* Scalar control state, independent of the lossy diagnostic ring. This is
 * single-recipe stock worker state; native recipe operation serialization is
 * retained, not replaced by a lock held across original calls. */
typedef struct {uint32_t magic,owner,shooting,generation,phase,backing,source,caller,pool_result,reserved[3];} m10v_capture_raw_lifetime;
void m10v_capture_raw_init(m10v_capture_raw_lifetime *,uint32_t owner);
void m10v_capture_raw_invalidate(m10v_capture_raw_lifetime *,uint32_t owner);
void m10v_capture_raw_release_begin(m10v_capture_raw_lifetime *,uint32_t owner,uint32_t shooting,uint32_t backing,uint32_t source,uint32_t caller);
void m10v_capture_raw_pool_return(m10v_capture_raw_lifetime *,uint32_t owner,uint32_t shooting,uint32_t id,uint32_t backing,uint32_t result);
void m10v_capture_raw_set_after(m10v_capture_raw_lifetime *,uint32_t owner,uint32_t shooting,uint32_t id,uint32_t input,uint32_t old_backing,uint32_t old_source,uint32_t current_backing,uint32_t current_source);
void m10v_capture_raw_release_finish(m10v_capture_raw_lifetime *,uint32_t owner,uint32_t shooting,uint32_t backing,uint32_t source);
uint32_t m10v_capture_raw_classify(const m10v_capture_raw_lifetime *,uint32_t owner,uint32_t shooting,uint32_t backing,uint32_t source);
#endif

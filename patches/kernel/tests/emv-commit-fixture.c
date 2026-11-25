// SPDX-License-Identifier: GPL-2.0-only
// Host adapters for the extracted MiCode pack, setter, and dispatch functions.
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint64_t u64;
typedef uint64_t atomic64_t;
#define ATOMIC64_INIT(v) (v)
static u64 atomic64_inc_return_relaxed(atomic64_t *n) {
    return __atomic_add_fetch(n, 1, __ATOMIC_RELAXED);
}
#define MI_NOVA_EMV_ENABLED 1
typedef uint32_t u32;
typedef uint8_t u8;
typedef int64_t ktime_t;
typedef unsigned refcount_t;
#define __user
#define MI_EMV_MAX_SIZE 1644
#define MI_DISP_PRIMARY 0
#define MI_DISP_SECONDARY 1
#define MI_DISP_MAX 2
#define DRM_MODE_CONNECTOR_DSI 16
#define DSI_CMD_SET_STATE_HS 1
#define NSEC_PER_MSEC 1000000
#define GFP_KERNEL 0
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define min_t(t, a, b) min((t)(a), (t)(b))
#define struct_size(p, m, n) (sizeof(*(p)) + sizeof((p)->m[0]) * (n))
#define ERR_PTR(n) ((void *)(intptr_t)(n))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define READ_ONCE(x) __atomic_load_n(&(x), __ATOMIC_RELAXED)
#define WRITE_ONCE(x, v) __atomic_store_n(&(x), (v), __ATOMIC_RELAXED)
#define smp_load_acquire(p) __atomic_load_n((p), __ATOMIC_ACQUIRE)
#define smp_store_release(p, v) __atomic_store_n((p), (v), __ATOMIC_RELEASE)
#define SDE_ATRACE_BEGIN(n) ((void)0)
#define SDE_ATRACE_END(n) ((void)0)
static int64_t now;
static ktime_t ktime_get(void) {
    return now;
}
static ktime_t ktime_add_ns(ktime_t t, int64_t n) {
    return t + n;
}
static bool ktime_after(ktime_t a, ktime_t b) {
    return a > b;
}
static void refcount_set(refcount_t *p, unsigned n) {
    __atomic_store_n(p, n, __ATOMIC_RELEASE);
}
static void refcount_inc(refcount_t *p) {
    __atomic_fetch_add(p, 1, __ATOMIC_ACQ_REL);
}
static bool refcount_dec_and_test(refcount_t *p) {
    return __atomic_sub_fetch(p, 1, __ATOMIC_ACQ_REL) == 0;
}
static void *kmalloc(size_t bytes, unsigned flags) {
    (void)flags;
    return malloc(bytes);
}
static void kfree(void *p) {
    free(p);
}
static void *memdup_user(void *from, size_t n) {
    return memcpy(malloc(n), from, n);
}

struct mutex {
    pthread_mutex_t primitive;
};
#define __MUTEX_INITIALIZER(n) {PTHREAD_MUTEX_INITIALIZER}
#define DEFINE_MUTEX(n) struct mutex n = __MUTEX_INITIALIZER(n)
static void mutex_lock(struct mutex *m) {
    assert(!pthread_mutex_lock(&m->primitive));
}
static void mutex_unlock(struct mutex *m) {
    assert(!pthread_mutex_unlock(&m->primitive));
}
static bool mutex_trylock(struct mutex *m) {
    return !pthread_mutex_trylock(&m->primitive);
}

struct kthread_work {
    void (*call)(struct kthread_work *);
    bool queued;
};
struct kthread_worker {
    int unused;
};
static void kthread_init_work(struct kthread_work *w, void (*f)(struct kthread_work *)) {
    w->call = f;
    w->queued = false;
}
static bool kthread_queue_work(struct kthread_worker *k, struct kthread_work *w) {
    assert(k);
    return !__atomic_exchange_n(&w->queued, true, __ATOMIC_ACQ_REL);
}
static void kthread_cancel_work_sync(struct kthread_work *w) {
    w->queued = false;
}
static void run_queued_work(struct kthread_work *w) {
    if (__atomic_exchange_n(&w->queued, false, __ATOMIC_ACQ_REL))
        w->call(w);
}
struct MiEmvConfig {
    u32 emv_enable_state, mvInfo[MI_EMV_MAX_SIZE], mv_info_size;
};
struct dsi_panel {
    const char *type;
    struct mutex panel_lock;
};
struct dsi_display {
    struct dsi_panel *panel;
    struct mutex display_lock;
};
struct drm_device {
    int unused;
};
struct drm_crtc_state {
    bool active;
};
struct sde_crtc_state {
    struct drm_crtc_state base;
    u32 mi_emv_kicked_encoders, mi_emv_done_encoders;
};
struct drm_crtc {
    struct drm_crtc_state *state;
};
struct drm_encoder {
    struct drm_crtc *crtc;
    u32 mask;
};
struct drm_connector_state {
    struct drm_crtc *crtc;
    struct drm_encoder *best_encoder;
};
struct drm_connector {
    struct drm_device *dev;
    u32 mask;
    struct drm_connector_state *state;
};
struct drm_atomic_state {
    struct drm_crtc *crtc;
    struct drm_crtc_state *new_state;
};
static u32 drm_encoder_mask(struct drm_encoder *e) {
    return e->mask;
}
static struct drm_crtc_state *drm_atomic_get_new_crtc_state(struct drm_atomic_state *t,
                                                            struct drm_crtc *crtc) {
    return t->crtc == crtc ? t->new_state : NULL;
}
#define to_sde_crtc_state(frame) container_of(frame, struct sde_crtc_state, base)
struct sde_connector {
    struct dsi_display *display;
    int connector_type;
};
struct mi_emv_packet;
struct sde_connector_state {
    struct mi_emv_packet *mi_emv;
    bool mi_emv_reset;
};
static bool is_support_disp_id(int id) {
    return id >= 0 && id < MI_DISP_MAX;
}
static int mi_get_disp_id(const char *type) {
    return strcmp(type, "primary") ? 1 : 0;
}
static u32 drm_connector_mask(const struct drm_connector *c) {
    return c->mask;
}
static void dsi_panel_release_panel_lock(struct dsi_panel *p) {
    mutex_unlock(&p->panel_lock);
}
struct dsi_cmd_desc {
    struct {
        unsigned type;
        const void *tx_buf;
        size_t tx_len;
    } msg;
};
struct dsi_panel_cmd_set {
    struct dsi_cmd_desc *cmds;
    u32 count, state;
};
static unsigned results[4][8], batches, chunks, fail_chunk, markers[32];
struct report {
    u32 mask;
    u64 serial;
    int stage, status;
};
static struct report events[64];
static unsigned event_count;
static bool slow, started, allow_finish, kickoff_entered, kickoff_finished;
static pthread_mutex_t sync_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t sync_cv = PTHREAD_COND_INITIALIZER;
static void trace_mi_emv_batch(u32 mask, u64 serial, int stage, int status) {
    assert((mask == 1 || mask == 2) && serial);
    assert(event_count < ARRAY_SIZE(events));
    events[event_count++] = (struct report){mask, serial, stage, status};
    results[stage][status]++;
}
static int mi_dsi_display_cmd_write_locked(struct dsi_display *d, struct dsi_panel_cmd_set *cmd) {
    assert(d && cmd->count == 1 && cmd->state == DSI_CMD_SET_STATE_HS);
    assert(cmd->cmds->msg.type == 0x39 && cmd->cmds->msg.tx_len <= 3072);
    const u32 *p = cmd->cmds->msg.tx_buf;
    if (p[0] == 0x0854564e) {
        assert(batches < ARRAY_SIZE(markers));
        markers[batches++] = p[7];
        if (slow) {
            pthread_mutex_lock(&sync_lock);
            started = true;
            pthread_cond_broadcast(&sync_cv);
            while (!allow_finish)
                pthread_cond_wait(&sync_cv, &sync_lock);
            pthread_mutex_unlock(&sync_lock);
        }
    }
    chunks++;
    return fail_chunk && chunks == fail_chunk ? -EIO : 0;
}

// The generic display setter is called only when the non-Nova fixture asks for it.
static bool use_nova = true;
static int legacy_calls;
static bool mi_emv_uses_nova(void) {
    return use_nova;
}
static int mi_sde_connector_set_legacy_emv_buffer(struct sde_connector *c, void *p) {
    assert(c && p);
    legacy_calls++;
    return 0;
}

#include "production-emv.c"

static struct drm_device drm;
static struct drm_connector connector = {.dev = &drm, .mask = 1};
static struct dsi_panel panel = {"primary", __MUTEX_INITIALIZER(panel.panel_lock)};
static struct dsi_display display = {&panel, __MUTEX_INITIALIZER(display.display_lock)};
static struct sde_connector sde = {&display, DRM_MODE_CONNECTOR_DSI};
static struct kthread_worker worker;
static void config(struct MiEmvConfig *c, unsigned count, u32 first) {
    memset(c, 0, sizeof(*c));
    c->emv_enable_state = 1;
    c->mv_info_size = 1644;
    for (unsigned i = 0; i < 1644; i++)
        c->mvInfo[i] = 0x1234 + i * 0x187;
    c->mvInfo[0] = 16000;
    c->mvInfo[13] = count;
    if (count)
        c->mvInfo[14] = first;
}
// The stock source copies 996, then 1020 bytes at a time, with a continuation marker on boundaries.
static unsigned original(const u32 *m, u32 *out) {
    unsigned n = m[13], pos = 7, at = 14, step = 249;
    out[0] = 0x0854564e;
    out[1] = 0x4154454d;
    out[2] = (m[3] << 16) | (m[4] & 65535);
    out[3] = 0x10000801;
    out[4] = (m[7] << 16) | (m[8] & 65535);
    out[5] = (m[9] << 16) | (m[10] & 65535);
    out[6] = (m[11] << 16) | (m[12] & 65535);
    while (n) {
        unsigned take = n < step ? n : step;
        memcpy(out + pos, m + at, take * 4);
        pos += take;
        at += take;
        n -= take;
        if (n) {
            out[pos++] = 0x0954564e;
            step = 255;
        }
    }
    if (!(pos % 256))
        out[pos++] = 0x0954564e;
    out[pos++] = (m[at] << 16) | (m[at + 1] & 65535);
    out[pos++] = (m[at + 2] << 16) | (m[at + 3] & 65535);
    return pos * 4;
}
static void stage_packet(struct sde_connector_state *s, unsigned marker) {
    struct MiEmvConfig c;
    config(&c, 1620, marker);
    assert(!mi_sde_connector_set_emv_buffer(&sde, s, &c));
    assert(!s->mi_emv_reset);
}
static void release_state(struct sde_connector_state *s) {
    mi_emv_put(s->mi_emv);
    s->mi_emv = NULL;
}
static void post_committed(struct sde_connector_state *s) {
    mi_emv_after_kickoff(&connector, &display, s->mi_emv);
    release_state(s);
}
static void *worker_thread(void *p) {
    (void)p;
    run_queued_work(&emv[0].work);
    return NULL;
}
static void *next_kickoff(void *p) {
    (void)p;
    pthread_mutex_lock(&sync_lock);
    kickoff_entered = true;
    pthread_cond_broadcast(&sync_cv);
    pthread_mutex_unlock(&sync_lock);
    mi_emv_before_kickoff(&drm, 1, 1);
    pthread_mutex_lock(&sync_lock);
    kickoff_finished = true;
    pthread_cond_broadcast(&sync_cv);
    pthread_mutex_unlock(&sync_lock);
    return NULL;
}
int main(void) {
    // A missing completion or a recovered error does not confirm an image.
    assert(sde_kms_emv_wait_succeeded(true, 0, false, 0));
    assert(!sde_kms_emv_wait_succeeded(false, 0, false, 0));
    assert(!sde_kms_emv_wait_succeeded(true, -EWOULDBLOCK, false, 0));
    assert(!sde_kms_emv_wait_succeeded(true, -ETIMEDOUT, false, 0));
    assert(!sde_kms_emv_wait_succeeded(true, 0, true, 0));
    assert(!sde_kms_emv_wait_succeeded(true, 0, false, -EIO));

    // Each gate must independently identify the CRTC and encoder of the same atomic commit.
    struct sde_crtc_state frame = {
        .base = {.active = true}, .mi_emv_kicked_encoders = 2, .mi_emv_done_encoders = 2};
    struct drm_crtc crtc = {&frame.base}, other_crtc = {0};
    struct drm_encoder encoder = {&crtc, 2};
    struct drm_connector_state state = {&crtc, &encoder}, other_state = {&crtc, &encoder};
    struct drm_atomic_state transaction = {&crtc, &frame.base};
    connector.state = &state;
    assert(sde_kms_emv_confirmed(&transaction, &connector, &state));
    assert(!sde_kms_emv_confirmed(&transaction, &connector, &other_state));
    frame.mi_emv_kicked_encoders = 1;
    assert(!sde_kms_emv_confirmed(&transaction, &connector, &state));
    frame.mi_emv_kicked_encoders = 2;
    frame.mi_emv_done_encoders = 1;
    assert(!sde_kms_emv_confirmed(&transaction, &connector, &state));
    frame.mi_emv_done_encoders = 2;
    frame.base.active = false;
    assert(!sde_kms_emv_confirmed(&transaction, &connector, &state));
    frame.base.active = true;
    crtc.state = NULL;
    assert(!sde_kms_emv_confirmed(&transaction, &connector, &state));
    crtc.state = &frame.base;
    transaction.crtc = &other_crtc;
    assert(!sde_kms_emv_confirmed(&transaction, &connector, &state));
    transaction.crtc = &crtc;
    encoder.crtc = &other_crtc;
    assert(!sde_kms_emv_confirmed(&transaction, &connector, &state));
    encoder.crtc = &crtc;
    assert(sde_kms_emv_confirmed(&transaction, &connector, &state));

    // Compare the complete wire packet at every possible chunk boundary.
    struct MiEmvConfig c;
    u32 wire[1700];
    for (unsigned n = 0; n <= 1644 - 18; n++) {
        config(&c, n, 0x9876);
        unsigned expected = original(c.mvInfo, wire);
        struct mi_emv_packet *p = mi_emv_pack(&c, 12345);
        assert(p && !IS_ERR(p) && p->deadline == 12345);
        assert(p->bytes == expected && !memcmp(wire, p->data, expected));
        mi_emv_put(p);
    }
    config(&c, 1627, 1);
    assert(PTR_ERR(mi_emv_pack(&c, 0)) == -EINVAL);
    c.mv_info_size = 17;
    c.mvInfo[13] = 0;
    assert(PTR_ERR(mi_emv_pack(&c, 0)) == -EINVAL);
    c.mv_info_size = 0;
    assert(PTR_ERR(mi_emv_pack(&c, 0)) == -EINVAL);
    c.mv_info_size = 1645;
    assert(PTR_ERR(mi_emv_pack(&c, 0)) == -EINVAL);
    config(&c, 1620, 1);
    c.mvInfo[0] = 40000;
    assert(!mi_emv_pack(&c, 0));
    c.mvInfo[0] |= 0x10000;
    struct mi_emv_packet *test_pattern = mi_emv_pack(&c, 0);
    assert(test_pattern && !IS_ERR(test_pattern));
    mi_emv_put(test_pattern);
    // A later ioctl must not overwrite a packet owned by an earlier commit.
    struct sde_connector_state a = {0}, b = {0}, failed = {0}, test_only = {0};
    mi_emv_attach(0, &display, &worker);
    stage_packet(&a, 10);
    stage_packet(&b, 20);
    stage_packet(&a, 11);
    stage_packet(&test_only, 100);
    release_state(&test_only);
    stage_packet(&failed, 200);
    config(&c, 1627, 2);
    assert(mi_sde_connector_set_emv_buffer(&sde, &failed, &c) == -EINVAL);
    release_state(&failed);
    assert(batches == 0);
    post_committed(&a);
    mi_emv_before_kickoff(&drm, 2, 2);
    assert(batches == 0);
    mi_emv_before_kickoff(&drm, 1, 1);
    post_committed(&b);
    run_queued_work(&emv[0].work);
    run_queued_work(&emv[0].work);
    assert(batches == 2 && markers[0] == 11 && markers[1] == 20 && chunks == 6);
    assert(results[EMV_BEFORE_KICKOFF][EMV_OK] == 1 && results[EMV_WORKER][EMV_OK] == 1);
    // Idle, expiry, lock contention and transfer failure each terminate their own batch.
    stage_packet(&a, 30);
    post_committed(&a);
    mi_emv_before_kickoff(&drm, 1, 0);
    run_queued_work(&emv[0].work);
    assert(results[EMV_BEFORE_KICKOFF][EMV_CANCELLED] == 1 && batches == 2);
    stage_packet(&a, 31);
    config(&c, 1620, 2);
    c.mvInfo[0] = 40000;
    assert(!mi_sde_connector_set_emv_buffer(&sde, &a, &c) && a.mi_emv_reset && !a.mi_emv);
    stage_packet(&a, 32);
    post_committed(&a);
    now += 16000001;
    mi_emv_before_kickoff(&drm, 1, 1);
    assert(results[EMV_BEFORE_KICKOFF][EMV_EXPIRED] == 1 && batches == 2);
    stage_packet(&a, 33);
    post_committed(&a);
    mutex_lock(&panel.panel_lock);
    run_queued_work(&emv[0].work);
    mutex_unlock(&panel.panel_lock);
    assert(results[EMV_WORKER][EMV_BUSY] == 1 && batches == 2);
    stage_packet(&a, 34);
    post_committed(&a);
    fail_chunk = chunks + 2;
    run_queued_work(&emv[0].work);
    assert(results[EMV_WORKER][EMV_DSI_ERROR] == 1 && chunks == 8);
    fail_chunk = 0;
    // An already admitted slow transfer must finish before the next actual kickoff can advance.
    slow = true;
    stage_packet(&a, 35);
    post_committed(&a);
    pthread_t running, next;
    assert(!pthread_create(&running, NULL, worker_thread, NULL));
    pthread_mutex_lock(&sync_lock);
    while (!started)
        pthread_cond_wait(&sync_cv, &sync_lock);
    pthread_mutex_unlock(&sync_lock);
    assert(!pthread_create(&next, NULL, next_kickoff, NULL));
    pthread_mutex_lock(&sync_lock);
    while (!kickoff_entered)
        pthread_cond_wait(&sync_cv, &sync_lock);
    assert(!kickoff_finished);
    allow_finish = true;
    pthread_cond_broadcast(&sync_cv);
    pthread_mutex_unlock(&sync_lock);
    pthread_join(running, NULL);
    pthread_join(next, NULL);
    slow = false;
    assert(kickoff_finished && batches == 4 && chunks == 11);
    // Unbinding cancels the outstanding batch and a subsequent attach starts cleanly.
    stage_packet(&a, 36);
    post_committed(&a);
    mi_emv_detach(0, &display);
    run_queued_work(&emv[0].work);
    stage_packet(&a, 37);
    post_committed(&a);
    assert(results[EMV_DETACH][EMV_CANCELLED] == 1 && results[EMV_COMMIT][EMV_OFFLINE] == 1);
    mi_emv_attach(0, &display, &worker);
    stage_packet(&a, 38);
    post_committed(&a);
    run_queued_work(&emv[0].work);
    mi_emv_detach(0, &display);
    assert(batches == 5 && markers[4] == 38);
    // A rejected real display commit has exactly its own ID and no DSI transfer.
    stage_packet(&a, 39);
    mi_emv_no_display_commit(&connector, a.mi_emv);
    release_state(&a);
    unsigned total = 0;
    for (unsigned i = 0; i < event_count; i++) {
        struct report event = events[i];
        if (event.stage != EMV_COMMIT)
            continue;
        unsigned terminals = 0;
        for (unsigned j = 0; j < event_count; j++) {
            if (i != j && events[j].serial == event.serial) {
                assert(j > i && events[j].mask == event.mask && events[j].stage != EMV_COMMIT);
                terminals++;
            }
        }
        assert(terminals == (event.status == EMV_OK));
        total++;
    }
    assert(total == 11 && batches == 5);
    // The same connector index in a separate DRM device cannot claim the packet.
    struct drm_device other = {0};
    mi_emv_attach(0, &display, &worker);
    stage_packet(&a, 40);
    post_committed(&a);
    mi_emv_before_kickoff(&other, 1, 1);
    assert(batches == 5);
    mi_emv_before_kickoff(&drm, 1, 1);
    assert(batches == 6 && markers[5] == 40);
    mi_emv_detach(0, &display);
    use_nova = false;
    config(&c, 1620, 41);
    assert(!mi_sde_connector_set_emv_buffer(&sde, &a, &c) && legacy_calls == 1 && !a.mi_emv);
    puts(
        "PASS 1627 packet lengths, transactional ownership, display eligibility, worker/takeover,");
    puts(
        "     cancellation, delayed DSI, faults, trace correlation, device isolation and reattach");
}

/* Fixed-size ring buffer (single-producer / single-consumer style).
 *
 * Why a quant cares: every order-book matching engine and every market-data
 * feed handler uses a ring buffer somewhere. The pattern — a contiguous
 * array of slots with head/tail indices wrapping modulo capacity — is the
 * canonical lock-free primitive. Here it's single-threaded so the indices
 * are plain ints; in production each side gets its own atomic. */

#include <stdio.h>
#include <stdbool.h>

#define CAP 4

typedef struct {
    int slots[CAP];
    int head;   /* next write index (mod CAP) */
    int tail;   /* next read index  (mod CAP) */
    int count;  /* simplifies full vs empty disambiguation */
} RingBuffer;

static void rb_init(RingBuffer *rb) {
    rb->head = rb->tail = rb->count = 0;
}

static bool rb_push(RingBuffer *rb, int x) {
    if (rb->count == CAP) return false;
    rb->slots[rb->head] = x;
    rb->head = (rb->head + 1) % CAP;
    rb->count++;
    return true;
}

static bool rb_pop(RingBuffer *rb, int *out) {
    if (rb->count == 0) return false;
    *out = rb->slots[rb->tail];
    rb->tail = (rb->tail + 1) % CAP;
    rb->count--;
    return true;
}

int main(void) {
    RingBuffer rb;
    rb_init(&rb);

    for (int i = 1; i <= 6; i++) {
        bool ok = rb_push(&rb, i * 10);
        printf("push(%d) %s  count=%d\n", i * 10, ok ? "ok" : "FULL", rb.count);
    }
    int v;
    while (rb_pop(&rb, &v)) {
        printf("pop -> %d  count=%d\n", v, rb.count);
    }
    return 0;
}

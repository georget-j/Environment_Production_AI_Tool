/* Manual strlen vs <string.h>'s strlen.
 *
 * Why a quant cares: this is the smallest case of "library code is fast
 * because someone vectorised it." libc's strlen on x86 reads 16 bytes
 * at a time with SSE/AVX intrinsics; a hand-written byte loop reads one
 * byte at a time. The semantics are identical; the speed isn't. */

#include <stdio.h>
#include <string.h>
#include <time.h>

static size_t manual_strlen(const char *s) {
    const char *p = s;
    while (*p != '\0') {
        p++;
    }
    return (size_t)(p - s);
}

int main(void) {
    /* Build a long string at runtime. */
    static char buf[10001];
    for (int i = 0; i < 10000; i++) buf[i] = 'A' + (i % 26);
    buf[10000] = '\0';

    const int iterations = 5000;
    size_t total = 0;

    clock_t t0 = clock();
    for (int i = 0; i < iterations; i++) total += manual_strlen(buf);
    clock_t t1 = clock();
    for (int i = 0; i < iterations; i++) total += strlen(buf);
    clock_t t2 = clock();

    double ms_manual = 1000.0 * (t1 - t0) / CLOCKS_PER_SEC;
    double ms_libc   = 1000.0 * (t2 - t1) / CLOCKS_PER_SEC;

    printf("string length: %zu\n", strlen(buf));
    printf("manual strlen x %d: %.2f ms\n", iterations, ms_manual);
    printf("libc   strlen x %d: %.2f ms\n", iterations, ms_libc);
    if (ms_libc > 0) {
        printf("speedup: %.2fx\n", ms_manual / ms_libc);
    }
    (void)total; /* keep the compiler from eliding the work */
    return 0;
}

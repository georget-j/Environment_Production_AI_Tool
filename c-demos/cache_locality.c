/* Cache locality — same data, two access patterns, very different speed.
 *
 * Why a quant cares: covariance matrix multiplies and rolling-window
 * computations spend most of their time waiting on memory, not CPU. The
 * pattern you walk through memory matters because the L1 cache holds
 * one ~64-byte cache line at a time — sequential access is ~10x faster
 * than random access at the same algorithmic cost.
 *
 * Here we sum a 1000x1000 matrix two ways. Both do 1M loads. Row-major
 * walks neighbouring memory; column-major jumps by 4KB each load. */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 1000

static double *matrix;

static long sum_row_major(void) {
    long s = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            s += (long)matrix[i * N + j];
        }
    }
    return s;
}

static long sum_col_major(void) {
    long s = 0;
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) {
            s += (long)matrix[i * N + j];
        }
    }
    return s;
}

int main(void) {
    matrix = malloc(sizeof(double) * N * N);
    for (int i = 0; i < N * N; i++) matrix[i] = (double)(i % 7);

    clock_t t0 = clock();
    long s1 = sum_row_major();
    clock_t t1 = clock();
    long s2 = sum_col_major();
    clock_t t2 = clock();

    double ms_row = 1000.0 * (t1 - t0) / CLOCKS_PER_SEC;
    double ms_col = 1000.0 * (t2 - t1) / CLOCKS_PER_SEC;

    printf("sum  (sanity check, should match): row=%ld col=%ld\n", s1, s2);
    printf("row-major:    %.2f ms\n", ms_row);
    printf("column-major: %.2f ms\n", ms_col);
    if (ms_row > 0) {
        printf("ratio: column / row = %.2fx\n", ms_col / ms_row);
    }
    free(matrix);
    return 0;
}

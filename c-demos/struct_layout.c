/* Struct layout — why sizeof() can surprise you.
 *
 * Why a quant cares: market-data structs are read billions of times per
 * day. A 24-byte struct in a 64-byte cache line lets you pack 2 per line;
 * a poorly-packed 40-byte struct fits only 1. The compiler inserts
 * padding to satisfy alignment requirements — usually invisible, but at
 * HFT scale it's measured.
 *
 * Here we declare two functionally identical Order structs and print
 * sizeof. The second one is reordered to drop the padding. */

#include <stdio.h>
#include <stddef.h>

typedef struct {
    char side;         /* 1 byte */
                       /* 7 bytes padding here so price aligns to 8 */
    double price;      /* 8 bytes */
    int qty;           /* 4 bytes */
                       /* 4 bytes padding here so size is a multiple of 8 */
} OrderNaive;

typedef struct {
    double price;      /* 8 bytes — biggest field first */
    int qty;           /* 4 bytes */
    char side;         /* 1 byte */
                       /* 3 bytes padding (smaller) */
} OrderPacked;

int main(void) {
    printf("sizeof(OrderNaive)  = %zu bytes\n", sizeof(OrderNaive));
    printf("sizeof(OrderPacked) = %zu bytes\n", sizeof(OrderPacked));
    printf("offsetof(price, naive)  = %zu\n", offsetof(OrderNaive, price));
    printf("offsetof(price, packed) = %zu\n", offsetof(OrderPacked, price));
    printf("\n");
    printf("Same fields, different order. The naive layout wastes %zu bytes\n",
           sizeof(OrderNaive) - sizeof(OrderPacked));
    printf("per record — meaningful when you stream 10M ticks/sec.\n");
    return 0;
}

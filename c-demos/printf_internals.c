/* printf format specifiers — the C output toolkit.
 *
 * Why a quant cares: log lines, debug dumps, and CSV emitters in
 * production code all reach for printf-family functions. Knowing the
 * specifiers (and how %.4f differs from %g, why %p shows hex, why
 * width specifiers matter for alignment) is table stakes. */

#include <stdio.h>

int main(void) {
    int    qty   = 42;
    double price = 100.13579;
    char  *side  = "BUY";
    void  *addr  = (void *)&qty;

    printf("decimal:           %d\n",      qty);
    printf("hex (lowercase):   %x\n",      qty);
    printf("hex (with prefix): %#x\n",     qty);
    printf("padded width 6:    %6d\n",     qty);
    printf("zero-padded:       %06d\n",    qty);
    printf("\n");
    printf("float (default):   %f\n",      price);
    printf("float (.2f):       %.2f\n",    price);
    printf("scientific:        %.3e\n",    price);
    printf("shortest (.4g):    %.4g\n",    price);
    printf("\n");
    printf("string:            %s\n",      side);
    printf("right-justified:   |%6s|\n",   side);
    printf("left-justified:    |%-6s|\n",  side);
    printf("\n");
    printf("pointer:           %p\n",      addr);
    printf("character:         %c\n",      side[0]);
    return 0;
}

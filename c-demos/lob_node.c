/* Limit order book — sorted insert into a singly-linked list, then
 * top-of-book read.
 *
 * Why a quant cares: an LOB needs O(1) top-of-book and O(log N) or better
 * insertion. Linked lists give you O(1) at the head but O(N) insertion in
 * the middle — production LOBs use heaps or skiplists. This demo uses a
 * sorted list so you can SEE the structure; production code uses
 * intrusive doubly-linked lists at each price level for O(1) cancel. */

#include <stdio.h>
#include <stdlib.h>

typedef struct Order {
    int order_id;
    double price;
    int qty;
    struct Order *next;
} Order;

/* Insert sorted descending by price (bids; best bid at head). */
static Order *insert_bid(Order *head, int id, double price, int qty) {
    Order *n = malloc(sizeof *n);
    n->order_id = id;
    n->price = price;
    n->qty = qty;
    n->next = NULL;

    if (head == NULL || price > head->price) {
        n->next = head;
        return n;
    }
    Order *cur = head;
    while (cur->next != NULL && cur->next->price >= price) {
        cur = cur->next;
    }
    n->next = cur->next;
    cur->next = n;
    return head;
}

static void print_book(Order *head) {
    printf("bids: ");
    for (Order *c = head; c != NULL; c = c->next) {
        printf("[#%d %.2f x %d] ", c->order_id, c->price, c->qty);
    }
    printf("\n");
}

int main(void) {
    Order *bids = NULL;
    bids = insert_bid(bids, 1, 100.05, 5);
    bids = insert_bid(bids, 2, 100.10, 3);
    bids = insert_bid(bids, 3, 99.95, 8);
    bids = insert_bid(bids, 4, 100.10, 2);
    bids = insert_bid(bids, 5, 100.07, 1);

    print_book(bids);
    if (bids != NULL) {
        printf("best bid: %.2f (qty %d)\n", bids->price, bids->qty);
    }
    return 0;
}

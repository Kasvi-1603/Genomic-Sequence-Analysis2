/*
 * Huffman Coding — lossless compression
 *
 * Time complexity : O(n + k log k)   n = input length, k = unique symbols
 * Space complexity: O(k)             tree + code table
 *
 * Works best on skewed symbol distributions (common bases in genomic data).
 *
 * IGDA reference: src/igda/compression/huffman.py
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SYMBOLS 256

typedef struct HNode {
    int freq;
    int order;
    char ch;              /* valid when ch >= 0 */
    int has_char;
    struct HNode *left;
    struct HNode *right;
} HNode;

typedef struct {
    char ch;
    char code[64];        /* binary string: '0' / '1' */
} HuffCode;

/* Min-heap for building the Huffman tree */
typedef struct {
    HNode **data;
    int size;
    int cap;
} MinHeap;

static void heap_push(MinHeap *h, HNode *node) {
    int i = h->size++;
    h->data[i] = node;
    while (i > 0) {
        int p = (i - 1) / 2;
        HNode *a = h->data[i];
        HNode *b = h->data[p];
        if (a->freq > b->freq || (a->freq == b->freq && a->order > b->order))
            break;
        h->data[i] = b;
        h->data[p] = a;
        i = p;
    }
}

static HNode *heap_pop(MinHeap *h) {
    HNode *top = h->data[0];
    h->data[0] = h->data[--h->size];
    int i = 0;
    for (;;) {
        int l = 2 * i + 1, r = 2 * i + 2, best = i;
        if (l < h->size) {
            HNode *a = h->data[l], *b = h->data[best];
            if (a->freq < b->freq || (a->freq == b->freq && a->order < b->order))
                best = l;
        }
        if (r < h->size) {
            HNode *a = h->data[r], *b = h->data[best];
            if (a->freq < b->freq || (a->freq == b->freq && a->order < b->order))
                best = r;
        }
        if (best == i) break;
        HNode *tmp = h->data[i];
        h->data[i] = h->data[best];
        h->data[best] = tmp;
        i = best;
    }
    return top;
}

static HNode *hnode_leaf(int freq, int order, char ch) {
    HNode *n = (HNode *)calloc(1, sizeof(HNode));
    n->freq = freq;
    n->order = order;
    n->ch = ch;
    n->has_char = 1;
    return n;
}

static HNode *hnode_internal(int freq, int order, HNode *l, HNode *r) {
    HNode *n = (HNode *)calloc(1, sizeof(HNode));
    n->freq = freq;
    n->order = order;
    n->left = l;
    n->right = r;
    return n;
}

static void free_tree(HNode *root) {
    if (!root) return;
    free_tree(root->left);
    free_tree(root->right);
    free(root);
}

/* Count symbol frequencies in text */
static int count_freq(const char *text, int freq[MAX_SYMBOLS]) {
    memset(freq, 0, sizeof(int) * MAX_SYMBOLS);
    int unique = 0;
    for (int i = 0; text[i]; i++) {
        unsigned char c = (unsigned char)text[i];
        if (freq[c] == 0) unique++;
        freq[c]++;
    }
    return unique;
}

static HNode *build_huffman_tree(const char *text) {
    int freq[MAX_SYMBOLS];
    int unique = count_freq(text, freq);
    if (unique == 0) return NULL;

    MinHeap heap = {0};
    heap.cap = unique + 8;
    heap.data = (HNode **)calloc((size_t)heap.cap, sizeof(HNode *));
    int order = 0;

    for (int c = 0; c < MAX_SYMBOLS; c++) {
        if (freq[c] > 0)
            heap_push(&heap, hnode_leaf(freq[c], order++, (char)c));
    }

    while (heap.size > 1) {
        HNode *a = heap_pop(&heap);
        HNode *b = heap_pop(&heap);
        heap_push(&heap, hnode_internal(a->freq + b->freq, order++, a, b));
    }

    HNode *root = heap.size ? heap_pop(&heap) : NULL;
    free(heap.data);
    return root;
}

static void build_codes_rec(HNode *node, char *prefix, int depth,
                            HuffCode *table, int *ncodes) {
    if (!node) return;
    if (node->has_char) {
        table[*ncodes].ch = node->ch;
        if (depth == 0) {
            strcpy(table[*ncodes].code, "0");
        } else {
            prefix[depth] = '\0';
            strcpy(table[*ncodes].code, prefix);
        }
        (*ncodes)++;
        return;
    }
    prefix[depth] = '0';
    build_codes_rec(node->left, prefix, depth + 1, table, ncodes);
    prefix[depth] = '1';
    build_codes_rec(node->right, prefix, depth + 1, table, ncodes);
    prefix[depth] = '\0';
}

static int build_codes(HNode *root, HuffCode *table) {
    int n = 0;
    char prefix[64];
    build_codes_rec(root, prefix, 0, table, &n);
    return n;
}

static const char *lookup_code(HuffCode *table, int n, char ch) {
    for (int i = 0; i < n; i++)
        if (table[i].ch == ch) return table[i].code;
    return "";
}

/*
 * Encode text to a bitstring (stored as '0'/'1' chars for clarity).
 * Caller must free *bitstring.
 */
int huffman_encode(const char *text, char **bitstring,
                   HuffCode *codes, int *ncodes) {
    HNode *root = build_huffman_tree(text);
    if (!root) {
        *bitstring = strdup("");
        *ncodes = 0;
        return 0;
    }

    *ncodes = build_codes(root, codes);

    size_t cap = strlen(text) * 16 + 1;
    *bitstring = (char *)malloc(cap);
    (*bitstring)[0] = '\0';

    for (int i = 0; text[i]; i++) {
        const char *code = lookup_code(codes, *ncodes, text[i]);
        strcat(*bitstring, code);
    }

    free_tree(root);
    return (int)strlen(*bitstring);
}

#ifdef HUFFMAN_DEMO
int main(void) {
    const char *dna = "ACGTACGTAAA";
    char *bits = NULL;
    HuffCode codes[MAX_SYMBOLS];
    int ncodes = 0;
    int payload_bits = huffman_encode(dna, &bits, codes, &ncodes);

    printf("Huffman encode: \"%s\"\n", dna);
    printf("Codebook (%d symbols):\n", ncodes);
    for (int i = 0; i < ncodes; i++)
        printf("  '%c' -> %s\n", codes[i].ch, codes[i].code);
    printf("Bitstring (%d bits): %s\n", payload_bits, bits);

    free(bits);
    return 0;
}
#endif

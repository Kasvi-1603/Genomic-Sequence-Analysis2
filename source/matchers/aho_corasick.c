/*
 * Aho–Corasick multi-pattern string matching
 *
 * Time complexity : O(n + m + z)   n = |text|, m = sum of pattern lengths, z = outputs
 * Space complexity: O(m)           trie + failure links
 *
 * One left-to-right pass over text; strong when searching many patterns at once.
 *
 * IGDA reference: src/igda/matchers/aho_corasick.py
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_NODES   4096
#define MAX_PATTERNS 64
#define MAX_OUT     16
#define ALPHABET    256

typedef struct {
    int next[ALPHABET];
    int fail;
    int out[MAX_OUT];
    int out_count;
    int base[MAX_OUT];
    int base_count;
} AcNode;

typedef struct {
    AcNode nodes[MAX_NODES];
    int node_count;
} AcAutomaton;

static AcNode *new_node(AcAutomaton *ac) {
    int id = ac->node_count++;
    AcNode *node = &ac->nodes[id];
    for (int i = 0; i < ALPHABET; i++)
        node->next[i] = -1;
    node->fail = 0;
    node->out_count = 0;
    node->base_count = 0;
    return node;
}

static void build_trie(AcAutomaton *ac, char *patterns[], int npatterns) {
    ac->node_count = 0;
    new_node(ac); /* root = 0 */

    for (int pid = 0; pid < npatterns; pid++) {
        const char *w = patterns[pid];
        int s = 0;
        for (int i = 0; w[i]; i++) {
            unsigned char c = (unsigned char)w[i];
            if (ac->nodes[s].next[c] < 0) {
                int u = ac->node_count;
                new_node(ac);
                ac->nodes[s].next[c] = u;
            }
            s = ac->nodes[s].next[c];
        }
        AcNode *leaf = &ac->nodes[s];
        if (leaf->base_count < MAX_OUT)
            leaf->base[leaf->base_count++] = pid;
    }
}

static void build_fail(AcAutomaton *ac) {
    int queue[MAX_NODES];
    int head = 0, tail = 0;

    for (int c = 0; c < ALPHABET; c++) {
        int u = ac->nodes[0].next[c];
        if (u >= 0) {
            ac->nodes[u].fail = 0;
            queue[tail++] = u;
        }
    }

    while (head < tail) {
        int r = queue[head++];
        for (int c = 0; c < ALPHABET; c++) {
            int u = ac->nodes[r].next[c];
            if (u < 0) continue;

            queue[tail++] = u;
            int f = ac->nodes[r].fail;
            while (f && ac->nodes[f].next[c] < 0)
                f = ac->nodes[f].fail;

            if (ac->nodes[f].next[c] >= 0)
                ac->nodes[u].fail = ac->nodes[f].next[c];
            else
                ac->nodes[u].fail = 0;
        }
    }
}

static void merge_output(AcAutomaton *ac) {
    int queue[MAX_NODES];
    int head = 0, tail = 0;
    queue[tail++] = 0;

    while (head < tail) {
        int u = queue[head++];
        for (int c = 0; c < ALPHABET; c++) {
            if (ac->nodes[u].next[c] >= 0)
                queue[tail++] = ac->nodes[u].next[c];
        }
    }

    for (int qi = 0; qi < tail; qi++) {
        int u = queue[qi];
        AcNode *node = &ac->nodes[u];
        node->out_count = node->base_count;
        for (int i = 0; i < node->base_count; i++)
            node->out[i] = node->base[i];

        if (u == 0) continue;

        AcNode *fail_node = &ac->nodes[node->fail];
        for (int i = 0; i < fail_node->out_count; i++) {
            int p = fail_node->out[i];
            int seen = 0;
            for (int j = 0; j < node->out_count; j++)
                if (node->out[j] == p) { seen = 1; break; }
            if (!seen && node->out_count < MAX_OUT)
                node->out[node->out_count++] = p;
        }
    }
}

typedef struct {
    int start;
    int pattern_id;
} AcMatch;

int aho_corasick_match(const char *text, char *patterns[], int npatterns,
                       AcMatch *matches, int max_matches, int *steps) {
    AcAutomaton ac;
    build_trie(&ac, patterns, npatterns);
    build_fail(&ac);
    merge_output(&ac);

    int found = 0;
    *steps = 0;
    int state = 0;
    int n = (int)strlen(text);

    for (int i = 0; i < n; i++) {
        unsigned char c = (unsigned char)text[i];
        while (state && ac.nodes[state].next[c] < 0) {
            (*steps)++;
            state = ac.nodes[state].fail;
        }
        if (ac.nodes[state].next[c] >= 0) {
            (*steps)++;
            state = ac.nodes[state].next[c];
        }

        AcNode *node = &ac.nodes[state];
        for (int k = 0; k < node->out_count; k++) {
            int pid = node->out[k];
            int plen = (int)strlen(patterns[pid]);
            int end = i + 1;
            int start = end - plen;
            if (found < max_matches) {
                matches[found].start = start;
                matches[found].pattern_id = pid;
                found++;
            }
        }
    }
    return found;
}

#ifdef AHO_CORASICK_DEMO
int main(void) {
    const char *text = "ACGTACGTACGT";
    char *patterns[] = { "ACG", "CGT", "GT" };
    int np = 3;
    AcMatch hits[32];
    int steps = 0;
    int k = aho_corasick_match(text, patterns, np, hits, 32, &steps);

    printf("Aho-Corasick: text=\"%s\"\n", text);
    printf("Patterns: ACG, CGT, GT\n");
    printf("Matches: %d, transition steps: %d\n", k, steps);
    for (int i = 0; i < k; i++)
        printf("  start=%d pattern=\"%s\"\n",
               hits[i].start, patterns[hits[i].pattern_id]);
    return 0;
}
#endif

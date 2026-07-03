/*
 * Boyer–Moore–Horspool string matching
 *
 * Time complexity : O(n) average; O(n * m) worst case
 * Space complexity: O(|Sigma|) shift table (256 entries for byte alphabet)
 *
 * Scans the pattern from right to left; shifts window using bad-character rule.
 *
 * IGDA reference: src/igda/matchers/horspool.py
 */

#include <stdio.h>
#include <string.h>

#define ALPHABET 256

static void build_shift_table(const char *pattern, int m, int table[ALPHABET]) {
    for (int i = 0; i < ALPHABET; i++)
        table[i] = m;

    if (m <= 1)
        return;

    for (int i = 0; i < m - 1; i++)
        table[(unsigned char)pattern[i]] = m - 1 - i;
}

int horspool_match(const char *text, const char *pattern,
                   int *starts, int max_matches, int *comparisons) {
    int n = (int)strlen(text);
    int m = (int)strlen(pattern);
    int found = 0;
    *comparisons = 0;

    if (m == 0 || n < m)
        return 0;

    int table[ALPHABET];
    build_shift_table(pattern, m, table);

    int i = 0;
    while (i <= n - m) {
        int j = m - 1;
        while (j >= 0) {
            (*comparisons)++;
            if (text[i + j] != pattern[j])
                break;
            j--;
        }

        if (j < 0) {
            if (found < max_matches)
                starts[found] = i;
            found++;
            i++;
        } else {
            i += table[(unsigned char)text[i + m - 1]];
        }
    }
    return found;
}

#ifdef HORSPOOL_DEMO
int main(void) {
    const char *text = "ACGTACGTACGTACGT";
    const char *pat = "ACGT";
    int starts[32];
    int cmp = 0;
    int k = horspool_match(text, pat, starts, 32, &cmp);

    printf("Horspool match: text=\"%s\" pattern=\"%s\"\n", text, pat);
    printf("Matches: %d, comparisons: %d\n", k, cmp);
    for (int i = 0; i < k; i++)
        printf("  start=%d\n", starts[i]);
    return 0;
}
#endif

/*
 * Knuth–Morris–Pratt (KMP) string matching
 *
 * Time complexity : O(n + m) per pattern
 * Space complexity: O(m) for LPS (longest proper prefix which is also suffix)
 *
 * Preprocesses the pattern to avoid rescanning matched prefix after mismatch.
 *
 * IGDA reference: src/igda/matchers/kmp.py
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Build LPS array for pattern (failure function) */
static void build_lps(const char *pattern, int *lps, int m) {
    lps[0] = 0;
    int length = 0;
    int i = 1;

    while (i < m) {
        if (pattern[i] == pattern[length]) {
            length++;
            lps[i] = length;
            i++;
        } else if (length > 0) {
            length = lps[length - 1];
        } else {
            lps[i] = 0;
            i++;
        }
    }
}

int kmp_match(const char *text, const char *pattern,
              int *starts, int max_matches, int *comparisons) {
    int n = (int)strlen(text);
    int m = (int)strlen(pattern);
    int found = 0;
    *comparisons = 0;

    if (m == 0 || n < m)
        return 0;

    int *lps = (int *)malloc((size_t)m * sizeof(int));
    build_lps(pattern, lps, m);

    int i = 0; /* index in text */
    int j = 0; /* index in pattern */

    while (i < n) {
        if (j < m && text[i] == pattern[j]) {
            (*comparisons)++;
            i++;
            j++;
        }

        if (j == m) {
            if (found < max_matches)
                starts[found] = i - m;
            found++;
            j = lps[j - 1];
        } else if (i < n && (j == 0 || text[i] != pattern[j])) {
            (*comparisons)++;
            if (j > 0)
                j = lps[j - 1];
            else
                i++;
        }
    }

    free(lps);
    return found;
}

#ifdef KMP_DEMO
int main(void) {
    const char *text = "ABABDABACDABABCABAB";
    const char *pat = "ABABCABAB";
    int starts[32];
    int cmp = 0;
    int k = kmp_match(text, pat, starts, 32, &cmp);

    printf("KMP match: text=\"%s\" pattern=\"%s\"\n", text, pat);
    printf("Matches: %d, comparisons: %d\n", k, cmp);
    for (int i = 0; i < k; i++)
        printf("  start=%d\n", starts[i]);
    return 0;
}
#endif

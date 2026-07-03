/*
 * Naive / Brute-force string matching
 *
 * Time complexity : O(n * m) per pattern
 * Space complexity: O(1) auxiliary (excluding output)
 *
 * Trivial baseline: retries from every shift; no preprocessing reuse.
 *
 * IGDA reference: src/igda/matchers/naive.py
 */

#include <stdio.h>
#include <string.h>

typedef struct {
    int start;
    int end;
} Match;

/*
 * Find all exact occurrences of pattern in text.
 * Writes match start indices into starts[] (at most max_matches entries).
 * Returns number of matches; *comparisons receives character comparisons.
 */
int naive_match(const char *text, const char *pattern,
                int *starts, int max_matches, int *comparisons) {
    int n = (int)strlen(text);
    int m = (int)strlen(pattern);
    int found = 0;
    *comparisons = 0;

    if (m == 0 || n < m)
        return 0;

    for (int i = 0; i <= n - m; i++) {
        int j = 0;
        while (j < m) {
            (*comparisons)++;
            if (text[i + j] != pattern[j])
                break;
            j++;
        }
        if (j == m && found < max_matches) {
            starts[found++] = i;
        }
    }
    return found;
}

#ifdef NAIVE_DEMO
int main(void) {
    const char *text = "ACGTACGTACGT";
    const char *pat = "ACGT";
    int starts[32];
    int cmp = 0;
    int k = naive_match(text, pat, starts, 32, &cmp);

    printf("Naive match: text=\"%s\" pattern=\"%s\"\n", text, pat);
    printf("Matches: %d, comparisons: %d\n", k, cmp);
    for (int i = 0; i < k; i++)
        printf("  start=%d end=%d\n", starts[i], starts[i] + (int)strlen(pat));
    return 0;
}
#endif

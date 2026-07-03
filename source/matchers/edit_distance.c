/*
 * Levenshtein edit distance (Wagner–Fischer DP)
 * Used for approximate matching with bounded edits.
 *
 * Time complexity : O(len(a) * len(b)) per pair
 * Space complexity: O(len(b)) — two rolling rows
 *
 * Windowed over text: O(n * m) average; O(n * m^2) worst (full DP per window).
 *
 * IGDA reference: src/igda/matchers/edit_distance.py
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int min3(int a, int b, int c) {
    int m = a;
    if (b < m) m = b;
    if (c < m) m = c;
    return m;
}

int levenshtein(const char *a, const char *b) {
    int m = (int)strlen(a);
    int n = (int)strlen(b);

    if (m == 0) return n;
    if (n == 0) return m;

    int *prev = (int *)malloc((size_t)(n + 1) * sizeof(int));
    int *cur  = (int *)malloc((size_t)(n + 1) * sizeof(int));

    for (int j = 0; j <= n; j++)
        prev[j] = j;

    for (int i = 1; i <= m; i++) {
        cur[0] = i;
        for (int j = 1; j <= n; j++) {
            int cost = (a[i - 1] == b[j - 1]) ? 0 : 1;
            cur[j] = min3(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost);
        }
        int *tmp = prev;
        prev = cur;
        cur = tmp;
    }

    int dist = prev[n];
    free(prev);
    free(cur);
    return dist;
}

/*
 * Slide a window of |pattern| over text; report starts where distance <= max_edits.
 */
int edit_distance_match(const char *text, const char *pattern, int max_edits,
                        int *starts, int *distances, int max_matches) {
    int n = (int)strlen(text);
    int m = (int)strlen(pattern);
    int found = 0;

    if (m == 0 || n < m)
        return 0;

    for (int i = 0; i <= n - m; i++) {
        char window[512];
        if (m >= (int)sizeof(window))
            continue;
        strncpy(window, text + i, (size_t)m);
        window[m] = '\0';

        int d = levenshtein(window, pattern);
        if (d <= max_edits && found < max_matches) {
            starts[found] = i;
            distances[found] = d;
            found++;
        }
    }
    return found;
}

#ifdef EDIT_DISTANCE_DEMO
int main(void) {
    const char *text = "ACGTACGTACGT";
    const char *pat = "ACCT";
    int starts[32], dists[32];
    int k = edit_distance_match(text, pat, 1, starts, dists, 32);

    printf("Approximate match (max_edits=1): text=\"%s\" pattern=\"%s\"\n", text, pat);
    printf("Matches: %d\n", k);
    for (int i = 0; i < k; i++)
        printf("  start=%d edit_distance=%d\n", starts[i], dists[i]);
    return 0;
}
#endif

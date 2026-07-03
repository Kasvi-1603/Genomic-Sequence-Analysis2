/*
 * Run-Length Encoding (RLE) — lossless compression
 *
 * Time complexity : O(n)        where n = input length
 * Space complexity: O(r)        where r = number of runs
 *
 * Best when data has long repeated runs (e.g. homopolymer stretches in DNA).
 * Can expand on high-entropy text.
 *
 * IGDA reference: src/igda/compression/rle.py
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char ch;
    int count;
} RleRun;

/*
 * Scan text once and fill runs[] with (character, run-length) pairs.
 * Returns number of runs written (0 if text is empty).
 */
int rle_encode(const char *text, RleRun *runs, int max_runs) {
    if (!text || text[0] == '\0')
        return 0;

    char cur = text[0];
    int cnt = 1;
    int nruns = 0;

    for (int i = 1; text[i] != '\0'; i++) {
        if (text[i] == cur) {
            cnt++;
        } else {
            if (nruns < max_runs) {
                runs[nruns].ch = cur;
                runs[nruns].count = cnt;
            }
            nruns++;
            cur = text[i];
            cnt = 1;
        }
    }

    if (nruns < max_runs) {
        runs[nruns].ch = cur;
        runs[nruns].count = cnt;
    }
    nruns++;
    return nruns;
}

/*
 * Estimate compressed size: each run stored as 1 byte (char) + 4 bytes (count).
 */
int rle_compressed_bytes(int run_count) {
    return run_count * 5;
}

/* Example usage (for demonstration) */
#ifdef RLE_DEMO
int main(void) {
    const char *dna = "AAAACCCGGGTTTTAAA";
    RleRun runs[256];
    int n = rle_encode(dna, runs, 256);
    int orig = (int)strlen(dna);
    int comp = rle_compressed_bytes(n);

    printf("RLE encode: \"%s\"\n", dna);
    printf("Runs (%d):\n", n);
    for (int i = 0; i < n; i++)
        printf("  '%c' x %d\n", runs[i].ch, runs[i].count);
    printf("Original bytes: %d, estimated compressed: %d\n", orig, comp);
    return 0;
}
#endif

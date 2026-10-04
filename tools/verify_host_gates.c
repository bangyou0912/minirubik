/* Verification tooling only. The final C search algorithm is student work. */
#define main baseline_solver_main
#include "solver.c"
#undef main

#include <errno.h>
#include <limits.h>
#include <time.h>

enum { PERM_EDGES = 5040 * 3, JOINT_EDGES = 5670 * 3 };

static uint16_t perm_edges[PERM_EDGES];
static uint16_t a_edges[JOINT_EDGES];
static uint16_t b_edges[JOINT_EDGES];
static uint8_t perm_pdb[5040];
static uint8_t a_pdb[5670];
static uint8_t b_pdb[5670];
static uint32_t counts[6];

static const char *const labels[6] = {
    "perm_transition:", "perm_pdb:",
    "joint_a_transition:", "joint_a_pdb:",
    "joint_b_transition:", "joint_b_pdb:"
};
static const uint32_t capacities[6] = {
    PERM_EDGES, 5040, JOINT_EDGES, 5670, JOINT_EDGES, 5670
};

static void die(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    exit(EXIT_FAILURE);
}

static void load_tables(const char *filename)
{
    FILE *file = fopen(filename, "r");
    char line[4096];
    int section = -1;
    if (!file) {
        perror(filename);
        exit(EXIT_FAILURE);
    }
    while (fgets(line, sizeof line, file)) {
        for (int i = 0; i < 6; ++i) {
            if (strncmp(line, labels[i], strlen(labels[i])) == 0) {
                section = i;
                break;
            }
        }
        char *data = strstr(line, section >= 0 && section % 2 ? ".byte" : ".half");
        if (!data || section < 0)
            continue;
        data += 5;
        while (*data) {
            while (*data == ' ' || *data == '\t' || *data == ',')
                ++data;
            if (*data == '\n' || *data == '\r' || *data == '\0')
                break;
            errno = 0;
            char *end;
            unsigned long value = strtoul(data, &end, 0);
            if (end == data || errno || value > UINT16_MAX)
                die("bad numeric table entry");
            if (counts[section] >= capacities[section])
                die("too many table entries");
            uint32_t index = counts[section]++;
            if (section % 2) {
                if (value > UINT8_MAX)
                    die("PDB entry exceeds one byte");
                uint8_t *table = section == 1 ? perm_pdb :
                                 section == 3 ? a_pdb : b_pdb;
                table[index] = (uint8_t) value;
            } else {
                uint16_t *table = section == 0 ? perm_edges :
                                  section == 2 ? a_edges : b_edges;
                table[index] = (uint16_t) value;
            }
            data = end;
        }
    }
    if (ferror(file))
        die("failed while reading table file");
    fclose(file);
    for (int i = 0; i < 6; ++i)
        if (counts[i] != capacities[i])
            die("table entry count mismatch");
}

static void check_projection(const char *name, const uint16_t *edges,
                             const uint8_t *pdb, uint32_t size,
                             uint32_t goal)
{
    uint32_t zeros = 0;
    unsigned maximum = 0;
    if (pdb[goal] != 0)
        die("goal PDB entry is not zero");
    for (uint32_t c = 0; c < size; ++c) {
        if (pdb[c] == 0)
            ++zeros;
        if (pdb[c] > maximum)
            maximum = pdb[c];
        for (uint32_t face = 0; face < 3; ++face) {
            uint32_t next = edges[3 * c + face];
            if (next >= size)
                die("transition is out of range");
            for (uint32_t turn = 0; turn < 3; ++turn) {
                next = edges[3 * next + face];
                if (next >= size)
                    die("composed transition is out of range");
                if (pdb[next] > pdb[c] + 1 || pdb[c] > pdb[next] + 1)
                    die("PDB is not consistent over an HTM edge");
            }
        }
    }
    if (zeros != 1)
        die("PDB must have exactly one zero entry");
    printf("H2 %s: %u entries, goal=%u, max=%u, one zero, transitions in range and consistent\n",
           name, size, goal, maximum);
}

static uint32_t joint_coordinate(const state_t *state, int first_cubie)
{
    uint8_t positions[7];
    for (int i = 0; i < 7; ++i)
        positions[state->p[i]] = (uint8_t) i;
    uint32_t p0 = positions[first_cubie];
    uint32_t p1 = positions[first_cubie + 1];
    uint32_t p2 = positions[first_cubie + 2];
    uint32_t q1 = p1 - (p0 < p1);
    uint32_t q2 = p2 - (p0 < p2) - (p1 < p2);
    uint32_t rank = p0 * 30 + q1 * 5 + q2;
    uint32_t orientation = state->o[p0] * 9 + state->o[p1] * 3 + state->o[p2];
    return rank * 27 + orientation;
}

static uint32_t packed_p(const state_t *state)
{
    uint32_t result = 0;
    for (unsigned i = 0; i < 7; ++i)
        result |= (uint32_t) state->p[i] << (3 * i);
    return result;
}

static uint32_t packed_o(const state_t *state)
{
    uint32_t result = 0;
    for (unsigned i = 0; i < 7; ++i)
        result |= (uint32_t) state->o[i] << (2 * i);
    return result;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s rv32i/search_tables.s\n", argv[0]);
        return EXIT_FAILURE;
    }
    load_tables(argv[1]);
    check_projection("permutation", perm_edges, perm_pdb, 5040, 0);
    check_projection("joint A", a_edges, a_pdb, 5670, 0);
    check_projection("joint B", b_edges, b_pdb, 5670, 2916);

    uint8_t diameter;
    uint8_t *toward = build_table(&diameter);
    uint8_t *distance = malloc(STATES);
    if (!toward || !distance)
        die("could not allocate host oracle tables");
    memset(distance, UINT8_MAX, STATES);
    distance[0] = 0;
    uint32_t histogram[12] = {0};
    histogram[0] = 1;
    uint32_t packed_checked = 0;

    clock_t started = clock();
    for (uint32_t rank = 0; rank < STATES; ++rank) {
        if (distance[rank] == UINT8_MAX) {
            uint32_t chain[12];
            unsigned length = 0;
            uint32_t cursor = rank;
            while (distance[cursor] == UINT8_MAX) {
                if (length >= 12)
                    die("oracle path exceeds diameter");
                chain[length++] = cursor;
                state_t state;
                unrank_state(cursor, &state);
                state = apply_move(state, toward[cursor]);
                cursor = rank_state(&state);
            }
            uint8_t d = distance[cursor];
            while (length) {
                uint32_t current = chain[--length];
                distance[current] = ++d;
                if (d > 11)
                    die("oracle distance exceeds 11");
                ++histogram[d];
            }
        }
        state_t state;
        unrank_state(rank, &state);
        uint32_t perm = rank / ORIENTATIONS;
        uint32_t a = joint_coordinate(&state, 0);
        uint32_t b = joint_coordinate(&state, 3);
        unsigned h = perm_pdb[perm];
        if (a_pdb[a] > h) h = a_pdb[a];
        if (b_pdb[b] > h) h = b_pdb[b];
        if (h > distance[rank])
            die("H1 inadmissible heuristic at a full-state rank");
        uint32_t p = packed_p(&state), o = packed_o(&state);
        for (unsigned i = 0; i < 7; ++i) {
            if (((p >> (3 * i)) & 7) != state.p[i] ||
                ((o >> (2 * i)) & 3) != state.o[i])
                die("H4 packed accessor mismatch");
            ++packed_checked;
        }
    }
    if (diameter != 11)
        die("oracle diameter is not 11");
    printf("H1: %u/%u full states satisfy h <= exact distance\n", STATES, STATES);
    printf("H4: %u packed position reads match unpacked values; both index parities covered\n",
           packed_checked);
    printf("Oracle diameter=%u, distance-11 states=%u, CPU time=%.3f s\n",
           diameter, histogram[11], (double)(clock() - started) / CLOCKS_PER_SEC);
    puts("H3: NOT RUN: final student C search implementation is not present");
    free(toward);
    free(distance);
    return EXIT_SUCCESS;
}

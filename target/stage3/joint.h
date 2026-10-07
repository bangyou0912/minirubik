#ifndef STAGE2_JOINT_H
#define STAGE2_JOINT_H
#include <stdint.h>
enum { S2_PERM=5040, S2_JOINT=5670, S2_MOVES=9, S2_GOAL_B=2916 };
typedef struct {
    uint16_t perm_next[3][S2_PERM];
    uint16_t joint_next[3][S2_JOINT];
    uint8_t perm_distance[S2_PERM];
    uint8_t joint_distance[2][S2_JOINT];
} s2_tables;
/* Frames cache the current quarter-turn child, avoiding repeat lookup work. */
typedef struct {
    uint16_t p,a,b,np,na,nb;
    uint8_t remaining,last_face,face,turn;
} s2_frame;
typedef struct {
    s2_frame frames[12];
    uint8_t moves[11];
    uint8_t length;
} s2_workspace;
typedef struct { uint64_t edges, visits, transition_reads, pdb_reads[3], frame_initializations, path_writes, pruned, max_comparisons, threshold_comparisons, rejected_by[3], iterations; } s2_stats;
uint16_t s2_position_rank(const uint8_t positions[3]);
uint16_t s2_joint_rank(const uint8_t p[7],const uint8_t o[7],unsigned group);
unsigned s2_heuristic(const s2_tables *t,unsigned p,unsigned a,unsigned b);
int s2_solve(const s2_tables *t,unsigned p,unsigned a,unsigned b,
             s2_workspace *w,s2_stats *stats);
#endif



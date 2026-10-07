#include "joint.h"
uint16_t s2_position_rank(const uint8_t x[3]) {
    unsigned second=x[1]-(x[1]>x[0]);
    unsigned third=x[2]-(x[2]>x[0])-(x[2]>x[1]);
    return (uint16_t)((x[0]*6U+second)*5U+third);
}
uint16_t s2_joint_rank(const uint8_t p[7],const uint8_t o[7],unsigned group) {
    uint8_t positions[3],orientations[3];
    for(unsigned i=0;i<7;i++) {
        unsigned cubie=p[i];
        if(cubie>=group*3U && cubie<group*3U+3U) {
            unsigned k=cubie-group*3U;
            positions[k]=(uint8_t)i;orientations[k]=o[i];
        }
    }
    unsigned orientation=(orientations[0]*3U+orientations[1])*3U+orientations[2];
    return (uint16_t)(s2_position_rank(positions)*27U+orientation);
}
unsigned s2_heuristic(const s2_tables *t,unsigned p,unsigned a,unsigned b) {
    unsigned h=t->perm_distance[p];
    unsigned ha=t->joint_distance[0][a],hb=t->joint_distance[1][b];
    if(ha>h)h=ha;
    if(hb>h)h=hb;
    return h;
}

#ifndef S3_VARIANT
#define S3_VARIANT 2
#endif
#ifndef S3_ORDER
#define S3_ORDER 3
#endif
#ifdef S3_COUNT
#define ADD(field,value) do {if(stats)stats->field+=(value);} while(0)
#else
#define ADD(field,value) ((void)0)
#endif
/* Orders PAB,PBA,APB,ABP,BPA,BAP; selected at compile time. */
static int rejected(const s2_tables *t,unsigned p,unsigned a,unsigned b,
                    unsigned left,s2_stats *stats) {
    (void)stats;
#if S3_VARIANT < 2
    ADD(pdb_reads[0],1);ADD(pdb_reads[1],1);ADD(pdb_reads[2],1);
    ADD(max_comparisons,2);ADD(threshold_comparisons,1);
    return s2_heuristic(t,p,a,b)>left;
#else
#define TEST_P do {ADD(pdb_reads[0],1);ADD(threshold_comparisons,1);if(t->perm_distance[p]>left){ADD(rejected_by[0],1);return 1;}}while(0)
#define TEST_A do {ADD(pdb_reads[1],1);ADD(threshold_comparisons,1);if(t->joint_distance[0][a]>left){ADD(rejected_by[1],1);return 1;}}while(0)
#define TEST_B do {ADD(pdb_reads[2],1);ADD(threshold_comparisons,1);if(t->joint_distance[1][b]>left){ADD(rejected_by[2],1);return 1;}}while(0)
#if S3_ORDER==0
    TEST_P;TEST_A;TEST_B;
#elif S3_ORDER==1
    TEST_P;TEST_B;TEST_A;
#elif S3_ORDER==2
    TEST_A;TEST_P;TEST_B;
#elif S3_ORDER==3
    TEST_A;TEST_B;TEST_P;
#elif S3_ORDER==4
    TEST_B;TEST_P;TEST_A;
#elif S3_ORDER==5
    TEST_B;TEST_A;TEST_P;
#else
#error Invalid PDB order
#endif
    return 0;
#endif
}
static int search_bound(const s2_tables *t,unsigned p,unsigned a,unsigned b,
                        unsigned bound,s2_workspace *w,s2_stats *stats) {
    int depth=0;
    ADD(iterations,1);ADD(frame_initializations,1);
    w->frames[0]=(s2_frame){p,a,b,p,a,b,bound,3,255,0};
#if S3_VARIANT > 0
    ADD(visits,1);
    /* Bound starts at root h, so the root cannot be rejected. */
    if(p==0 && a==0 && b==S2_GOAL_B){w->length=0;return 1;}
    w->frames[0].face=0;
#endif
    while(depth>=0) {
        s2_frame *f=&w->frames[depth];
#if S3_VARIANT==0
        if(f->face==255) {
            ADD(visits,1);
            if(rejected(t,f->p,f->a,f->b,f->remaining,stats)) {
                ADD(pruned,1);--depth;continue;
            }
            if(f->p==0 && f->a==0 && f->b==S2_GOAL_B){w->length=(uint8_t)depth;return 1;}
            if(!f->remaining){--depth;continue;}
            f->face=0;
        }
#endif
        if(f->face==3){--depth;continue;}
        if(f->face==f->last_face || f->turn==3) {
            ++f->face;f->turn=0;f->np=f->p;f->na=f->a;f->nb=f->b;continue;
        }
        /* Advance ALL coordinates, even if a PDB subsequently rejects it.
           The next quarter turn depends on these cached child coordinates. */
        const uint16_t *perm_row=t->perm_next[f->face];
        const uint16_t *joint_row=t->joint_next[f->face];
        f->np=perm_row[f->np];f->na=joint_row[f->na];f->nb=joint_row[f->nb];
        ADD(edges,1);ADD(transition_reads,3);
        unsigned move=f->face*3U+f->turn;
        ++f->turn;
#if S3_VARIANT > 0
        ADD(visits,1);
        unsigned left=f->remaining-1U;
        if(rejected(t,f->np,f->na,f->nb,left,stats)) {ADD(pruned,1);continue;}
        /* Commit a path entry only for a child which survives the cutoff. */
        ADD(path_writes,1);w->moves[depth]=(uint8_t)move;
        if(f->np==0 && f->na==0 && f->nb==S2_GOAL_B){w->length=(uint8_t)(depth+1);return 1;}
        if(!left)continue;
        s2_frame child={f->np,f->na,f->nb,f->np,f->na,f->nb,left,f->face,0,0};
#else
        ADD(path_writes,1);w->moves[depth]=(uint8_t)move;
        s2_frame child={f->np,f->na,f->nb,f->np,f->na,f->nb,f->remaining-1,f->face,255,0};
#endif
        ADD(frame_initializations,1);w->frames[++depth]=child;
    }
    return 0;
}
int s2_solve(const s2_tables *t,unsigned p,unsigned a,unsigned b,
             s2_workspace *w,s2_stats *stats) {
    (void)stats;
    if(p>=S2_PERM || a>=S2_JOINT || b>=S2_JOINT)return 0;
    w->length=255;
#ifdef S3_COUNT
    if(stats)*stats=(s2_stats){0};
#endif
    /* Only the root needs the numerical maximum to set the first bound. */
    ADD(pdb_reads[0],1);ADD(pdb_reads[1],1);ADD(pdb_reads[2],1);ADD(max_comparisons,2);
    unsigned start=s2_heuristic(t,p,a,b);
    for(unsigned bound=start;bound<=11;bound++)
        if(search_bound(t,p,a,b,bound,w,stats))return 1;
    return 0;
}

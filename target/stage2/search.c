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
/* Enumeration order: R,R2,R',B,B2,B',D,D2,D'. */
static int search_bound(const s2_tables *t,unsigned p,unsigned a,unsigned b,
                        unsigned bound,s2_workspace *w,s2_stats *stats) {
    int depth=0;
    w->frames[0]=(s2_frame){p,a,b,p,a,b,bound,3,255,0};
    while(depth>=0) {
        s2_frame *f=&w->frames[depth];
        if(f->face==255) {
            if(stats)++stats->visits;
            if(s2_heuristic(t,f->p,f->a,f->b)>f->remaining) {--depth;continue;}
            if(f->p==0 && f->a==0 && f->b==S2_GOAL_B) {
                w->length=(uint8_t)depth;return 1;
            }
            if(!f->remaining) {--depth;continue;}
            f->face=0;
        }
        if(f->face==3) {--depth;continue;}
        if(f->face==f->last_face || f->turn==3) {
            ++f->face;f->turn=0;
            f->np=f->p;f->na=f->a;f->nb=f->b;continue;
        }
        f->np=t->perm_next[f->face][f->np];
        f->na=t->joint_next[f->face][f->na];
        f->nb=t->joint_next[f->face][f->nb];
        if(stats)++stats->edges;
        w->moves[depth]=(uint8_t)(f->face*3U+f->turn);
        ++f->turn;
        s2_frame child={f->np,f->na,f->nb,f->np,f->na,f->nb,
                        f->remaining-1,f->face,255,0};
        w->frames[++depth]=child;
    }
    return 0;
}
int s2_solve(const s2_tables *t,unsigned p,unsigned a,unsigned b,
             s2_workspace *w,s2_stats *stats) {
    if(p>=S2_PERM || a>=S2_JOINT || b>=S2_JOINT)return 0;
    w->length=255;
    if(stats)stats->edges=stats->visits=0;
    for(unsigned bound=s2_heuristic(t,p,a,b);bound<=11;bound++)
        if(search_bound(t,p,a,b,bound,w,stats))return 1;
    return 0;
}


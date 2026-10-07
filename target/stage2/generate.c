/* All table computation is host-side C, using the baseline move geometry. */
#define main baseline_main
#include "../../solver.c"
#undef main
#include "joint.h"
static s2_tables tables;
static uint16_t queue[S2_JOINT];
static void decode_joint(unsigned rank,uint8_t x[3],uint8_t o[3]) {
    unsigned orientation=rank%27U,position=rank/27U;
    unsigned digits[3]={position/30U,(position/5U)%6U,position%5U};
    uint8_t available[7]={0,1,2,3,4,5,6};
    for(unsigned i=0;i<3;i++) {
        x[i]=available[digits[i]];
        for(unsigned j=digits[i];j+1<7-i;j++)available[j]=available[j+1];
    }
    for(unsigned i=3;i-->0;) {o[i]=orientation%3U;orientation/=3U;}
}
static unsigned bfs(const uint16_t *next,unsigned count,unsigned goal,uint8_t *distance) {
    memset(distance,255,count);distance[goal]=0;queue[0]=goal;
    unsigned tail=1;
    for(unsigned head=0;head<tail;head++) {
        unsigned root=queue[head];
        for(unsigned face=0;face<3;face++) {
            unsigned child=root;
            for(unsigned turn=0;turn<3;turn++) {
                child=next[face*count+child];
                if(distance[child]==255) {distance[child]=distance[root]+1;queue[tail++]=child;}
            }
        }
    }
    return tail;
}
static void write_file(const char *name,const void *data,size_t n) {
    FILE *f=fopen(name,"wb");
    if(!f || fwrite(data,1,n,f)!=n || fclose(f))exit(1);
}
int main(void) {
    if(sizeof(s2_tables)!=80640 || sizeof(s2_frame)!=16 || sizeof(s2_workspace)!=204)return 1;
    for(unsigned p=0;p<S2_PERM;p++) {
        state_t state;unrank_state(p*729U,&state);
        for(unsigned face=0;face<3;face++) {
            state_t next=quarter_turn(state,face);
            tables.perm_next[face][p]=(uint16_t)(rank_state(&next)/729U);
        }
    }
    for(unsigned rank=0;rank<S2_JOINT;rank++) {
        uint8_t x[3],o[3];decode_joint(rank,x,o);
        for(unsigned face=0;face<3;face++) {
            uint8_t dest[7],nx[3],no[3];
            for(unsigned i=0;i<7;i++)dest[source[face][i]]=i;
            for(unsigned i=0;i<3;i++) {
                nx[i]=dest[x[i]];no[i]=(o[i]+twist[face][nx[i]])%3U;
            }
            unsigned orientation=(no[0]*3U+no[1])*3U+no[2];
            tables.joint_next[face][rank]=(uint16_t)(s2_position_rank(nx)*27U+orientation);
        }
    }
    unsigned coverage[3];
    coverage[0]=bfs(&tables.perm_next[0][0],S2_PERM,0,tables.perm_distance);
    coverage[1]=bfs(&tables.joint_next[0][0],S2_JOINT,0,tables.joint_distance[0]);
    coverage[2]=bfs(&tables.joint_next[0][0],S2_JOINT,S2_GOAL_B,tables.joint_distance[1]);
    if(coverage[0]!=S2_PERM || coverage[1]!=S2_JOINT || coverage[2]!=S2_JOINT)return 1;
    /* Explicit little-endian output for RV32I, independent of host endianness. */
    FILE *f=fopen("target/stage2/tables.bin","wb");if(!f)return 1;
    for(unsigned group=0;group<2;group++) {
        unsigned n=group?S2_JOINT:S2_PERM;
        const uint16_t *next=group?&tables.joint_next[0][0]:&tables.perm_next[0][0];
        for(unsigned i=0;i<3*n;i++) {if(fputc(next[i]&255,f)==EOF || fputc(next[i]>>8,f)==EOF)return 1;}
    }
    if(fwrite(tables.perm_distance,1,S2_PERM,f)!=S2_PERM ||
       fwrite(tables.joint_distance,1,2*S2_JOINT,f)!=2*S2_JOINT || fclose(f))return 1;
    write_file("target/stage2/perm-next.bin",tables.perm_next,sizeof tables.perm_next);
    printf("C-generated coverage: %u / %u / %u\n",coverage[0],coverage[1],coverage[2]);
    printf("tables=%zu frame=%zu workspace=%zu subtotal=%zu spare=%zu\n",
        sizeof tables,sizeof(s2_frame),sizeof(s2_workspace),sizeof tables+sizeof(s2_workspace),131072-sizeof tables-sizeof(s2_workspace));
    return 0;
}


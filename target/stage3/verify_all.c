#define main baseline_main
#include "../../solver.c"
#undef main
#include "joint.h"
#include <time.h>
static s2_tables tables;
static struct {uint32_t before;s2_workspace w;uint32_t after;} guarded={.before=0x1234abcd,.after=0x5678ef01};
static void require(int good,const char *reason){if(!good){fprintf(stderr,"FAIL: %s\n",reason);exit(1);}}
static void load(void){
    FILE *f=fopen("target/stage2/tables.bin","rb");require(f!=NULL,"tables");
    for(unsigned face=0;face<3;face++)for(unsigned i=0;i<S2_PERM;i++) {
        int lo=fgetc(f),hi=fgetc(f);require(lo>=0 && hi>=0,"perm data");tables.perm_next[face][i]=(uint16_t)(lo|(hi<<8));
    }
    for(unsigned face=0;face<3;face++)for(unsigned i=0;i<S2_JOINT;i++) {
        int lo=fgetc(f),hi=fgetc(f);require(lo>=0 && hi>=0,"joint data");tables.joint_next[face][i]=(uint16_t)(lo|(hi<<8));
    }
    require(fread(tables.perm_distance,1,S2_PERM,f)==S2_PERM && fread(tables.joint_distance,1,2*S2_JOINT,f)==2*S2_JOINT && fclose(f)==0,"distances");
}
int main(void){
    clock_t start=clock();load();uint8_t diameter,*oracle=build_table(&diameter);
    require(oracle && diameter==11,"BFS oracle");unsigned hard=0;
    for(unsigned r=0;r<STATES;r++) {
        state_t state,replay;unrank_state(r,&state);replay=state;unsigned distance=0;
        for(unsigned rank=r;rank;rank=rank_state(&replay)) {
            require(oracle[rank]<9,"oracle move");replay=apply_move(replay,oracle[rank]);require(++distance<=11,"oracle termination");
        }
        unsigned p=r/729,a=s2_joint_rank(state.p,state.o,0),b=s2_joint_rank(state.p,state.o,1);
        require(s2_solve(&tables,p,a,b,&guarded.w,NULL),"production search");
        require(guarded.w.length==distance,"shortest length");replay=state;
        for(unsigned i=0;i<guarded.w.length;i++) {
            require(guarded.w.moves[i]<9,"move range");
            if(i)require(guarded.w.moves[i]/3!=guarded.w.moves[i-1]/3,"same-face pruning");
            replay=apply_move(replay,guarded.w.moves[i]);
        }
        require(rank_state(&replay)==0,"full-cubie replay");
        require(guarded.before==0x1234abcd && guarded.after==0x5678ef01,"workspace guards");
        hard+=distance==11;
        if((r+1)%500000==0){printf("progress %u/%u\n",r+1,STATES);fflush(stdout);}
    }
    require(!s2_solve(&tables,S2_PERM,0,S2_GOAL_B,&guarded.w,NULL),"invalid permutation");
    require(!s2_solve(&tables,0,S2_JOINT,S2_GOAL_B,&guarded.w,NULL),"invalid joint A");
    require(!s2_solve(&tables,0,0,S2_JOINT,&guarded.w,NULL),"invalid joint B");
    require(hard==2644,"hard-state count");free(oracle);
    printf("PASS: all 3674160 states return exact BFS length and solve the full cubie model; all 2644 distance-11 states included.\n");
    printf("PASS: workspace guards, move ranges, consecutive-face pruning, invalid coordinate ranges.\n");
    printf("Production ABP build: diagnostic counters compiled out. Host CPU seconds %.3f.\n",(double)(clock()-start)/CLOCKS_PER_SEC);
    return 0;
}


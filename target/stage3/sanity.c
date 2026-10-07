#define main baseline_main
#include "../../solver.c"
#undef main
#include "joint.h"
static s2_tables tables;
static void require(int condition){if(!condition){fputs("sanitizer driver check failed\n",stderr);exit(1);}}
static void load(void){
    FILE *f=fopen("target/stage2/tables.bin","rb");require(f!=NULL);
    for(unsigned face=0;face<3;face++)for(unsigned i=0;i<S2_PERM;i++){
        int lo=fgetc(f),hi=fgetc(f);require(lo>=0 && hi>=0);tables.perm_next[face][i]=(uint16_t)(lo|(hi<<8));
    }
    for(unsigned face=0;face<3;face++)for(unsigned i=0;i<S2_JOINT;i++){
        int lo=fgetc(f),hi=fgetc(f);require(lo>=0 && hi>=0);tables.joint_next[face][i]=(uint16_t)(lo|(hi<<8));
    }
    require(fread(tables.perm_distance,1,S2_PERM,f)==S2_PERM);
    require(fread(tables.joint_distance,1,2*S2_JOINT,f)==2*S2_JOINT);require(fclose(f)==0);
}
static void check(const char *vector,unsigned expected){
    state_t state;require(parse_state(vector,&state));s2_workspace w;
    unsigned p=rank_state(&state)/729,a=s2_joint_rank(state.p,state.o,0),b=s2_joint_rank(state.p,state.o,1);
    require(s2_solve(&tables,p,a,b,&w,NULL));require(w.length==expected);
    for(unsigned i=0;i<w.length;i++){require(w.moves[i]<9);state=apply_move(state,w.moves[i]);}
    require(rank_state(&state)==0);
}
int main(void){
    load();FILE *f=fopen("tests/solutions.txt","r");require(f!=NULL);char line[256];unsigned count=0;
    while(fgets(line,sizeof line,f)){
        if(line[0]=='#' || line[0]=='\n')continue;
        char *bar=strchr(line,'|');require(bar!=NULL);*bar=0;
        unsigned expected=0;for(char *token=strtok(bar+1," \r\n");token;token=strtok(NULL," \r\n"))++expected;
        check(line,expected);++count;
    }
    require(fclose(f)==0 && count==8);
    check("24173562322133",3);check("54721631111111",11);
    puts("PASS: ASan+UBSan, all 8 solution vectors, a three-move scramble, and the maximum-edge distance-11 state; production counters disabled.");
    return 0;
}

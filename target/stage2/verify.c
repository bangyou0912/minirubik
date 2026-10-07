#define main baseline_main
#include "../../solver.c"
#undef main
#include "joint.h"
#include <time.h>
static s2_tables tables;
static uint16_t orientation_next[3][729];
static uint8_t orientation_distance[729];
static uint32_t distance_histogram[12];
static s2_workspace workspace;
static uint64_t basic_edges;
static void require(int condition,const char *message) {
    if(!condition){fprintf(stderr,"FAIL: %s\n",message);exit(1);}
}
static void load_tables(void) {
    FILE *f=fopen("target/stage2/tables.bin","rb");require(f!=NULL,"tables missing");
    for(unsigned g=0;g<2;g++) {
        unsigned n=g?S2_JOINT:S2_PERM;
        uint16_t *next=g?&tables.joint_next[0][0]:&tables.perm_next[0][0];
        for(unsigned i=0;i<3*n;i++) {
            int lo=fgetc(f),hi=fgetc(f);require(lo!=EOF && hi!=EOF,"truncated transition data");next[i]=(uint16_t)(lo|(hi<<8));
        }
    }
    require(fread(tables.perm_distance,1,S2_PERM,f)==S2_PERM,"permutation distance data");
    require(fread(tables.joint_distance,1,2*S2_JOINT,f)==2*S2_JOINT,"joint distance data");
    require(fgetc(f)==EOF && !ferror(f) && fclose(f)==0,"table length");
}
static void check_projection(const uint16_t *next,const uint8_t *distance,unsigned n,unsigned goal,const char *name) {
    unsigned zeros=0,maximum=0;
    for(unsigned r=0;r<n;r++) {
        require(distance[r]!=255,"unvisited PDB state");zeros+=distance[r]==0;
        if(distance[r]>maximum)maximum=distance[r];
        for(unsigned face=0;face<3;face++) {
            unsigned child=r;
            for(unsigned turn=0;turn<3;turn++) {
                child=next[face*n+child];require(child<n,"transition range");
                require(distance[r]<=1U+distance[child] && distance[child]<=1U+distance[r],"PDB consistency");
            }
            require(next[face*n+child]==r,"four quarter turns");
        }
    }
    require(zeros==1 && distance[goal]==0,"unique goal");
    printf("%s: entries=%u goal=%u max=%u unique zero; ranges, nine-move consistency, fourth-turn identity PASS\n",name,n,goal,maximum);
}
static void make_basic(void) {
    for(unsigned o=0;o<729;o++) {
        state_t state;unrank_state(o,&state);
        for(unsigned f=0;f<3;f++){state_t next=quarter_turn(state,f);orientation_next[f][o]=rank_state(&next)%729;}
    }
    uint16_t queue[729];memset(orientation_distance,255,729);orientation_distance[0]=0;queue[0]=0;
    unsigned tail=1;
    for(unsigned head=0;head<tail;head++)for(unsigned f=0;f<3;f++) {
        unsigned child=queue[head];
        for(unsigned turn=0;turn<3;turn++) {
            child=orientation_next[f][child];
            if(orientation_distance[child]==255){orientation_distance[child]=orientation_distance[queue[head]]+1;queue[tail++]=child;}
        }
    }
    require(tail==729,"orientation coverage");
}
static unsigned basic_h(unsigned p,unsigned o) {
    return tables.perm_distance[p]>orientation_distance[o]?tables.perm_distance[p]:orientation_distance[o];
}
static int basic_dfs(unsigned p,unsigned o,unsigned left,unsigned last) {
    if(basic_h(p,o)>left)return 0;
    if(!p && !o)return 1;
    if(!left)return 0;
    for(unsigned f=0;f<3;f++)if(f!=last) {
        unsigned np=p,no=o;
        for(unsigned turn=0;turn<3;turn++) {
            np=tables.perm_next[f][np];no=orientation_next[f][no];++basic_edges;
            if(basic_dfs(np,no,left-1,f))return 1;
        }
    }
    return 0;
}
static unsigned basic_solve(unsigned p,unsigned o) {
    basic_edges=0;
    for(unsigned bound=basic_h(p,o);bound<=11;bound++)if(basic_dfs(p,o,bound,3))return bound;
    return 99;
}
static void vector_for(const state_t *s,char out[15]) {
    for(unsigned i=0;i<7;i++){out[i]=(char)('1'+s->p[i]);out[i+7]=(char)('1'+s->o[i]);}out[14]=0;
}
int main(int argc,char **argv) {
    int exhaustive=argc==2 && strcmp(argv[1],"--all")==0;
    clock_t started=clock();load_tables();make_basic();
    check_projection(&tables.perm_next[0][0],tables.perm_distance,S2_PERM,0,"permutation");
    check_projection(&tables.joint_next[0][0],tables.joint_distance[0],S2_JOINT,0,"joint A");
    check_projection(&tables.joint_next[0][0],tables.joint_distance[1],S2_JOINT,S2_GOAL_B,"joint B");
    uint8_t diameter,*oracle=build_table(&diameter);require(oracle && diameter==11,"baseline oracle");
    FILE *csv=fopen("target/stage2/distance11.csv","w");require(csv!=NULL,"CSV output");
    fprintf(csv,"vector,rank,permutation,joint_a,joint_b,basic_edges,joint_edges,joint_visits,length\n");
    unsigned hard=0,checked=0,max_basic_rank=0,max_joint_rank=0;
    uint64_t max_basic=0,max_joint=0;
    for(unsigned r=0;r<STATES;r++) {
        state_t state;unrank_state(r,&state);state_t replay=state;
        unsigned distance=0;
        for(unsigned rank=r;rank;rank=rank_state(&replay)) {
            require(oracle[rank]<9,"oracle move range");replay=apply_move(replay,oracle[rank]);require(++distance<=11,"oracle termination");
        }
        distance_histogram[distance]++;
        unsigned p=r/729,o=r%729;
        unsigned a=s2_joint_rank(state.p,state.o,0),b=s2_joint_rank(state.p,state.o,1);
        require(s2_heuristic(&tables,p,a,b)<=distance,"heuristic admissibility");
        require((s2_heuristic(&tables,p,a,b)==0)==(r==0),"full goal equivalence");
        /* Independently apply the full cubie model, then encode each projection. */
        for(unsigned f=0;f<3;f++) {
            state_t next=state;unsigned np=p,na=a,nb=b;
            for(unsigned turn=0;turn<3;turn++) {
                next=quarter_turn(next,f);
                np=tables.perm_next[f][np];na=tables.joint_next[f][na];nb=tables.joint_next[f][nb];
                require(np==rank_state(&next)/729 && na==s2_joint_rank(next.p,next.o,0) && nb==s2_joint_rank(next.p,next.o,1),"projection commutation");
            }
        }
        if(exhaustive || distance==11) {
            s2_stats stats;
            require(s2_solve(&tables,p,a,b,&workspace,&stats),"search failure");
            require(workspace.length==distance,"shortest length");
            replay=state;
            for(unsigned i=0;i<workspace.length;i++) {
                require(workspace.moves[i]<9,"search move range");
                if(i)require(workspace.moves[i]/3!=workspace.moves[i-1]/3,"same-face pruning");
                replay=apply_move(replay,workspace.moves[i]);
            }
            require(rank_state(&replay)==0,"full-cubie replay");++checked;
            if(distance==11) {
                require(basic_solve(p,o)==11,"basic shortest length");
                char vector[15];vector_for(&state,vector);
                fprintf(csv,"%s,%u,%u,%u,%u,%llu,%llu,%llu,%u\n",vector,r,p,a,b,
                    (unsigned long long)basic_edges,(unsigned long long)stats.edges,(unsigned long long)stats.visits,workspace.length);
                if(basic_edges>max_basic){max_basic=basic_edges;max_basic_rank=r;}
                if(stats.edges>max_joint){max_joint=stats.edges;max_joint_rank=r;}
                ++hard;
            }
        }
        if(exhaustive && (r+1)%500000==0){printf("search progress %u/%u\n",r+1,STATES);fflush(stdout);}
    }
    require(hard==2644,"distance-11 state count");require(fclose(csv)==0,"CSV close");free(oracle);
    printf("All %u states: projection commutation for all nine moves, admissibility, goal equivalence PASS\n",STATES);
    printf("Search: %u states have exact length and full-cubie replay PASS\n",checked);
    printf("Distance-11: %u; basic maximum edges=%llu rank=%u; joint maximum edges=%llu rank=%u\n",hard,(unsigned long long)max_basic,max_basic_rank,(unsigned long long)max_joint,max_joint_rank);
    for(unsigned d=0;d<=11;d++)printf("distance %u: %u states\n",d,distance_histogram[d]);
    printf("Host CPU seconds %.3f; these are host counts, not Ripes instruction measurements\n",(double)(clock()-started)/CLOCKS_PER_SEC);
    return 0;
}

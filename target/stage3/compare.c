#include "joint.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DECLARE(n) extern int solve_##n(const s2_tables *,unsigned,unsigned,unsigned,s2_workspace *,s2_stats *)
DECLARE(base);DECLARE(delayed);DECLARE(pab);DECLARE(pba);DECLARE(apb);DECLARE(abp);DECLARE(bpa);DECLARE(bap);
extern int stage2_reference(unsigned,unsigned,unsigned,uint8_t *,uint8_t *,uint64_t *);
static s2_tables tables;
typedef int (*solver)(const s2_tables *,unsigned,unsigned,unsigned,s2_workspace *,s2_stats *);
static const char *names[]={"baseline","delayed","PAB","PBA","APB","ABP","BPA","BAP"};
static solver solvers[]={solve_base,solve_delayed,solve_pab,solve_pba,solve_apb,solve_abp,solve_bpa,solve_bap};
static s2_stats totals[8];
static unsigned count;
static void require(int good,const char *reason){if(!good){fprintf(stderr,"FAIL %s\n",reason);exit(1);}}
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
static void accumulate(s2_stats *dst,const s2_stats *src){
#define SUM(f) dst->f+=src->f
    SUM(edges);SUM(visits);SUM(transition_reads);SUM(frame_initializations);SUM(path_writes);SUM(pruned);SUM(max_comparisons);SUM(threshold_comparisons);SUM(iterations);
    for(unsigned i=0;i<3;i++){SUM(pdb_reads[i]);SUM(rejected_by[i]);}
#undef SUM
}
static void row(FILE *out,const char *vector,const char *name,const s2_stats *s,unsigned length){
    fprintf(out,"%s,%s,%u,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu\n",vector,name,length,
        (unsigned long long)s->edges,(unsigned long long)s->visits,(unsigned long long)s->transition_reads,
        (unsigned long long)s->pdb_reads[0],(unsigned long long)s->pdb_reads[1],(unsigned long long)s->pdb_reads[2],
        (unsigned long long)s->frame_initializations,(unsigned long long)s->path_writes,(unsigned long long)s->pruned,
        (unsigned long long)s->max_comparisons,(unsigned long long)s->threshold_comparisons,
        (unsigned long long)s->rejected_by[0],(unsigned long long)s->rejected_by[1],(unsigned long long)s->rejected_by[2],(unsigned long long)s->iterations);
}
static void check(unsigned p,unsigned a,unsigned b,const char *vector,FILE *out,int total){
    uint8_t moves[11],length;uint64_t edges;
    require(stage2_reference(p,a,b,moves,&length,&edges),"original Stage 2 solve");
    for(unsigned v=0;v<8;v++) {
        s2_workspace w;s2_stats stats;
        require(solvers[v](&tables,p,a,b,&w,&stats),"variant solve");
        require(w.length==length && memcmp(w.moves,moves,length)==0,"identical length and move sequence");
        require(stats.edges==edges,"identical search edges");
        require(stats.transition_reads==3*edges,"three coordinate updates per edge");
        if(total)accumulate(&totals[v],&stats);
        row(out,vector,names[v],&stats,w.length);
    }
}
int main(void){
    load();FILE *input=fopen("target/stage2/distance11.csv","r"),*out=fopen("target/stage3/operations.csv","w");
    require(input && out,"CSV files");char line[256];require(fgets(line,sizeof line,input)!=NULL,"CSV header");
    fprintf(out,"vector,variant,length,edges,visits,transition_reads,pdb_P,pdb_A,pdb_B,frame_initializations,path_writes,pruned,max_comparisons,threshold_comparisons,reject_P,reject_A,reject_B,iterations\n");
    check(0,0,S2_GOAL_B,"12345671111111",out,0);
    while(fgets(line,sizeof line,input)) {
        char vector[15];unsigned rank,p,a,b;
        require(sscanf(line,"%14[^,],%u,%u,%u,%u",vector,&rank,&p,&a,&b)==5,"CSV row");
        check(p,a,b,vector,out,1);++count;
    }
    require(count==2644,"all hard cases");
    for(unsigned v=0;v<8;v++)row(out,"TOTAL_2644",names[v],&totals[v],11);
    require(fclose(input)==0 && fclose(out)==0,"CSV close");
    printf("All 2644 distance-11 states and solved state: all eight variants match original Stage 2 edges, lengths, and exact move sequences.\n");
    for(unsigned v=0;v<8;v++) {
        const s2_stats *s=&totals[v];
        printf("%s edges=%llu pdb_reads=%llu frames=%llu path_writes=%llu pruned=%llu max_comparisons=%llu threshold_comparisons=%llu\n",names[v],
            (unsigned long long)s->edges,(unsigned long long)(s->pdb_reads[0]+s->pdb_reads[1]+s->pdb_reads[2]),
            (unsigned long long)s->frame_initializations,(unsigned long long)s->path_writes,(unsigned long long)s->pruned,
            (unsigned long long)s->max_comparisons,(unsigned long long)s->threshold_comparisons);
    }
    return 0;
}

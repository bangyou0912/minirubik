/* Host C test selection; expected lengths come from the exact BFS oracle. */
#define main baseline_main
#include "../../solver.c"
#undef main
static unsigned distance(state_t s,const uint8_t *oracle){unsigned n=0;for(unsigned r=rank_state(&s);r;r=rank_state(&s)){s=apply_move(s,oracle[r]);if(++n>11)exit(1);}return n;}
static void emit(FILE *f,unsigned rank,unsigned d,int *first){state_t s;unrank_state(rank,&s);char v[15];for(unsigned i=0;i<7;i++){v[i]='1'+s.p[i];v[i+7]='1'+s.o[i];}v[14]=0;fprintf(f,"%s{\"vector\":\"%s\",\"distance\":%u,\"rank\":%u}",*first?"":",\n",v,d,rank);*first=0;}
int main(void){uint8_t diameter,*oracle=build_table(&diameter);if(!oracle||diameter!=11)return 1;FILE*f=fopen("target/stage4/extra-cases.json","w");if(!f)return 1;fprintf(f,"{\"oracle\":\"original C BFS\",\"cases\":[\n");unsigned counts[12]={0},left=34;int first=1;
for(unsigned r=0;r<STATES && left;r++){state_t s;unrank_state(r,&s);unsigned d=distance(s,oracle),need=d?3:1;if(counts[d]<need){emit(f,r,d,&first);counts[d]++;left--;}}
uint32_t seed=0x5a17c0de;for(unsigned i=0;i<48;i++){seed=seed*1664525U+1013904223U;unsigned r=seed%STATES;state_t s;unrank_state(r,&s);emit(f,r,distance(s,oracle),&first);}fprintf(f,"\n]}\n");fclose(f);free(oracle);if(left)return 1;puts("PASS: 34 depth-stratified plus 48 deterministic arbitrary tests derived from BFS");return 0;}

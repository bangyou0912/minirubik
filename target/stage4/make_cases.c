/* Host-only derivation of a short test, independent of any recorded animation. */
#define main baseline_main
#include "../../solver.c"
#undef main
int main(void){
    state_t s={{0,1,2,3,4,5,6},{0}};
    const uint8_t moves[]={0,7,5}; /* R D2 B' */
    for(unsigned i=0;i<3;i++)s=apply_move(s,moves[i]);
    char vector[15];for(unsigned i=0;i<7;i++){vector[i]=(char)('1'+s.p[i]);vector[i+7]=(char)('1'+s.o[i]);}vector[14]=0;
    uint8_t diameter,*table=build_table(&diameter);if(!table || diameter!=11)return 1;
    unsigned distance=0;for(unsigned r=rank_state(&s);r;r=rank_state(&s)){s=apply_move(s,table[r]);if(++distance>11)return 1;}
    free(table);if(distance!=3)return 1;
    FILE *f=fopen("target/stage4/test-cases.json","w");if(!f)return 1;
    fprintf(f,"{\"cases\":[{\"vector\":\"12345671111111\",\"distance\":0},{\"vector\":\"%s\",\"distance\":3,\"scramble\":\"R D2 B'\"},{\"vector\":\"21345671111111\",\"distance\":11}],\"short_distance_verified_by\":\"baseline BFS\"}\n",vector);
    if(fclose(f))return 1;
    printf("Short scramble R D2 B': %s, exact BFS distance %u\n",vector,distance);return 0;
}

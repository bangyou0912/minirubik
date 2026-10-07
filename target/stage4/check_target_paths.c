/* Independent original full-cubie oracle checks the paths printed by Ripes. */
#define main baseline_main
#include "../../solver.c"
#undef main
int main(int argc,char **argv){if(argc!=2)return 1;FILE*f=fopen(argv[1],"r");if(!f)return 1;uint8_t diameter,*oracle=build_table(&diameter);if(!oracle||diameter!=11)return 1;char line[512];unsigned cases=0;
while(fgets(line,sizeof line,f)){char *v=strtok(line," \t\r\n"),*d=strtok(NULL," \t\r\n");if(!v||!d||strlen(v)!=14)return 1;unsigned expected=(unsigned)strtoul(d,NULL,10);state_t s;for(unsigned i=0;i<7;i++){s.p[i]=v[i]-'1';s.o[i]=v[i+7]-'1';}state_t original=s;unsigned exact=0;for(unsigned r=rank_state(&s);r;r=rank_state(&s)){s=apply_move(s,oracle[r]);if(++exact>11)return 1;}if(exact!=expected)return 1;s=original;unsigned count=0,previous=3;char*move;
while((move=strtok(NULL," \t\r\n"))){unsigned m;for(m=0;m<MOVES;m++)if(!strcmp(move,move_names[m]))break;if(m==MOVES||m/3==previous)return 1;previous=m/3;s=apply_move(s,(uint8_t)m);count++;}if(count!=expected||rank_state(&s)!=0)return 1;cases++;}
fclose(f);free(oracle);printf("PASS: %u printed target paths have exact BFS length and solve the original full-cubie model\n",cases);return 0;}

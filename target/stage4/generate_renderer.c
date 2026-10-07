/* Host C renderer geometry and pixel fixtures, independent of target drawing. */
#define main baseline_main
#include "../../solver.c"
#undef main
#include "../stage3/joint.h"
#include <sys/stat.h>
static const unsigned colors[6]={0xffffff,0xff8000,0x00c040,0xff2020,0x2060ff,0xffe000};
/* U,L,F,R,B,D; each corner lists outward normals in one cyclic order. */
static const uint8_t triples[8][3]={{0,1,2},{0,2,3},{5,3,2},{5,2,1},{0,3,4},{5,4,3},{5,1,4},{0,4,1}};
static const uint8_t corners[6][4]={{7,4,0,1},{7,0,6,3},{0,1,3,2},{1,4,2,5},{4,7,5,6},{3,2,6,5}};
static const unsigned bx[6]={9,0,9,18,27,9},by[6]={0,7,7,7,7,14};
static const int xyz[8][3]={{-1,1,1},{1,1,1},{1,-1,1},{-1,-1,1},{1,1,-1},{1,-1,-1},{-1,-1,-1},{-1,1,-1}};
static const int normals[6][3]={{0,1,0},{-1,0,0},{0,0,1},{1,0,0},{0,0,-1},{0,-1,0}};
static unsigned slot(unsigned position,unsigned face){for(unsigned j=0;j<3;j++)if(triples[position][j]==face)return j;exit(1);}
static unsigned sticker(unsigned cubie,unsigned ori,unsigned index){return triples[cubie][(index+3-ori)%3];}
static void rotate(const int v[3],int r[3],unsigned f){if(f==0){r[0]=v[0];r[1]=v[2];r[2]=-v[1];}else if(f==1){r[0]=-v[1];r[1]=v[0];r[2]=v[2];}else{r[0]=v[2];r[1]=v[1];r[2]=-v[0];}}
static void geometry(void){unsigned checks=0;for(unsigned f=0;f<3;f++)for(unsigned pos=1;pos<8;pos++)for(unsigned cub=1;cub<8;cub++)for(unsigned ori=0;ori<3;ori++){
int moved=f==0?xyz[pos][0]==1:f==1?xyz[pos][2]==-1:xyz[pos][1]==-1;int r[3];if(moved)rotate(xyz[pos],r,f);else memcpy(r,xyz[pos],sizeof r);unsigned dest;for(dest=0;dest<8;dest++)if(!memcmp(r,xyz[dest],sizeof r))break;if(!dest||dest==8||source[f][dest-1]!=pos-1)exit(1);unsigned no=(ori+twist[f][dest-1])%3;
for(unsigned j=0;j<3;j++){unsigned face=triples[pos][j];if(moved)rotate(normals[face],r,f);else memcpy(r,normals[face],sizeof r);unsigned nf;for(nf=0;nf<6;nf++)if(!memcmp(r,normals[nf],sizeof r))break;if(nf==6||sticker(cub,ori,j)!=sticker(cub,no,slot(dest,nf)))exit(1);checks++;}}
printf("PASS: %u independent geometric sticker/turn checks\n",checks);}
static void pixels(const state_t *s,uint32_t out[875]){memset(out,0,875*sizeof *out);for(unsigned f=0;f<6;f++)for(unsigned i=0;i<4;i++){unsigned pos=corners[f][i],cub=pos?s->p[pos-1]+1:0,ori=pos?s->o[pos-1]:0;unsigned color=colors[sticker(cub,ori,slot(pos,f))],x=bx[f]+4*(i%2),y=by[f]+3*(i/2);for(unsigned yy=0;yy<3;yy++)for(unsigned xx=0;xx<4;xx++)out[(y+yy)*35+x+xx]=color;}}
static void write_frame(FILE*f,const state_t*s){uint32_t p[875];pixels(s,p);for(unsigned i=0;i<875;i++)for(unsigned b=0;b<4;b++)fputc((p[i]>>(8*b))&255,f);}
int main(void){geometry();FILE*f=fopen("target/stage4/renderer_data.inc","w");if(!f)return 1;fprintf(f,".section .rodata\n.balign 4\nface_palette: .word ");for(unsigned i=0;i<6;i++)fprintf(f,"%s0x%x",i?",":"",colors[i]);fprintf(f,"\ncorner_colors: .byte ");for(unsigned i=0;i<24;i++)fprintf(f,"%s%u",i?",":"",triples[i/3][i%3]);fprintf(f,"\nfacelet_map:\n");for(unsigned face=0;face<6;face++)for(unsigned i=0;i<4;i++)fprintf(f,".byte %u,%u,%u,%u\n",corners[face][i],slot(corners[face][i],face),bx[face]+4*(i%2),by[face]+3*(i/2));fclose(f);mkdir("target/stage4/fixtures",0777);s2_tables tables;f=fopen("target/stage2/tables.bin","rb");if(!f||fread(&tables,1,sizeof tables,f)!=sizeof tables)return 1;fclose(f);
const char *inputs[]={"12345671111111","26471352122222","21345671111111"};const unsigned expected[]={0,3,11};for(unsigned test=0;test<3;test++){state_t s;for(unsigned i=0;i<7;i++){s.p[i]=inputs[test][i]-'1';s.o[i]=inputs[test][i+7]-'1';}s2_workspace w;if(!s2_solve(&tables,rank_state(&s)/729,s2_joint_rank(s.p,s.o,0),s2_joint_rank(s.p,s.o,1),&w,0)||w.length!=expected[test])return 1;char path[256];snprintf(path,sizeof path,"target/stage4/fixtures/%s.bin",inputs[test]);f=fopen(path,"wb");if(!f)return 1;write_frame(f,&s);for(unsigned i=0;i<w.length;i++){s=apply_move(s,w.moves[i]);write_frame(f,&s);}fclose(f);if(rank_state(&s))return 1;printf("Fixture %s: %u frames, including solved final frame\n",inputs[test],w.length+1);}return 0;}

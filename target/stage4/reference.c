/* Freestanding GCC comparison driver, not the hand-written submission.
   Same parser, physical replay and validation must be counted in both builds. */
#include "../stage3/joint.h"
extern const s2_tables search_tables;
extern const char input_vector[];
extern const int32_t expected_length;
static s2_workspace workspace;
static uint8_t p[7],o[7];
static const uint8_t source[3][7]={{1,4,2,0,3,5,6},{0,1,2,4,5,6,3},{0,2,5,3,1,4,6}};
static const uint8_t twist[3][7]={{1,2,0,2,1,0,0},{0,0,0,1,2,1,2},{0,0,0,0,0,0,0}};
static void print_string(const char *text){
    register const char *arg __asm__("a0")=text;
    register unsigned service __asm__("a7")=4;
    __asm__ volatile("ecall" : "+r"(arg) : "r"(service) : "memory");
}
static const char *const move_names[9]={"R ","R2 ","R' ","B ","B2 ","B' ","D ","D2 ","D' "};
static unsigned smaller(unsigned i){unsigned count=0;for(unsigned j=i+1;j<7;j++)count+=p[j]<p[i];return count;}
static unsigned permutation_rank(void){
    unsigned r=smaller(0);r=r*6U+smaller(1);r=r*5U+smaller(2);
    r=r*4U+smaller(3);r=r*3U+smaller(4);return r*2U+smaller(5);
}
static int parse(void){
    unsigned seen=0,sum=0;
    for(unsigned i=0;i<14;i++){
        unsigned c=(unsigned char)input_vector[i];
        if(c<'1' || c>(i<7?'7':'3'))return 0;
        if(i<7){unsigned v=c-'1',bit=1U<<v;if(seen&bit)return 0;seen|=bit;p[i]=(uint8_t)v;}
        else{o[i-7]=(uint8_t)(c-'1');sum+=c-'1';}
    }
    while(sum>=3)sum-=3;
    return input_vector[14]==0 && seen==127 && sum==0;
}
static void quarter(unsigned face){
    uint8_t np[7],no[7];
    for(unsigned i=0;i<7;i++){
        unsigned from=source[face][i],sum=o[from]+twist[face][i];
        np[i]=p[from];no[i]=(uint8_t)(sum>=3?sum-3:sum);
    }
    for(unsigned i=0;i<7;i++){p[i]=np[i];o[i]=no[i];}
}
/* Return a0=length and a1=pass (1), via a two-word result on RV32. */
typedef struct {uint32_t length,pass;} result;
result reference_main(void){
    result failed={0xffffffffU,0};
    if(!parse())return failed;
    unsigned rank=permutation_rank(),a=s2_joint_rank(p,o,0),b=s2_joint_rank(p,o,1);
    if(!s2_solve(&search_tables,rank,a,b,&workspace,0))return failed;
    if(workspace.length>11)return failed;
    if(expected_length>=0 && workspace.length!=(unsigned)expected_length)return failed;
    for(unsigned i=0;i<workspace.length;i++){
        unsigned move=workspace.moves[i];if(move>=9)return failed;print_string(move_names[move]);
        unsigned face=move>=6?2:move>=3?1:0,turns=move-face*3U+1U;
        for(unsigned turn=0;turn<turns;turn++)quarter(face);
    }
    print_string("\n");
    for(unsigned i=0;i<7;i++)if(p[i]!=i || o[i]!=0)return failed;
    result passed={workspace.length,1};return passed;
}



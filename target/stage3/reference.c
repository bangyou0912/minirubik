#include <stdio.h>
#include "../stage2/joint.h"
#include <string.h>
int stage2_reference(unsigned p,unsigned a,unsigned b,uint8_t moves[11],uint8_t *length,uint64_t *edges) {
    static s2_tables tables;static int ready;
    if(!ready) {
        FILE *f; /* stdio is supplied by the compilation unit below */
        f=fopen("target/stage2/tables.bin","rb");if(!f)return 0;
        for(unsigned face=0;face<3;face++)for(unsigned i=0;i<S2_PERM;i++) {
            int lo=fgetc(f),hi=fgetc(f);if(lo<0 || hi<0)return 0;tables.perm_next[face][i]=(uint16_t)(lo|(hi<<8));
        }
        for(unsigned face=0;face<3;face++)for(unsigned i=0;i<S2_JOINT;i++) {
            int lo=fgetc(f),hi=fgetc(f);if(lo<0 || hi<0)return 0;tables.joint_next[face][i]=(uint16_t)(lo|(hi<<8));
        }
        if(fread(tables.perm_distance,1,S2_PERM,f)!=S2_PERM || fread(tables.joint_distance,1,2*S2_JOINT,f)!=2*S2_JOINT || fclose(f))return 0;
        ready=1;
    }
    s2_workspace workspace;s2_stats stats;
    if(!s2_solve(&tables,p,a,b,&workspace,&stats))return 0;
    memcpy(moves,workspace.moves,workspace.length);*length=workspace.length;*edges=stats.edges;return 1;
}


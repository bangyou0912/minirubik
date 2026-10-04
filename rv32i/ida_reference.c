/* C reference model of the IDA* search used by the RV32I solver.
 *
 * It mirrors the assembly version step by step so the two can be compared
 * on the same input: same move numbering as solver.c, same pattern-database
 * heuristic (max of the three PDBs), same explicit stack instead of
 * recursion. Input parsing and LED Matrix output stay in the assembly code.
 */
#include "search_tables_c.h"

typedef struct {
    cube_u16 perm;
    cube_u16 joint_a;
    cube_u16 joint_b;
    cube_u8 next_move;
    cube_u8 previous_face;
} ida_frame_c;

/* The deepest frame pushed is bound - 1 <= 10, so 11 frames are enough. */
static ida_frame_c ida_frames_c[11];

static cube_u8 ida_heuristic_c(cube_u16 perm, cube_u16 joint_a,
                                cube_u16 joint_b)
{
    cube_u8 h = perm_pdb_c[perm];
    if (joint_a_pdb_c[joint_a] > h)
        h = joint_a_pdb_c[joint_a];
    if (joint_b_pdb_c[joint_b] > h)
        h = joint_b_pdb_c[joint_b];
    return h;
}

/* Return an optimal HTM length from zero through eleven, or -1 on failure.
 * The caller supplies eleven move bytes. Move numbering matches solver.c.
 */
int ida_solve_c(cube_u16 perm, cube_u16 joint_a, cube_u16 joint_b,
                cube_u8 solution[11])
{
    cube_u8 bound = ida_heuristic_c(perm, joint_a, joint_b);
    if (bound == 0)
        return 0;
    if (bound > 11)
        return -1;

    ida_frames_c[0].perm = perm;
    ida_frames_c[0].joint_a = joint_a;
    ida_frames_c[0].joint_b = joint_b;
    ida_frames_c[0].previous_face = 3; /* no face yet */

    for (; bound <= 11; ++bound) {
        cube_u8 depth = 0;
        ida_frames_c[0].next_move = 0;

        for (;;) {
            ida_frame_c *frame = &ida_frames_c[depth];
            if (frame->next_move >= 9) {
                if (depth == 0)
                    break;
                --depth;
                continue;
            }

            /* Decode with compares instead of move / 3 and move % 3:
             * the RV32I base ISA has no divide instruction. */
            cube_u8 move = frame->next_move++;
            cube_u8 face;
            cube_u8 turns;
            if (move < 3) {
                face = 0;
                turns = (cube_u8)(move + 1);
            } else if (move < 6) {
                face = 1;
                turns = (cube_u8)(move - 2);
            } else {
                face = 2;
                turns = (cube_u8)(move - 5);
            }
            if (face == frame->previous_face)
                continue;

            cube_u16 next_perm = frame->perm;
            cube_u16 next_a = frame->joint_a;
            cube_u16 next_b = frame->joint_b;
            for (cube_u8 turn = 0; turn < turns; ++turn) {
                next_perm = perm_transition_c[next_perm][face];
                next_a = joint_a_transition_c[next_a][face];
                next_b = joint_b_transition_c[next_b][face];
            }

            cube_u8 h = ida_heuristic_c(next_perm, next_a, next_b);
            cube_u8 child_depth = (cube_u8)(depth + 1);
            if (child_depth + h > bound)
                continue;
            solution[depth] = move;
            if (h == 0)
                return child_depth;

            /* Here h >= 1, so child_depth < bound <= 11: no extra depth
             * check is needed before pushing. */
            ida_frame_c *child = &ida_frames_c[child_depth];
            child->perm = next_perm;
            child->joint_a = next_a;
            child->joint_b = next_b;
            child->next_move = 0;
            child->previous_face = face;
            depth = child_depth;
        }
    }
    return -1;
}

# Cross-Substrate Skill Transfer

Does a skill the system DISCOVERS on one substrate enable solving on a
DIFFERENT substrate whose native vocabulary CANNOT express it? Two
vocabularies over one universal VM: A (arithmetic) vs B (structure, no
ADD/MUL/INC). A learns skills; three B-arms attempt held-out targets.

## Result (n = 11 seeds; 4 arithmetic + 3 structure held-out tasks)

| Arm | ARITH /4 | STRUCT /3 |
|---|---|---|
| B_alone | 0.00 (floor — no arithmetic) | 3.00 |
| B_rand (random A-programs) | 1.00 | — |
| B_skill (learned skills) | 2.00 | 3.00 |

- Transfer (B_skill − B_alone): **+2.00, perm-p = 0.0008**
- Learning premium (B_skill − B_rand): **+1.00, perm-p = 0.014**
- Control: STRUCT tasks tie 3/3 across arms (boost is specific).

Honest boundary: direct behavioural transfer works (double, sumall);
compositional transfer (double_max, inc_min) solved by no arm — a skill
*emits* its output rather than leaving values on the stack, so it does not
chain into a native reduction. Reproduce: `python3 src/transferforge.py run 1 11 300`.

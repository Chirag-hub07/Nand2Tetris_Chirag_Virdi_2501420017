// Test for K=17 extra feature: duplicate label warning
// The label (LOOP) is written twice, so the assembler must warn.
@0
D=M
(LOOP)
@1
D=D+M
@LOOP
D;JGT
(LOOP)
@2
M=D
(END)
@END
0;JMP
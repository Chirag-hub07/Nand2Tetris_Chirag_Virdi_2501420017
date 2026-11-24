// Box.asm  --  Capstone Part C  (K = 17)
// While any key is pressed, a black box is drawn; when released it is erased.
//
//   start row : K            = 17
//   height    : 20 rows
//   width     : 16*((17 mod 4)+1) = 32 pixels = 2 words, from the left edge
//   first word: SCREEN + 32*17 = 16384 + 544 = 16928
//
// Variables:  shade (colour word), ptr (current row address), rowsLeft (counter)

(MAIN)
    @KBD
    D=M
    @PRESSED
    D;JNE           // key down -> go set black
    @shade
    M=0             // no key -> white
    @PAINT
    0;JMP

(PRESSED)
    @shade
    M=-1            // all 16 bits = 1 -> black

(PAINT)
    @16928          // address of first word of row 17
    D=A
    @ptr
    M=D
    @20
    D=A
    @rowsLeft
    M=D

(ROWLOOP)
    @shade
    D=M
    @ptr
    A=M
    M=D             // left word of this row
    A=A+1
    M=D             // second word of this row (32 pixels wide)
    @32
    D=A
    @ptr
    M=D+M           // move down one row (+32 words)
    @rowsLeft
    MD=M-1
    @ROWLOOP
    D;JGT
    @MAIN
    0;JMP
; Small Theft Auto - the three inner loops of the renderer, hand-written for the
; ATmega32U4. Each has a plain C++ twin in engine.h (ground_c, wall_c, dda_c)
; that defines what it must do; SELFTEST builds run both and compare.
;
;   ground_asm   textured ground pixels of one screen column
;   wall_asm     textured wall pixels of one wall segment
;   dda_asm      walk a ray through the city grid until something interesting
;
; Column scratch buffer: colbuf[0..7] = high bit plane, colbuf[8..15] = low bit
; plane, bit 0 of each byte is the top row of that byte.

#include <avr/io.h>
#include "consts.h"

.section .text

; ------------------------------------------------------------------ ground
; void ground_asm(uint8_t y0, int16_t rx, int16_t ry)
;   y0 r24, rx r23:r22, ry r21:r20      fills rows y0 .. ROWS-1
;
;   r2       zero                  r10      pixels left
;   r3       multiply scratch      r11      bit mask of the current row
;   r4:r5    depth table pointer   r12 r13  high / low plane byte being built
;   r6:r7    camera x              r14:r15  ground tile of the current cell
;   r8:r9    camera y              r16:r17  ray direction x      r18:r19  y
;   r20:r21  depth / scratch       r22:r23  world x   r24:r25  world y
;   r26 r27  cell of the previous pixel     Y  column buffer     Z  scratch
.global ground_asm
ground_asm:
    push r2
    push r3
    push r4
    push r5
    push r6
    push r7
    push r8
    push r9
    push r10
    push r11
    push r12
    push r13
    push r14
    push r15
    push r16
    push r17
    push r28
    push r29

    clr  r2
    movw r16, r22
    movw r18, r20
    lds  r6, view_x
    lds  r7, view_x + 1
    lds  r8, view_y
    lds  r9, view_y + 1

    ldi  r30, ROWS
    sub  r30, r24
    mov  r10, r30

    mov  r28, r24
    lsr  r28
    lsr  r28
    lsr  r28
    clr  r29
    subi r28, lo8(-(colbuf))
    sbci r29, hi8(-(colbuf))
    ld   r12, Y
    ldd  r13, Y+8

    mov  r30, r24
    andi r30, 7
    ldi  r31, 1
    mov  r11, r31
    tst  r30
    breq 2f
1:  lsl  r11
    dec  r30
    brne 1b
2:
    mov  r30, r24
    subi r30, HORIZON + 1
    lsl  r30
    clr  r31
    subi r30, lo8(-(GROUND_T4))
    sbci r31, hi8(-(GROUND_T4))
    movw r4, r30
    set                                 ; T = "no cell looked up yet"

g_loop:
    movw r30, r4
    lpm  r20, Z+
    lpm  r21, Z+
    movw r4, r30

    ; world x = camera x + high word of (direction x * depth)
    mul   r16, r20
    mov   r3, r1
    mulsu r17, r21
    movw  r22, r0
    mulsu r17, r20
    sbc   r23, r2
    add   r3, r0
    adc   r22, r1
    adc   r23, r2
    mul   r16, r21
    add   r3, r0
    adc   r22, r1
    adc   r23, r2
    add   r22, r6
    adc   r23, r7

    ; world y
    mul   r18, r20
    mov   r3, r1
    mulsu r19, r21
    movw  r24, r0
    mulsu r19, r20
    sbc   r25, r2
    add   r3, r0
    adc   r24, r1
    adc   r25, r2
    mul   r18, r21
    add   r3, r0
    adc   r24, r1
    adc   r25, r2
    add   r24, r8
    adc   r25, r9

    brts g_newcell
    cp   r23, r26
    brne g_newcell
    cp   r25, r27
    brne g_newcell
    rjmp g_texel

g_newcell:
    clt
    mov  r26, r23
    mov  r27, r25
    ; is it in the near window?
    mov  r20, r23
    lds  r21, win_x0
    sub  r20, r21
    mov  r21, r25
    lds  r0, win_y0
    sub  r21, r0
    mov  r0, r20
    or   r0, r21
    ldi  r30, 0xF0
    and  r0, r30
    brne g_far
    swap r21
    or   r21, r20
    ldi  r30, lo8(win)
    ldi  r31, hi8(win)
    add  r30, r21
    adc  r31, r2
    ld   r20, Z
    rjmp g_havecell
g_far:
    push r18
    push r19
    push r22
    push r23
    push r24
    push r25
    push r26
    push r27
    clr  r1
    mov  r22, r25
    mov  r24, r23
    call cell_far_c
    mov  r20, r24
    pop  r27
    pop  r26
    pop  r25
    pop  r24
    pop  r23
    pop  r22
    pop  r19
    pop  r18
g_havecell:
    sbrc r20, 7
    rjmp g_plain                        ; a building cell seen from outside: treat as road
    mov  r30, r20
    clr  r31
    subi r30, lo8(-(GTILE_LUT))
    sbci r31, hi8(-(GTILE_LUT))
    lpm  r21, Z
    mov  r30, r20
    andi r30, 0xF3
    cpi  r30, 0x22                      ; dashed lane line: drawn in every other cell only
    brne g_settile
    mov  r30, r25
    sbrc r20, 2
    mov  r30, r23
    sbrs r30, 0
    rjmp g_settile
g_plain:
    ldi  r21, TILE_PLAIN_ROAD
g_settile:
    ldi  r30, 16
    mul  r21, r30
    movw r14, r0
    ldi  r30, lo8(GTILES)
    ldi  r31, hi8(GTILES)
    add  r14, r30
    adc  r15, r31

g_texel:
    mov  r30, r24                       ; texel row: two bytes (high bits, low bits)
    swap r30
    andi r30, 0x0E
    clr  r31
    add  r30, r14
    adc  r31, r15
    lpm  r0, Z+
    lpm  r1, Z
    mov  r30, r22                       ; texel column -> bit mask
    swap r30
    lsr  r30
    andi r30, 0x07
    clr  r31
    subi r30, lo8(-(BITMASK))
    sbci r31, hi8(-(BITMASK))
    lpm  r30, Z
    and  r0, r30
    breq 3f
    or   r12, r11
3:  and  r1, r30
    breq 4f
    or   r13, r11
4:  lsl  r11
    brne 5f
    st   Y, r12
    std  Y+8, r13
    adiw r28, 1
    ld   r12, Y
    ldd  r13, Y+8
    inc  r11
5:  dec  r10
    breq 6f
    rjmp g_loop
6:
    st   Y, r12
    std  Y+8, r13
    clr  r1
    pop  r29
    pop  r28
    pop  r17
    pop  r16
    pop  r15
    pop  r14
    pop  r13
    pop  r12
    pop  r11
    pop  r10
    pop  r9
    pop  r8
    pop  r7
    pop  r6
    pop  r5
    pop  r4
    pop  r3
    pop  r2
    ret

; ------------------------------------------------------------------ wall
; void wall_asm(uint8_t y0, uint8_t n)
;   y0 r24, n r22      draws n pixels downwards from row y0 using wall_job:
;     +0 lv[4]   level for texel codes 0..3        +8  top     index of the top floor
;     +4 texm    texture column, upper floors      +9  zstep   cells per pixel, 0.16
;     +6 texg    texture column, ground floor      +11 z       height of first pixel, 8.16
;
;   r16:r17:r18  height z            r2 r3    texel (key) of the previous pixel
;   r20:r21      zstep               r4:r5    texm     r6:r7  texg     r8  top
;   r19          pixels left         r9       zero
;   r23          row bit mask        r24 r25  plane bytes being built
;   r26 r27      0x00 / 0xFF per plane for the current texel
.global wall_asm
wall_asm:
    push r2
    push r3
    push r4
    push r5
    push r6
    push r7
    push r8
    push r9
    push r16
    push r17
    push r28
    push r29

    clr  r9
    mov  r19, r22
    mov  r28, r24
    lsr  r28
    lsr  r28
    lsr  r28
    clr  r29
    subi r28, lo8(-(colbuf))
    sbci r29, hi8(-(colbuf))
    mov  r30, r24
    andi r30, 7
    ldi  r23, 1
    tst  r30
    breq 2f
1:  lsl  r23
    dec  r30
    brne 1b
2:
    ld   r24, Y
    ldd  r25, Y+8
    lds  r4, wall_job + 4
    lds  r5, wall_job + 5
    lds  r6, wall_job + 6
    lds  r7, wall_job + 7
    lds  r8, wall_job + 8
    lds  r20, wall_job + 9
    lds  r21, wall_job + 10
    lds  r16, wall_job + 11
    lds  r17, wall_job + 12
    lds  r18, wall_job + 13
    ldi  r30, 1                         ; a key no pixel can have (low bits are masked off)
    mov  r2, r30
    clr  r3
    clr  r26
    clr  r27

w_loop:
    mov  r22, r17
    andi r22, 0xE0
    cp   r22, r2
    cpc  r18, r3
    breq w_same
    mov  r2, r22
    mov  r3, r18
    mov  r30, r17                       ; texel row: 7 - (fraction >> 5)
    swap r30
    lsr  r30
    andi r30, 7
    ldi  r31, 7
    sub  r31, r30
    mov  r30, r18                       ; floor number
    sbrs r30, 7
    rjmp 1f
    clr  r30                            ; rounding took us just below the ground
    ldi  r31, 7
1:  cp   r30, r8
    brlo 2f
    tst  r31
    brne 2f
    ldi  r22, 2                         ; top edge of the top floor: a ledge
    rjmp 5f
2:  mov  r22, r31
    tst  r30
    movw r30, r4
    brne 3f
    movw r30, r6
3:  mov  r0, r22
    lsr  r0
    add  r30, r0
    adc  r31, r9
    lpm  r0, Z
    sbrc r22, 0
    swap r0
    mov  r22, r0
    andi r22, 0x0F
5:  mov  r30, r22
    clr  r31
    subi r30, lo8(-(wall_job))
    sbci r31, hi8(-(wall_job))
    ld   r22, Z
    clr  r26
    clr  r27
    sbrc r22, 1
    ser  r26
    sbrc r22, 0
    ser  r27
w_same:
    mov  r22, r23
    and  r22, r26
    or   r24, r22
    mov  r22, r23
    and  r22, r27
    or   r25, r22
    lsl  r23
    brne 6f
    st   Y, r24
    std  Y+8, r25
    adiw r28, 1
    ld   r24, Y
    ldd  r25, Y+8
    ldi  r23, 1
6:  sub  r16, r20
    sbc  r17, r21
    sbc  r18, r9
    dec  r19
    breq 7f
    rjmp w_loop
7:
    st   Y, r24
    std  Y+8, r25
    pop  r29
    pop  r28
    pop  r17
    pop  r16
    pop  r9
    pop  r8
    pop  r7
    pop  r6
    pop  r5
    pop  r4
    pop  r3
    pop  r2
    ret

; ------------------------------------------------------------------ ray walk
; uint8_t dda_asm(void)
;   Walks the ray in the dda block from cell to cell until it enters a building
;   taller than any seen so far on this ray (returns 1), or reaches the edge of
;   the world or the view distance (returns 0).
;     +0 tmx  +2 tmy   depth of the next x / y grid line     +8 ix  +9 iy
;     +4 tdx  +6 tdy   depth between grid lines              +10 sx +11 sy
;     +12 hmax         +13 t (depth of the crossing)  +15 side  +16 cell
;
;   r18:r19 tmx  r20:r21 tmy  r22:r23 tdx  r24:r25 tdy  r26 ix  r27 iy
;   r16:r17 t    r2 r3 near window origin    r4 sx  r5 sy  r6 side  r7 0xF0
.global dda_asm
dda_asm:
    push r2
    push r3
    push r4
    push r5
    push r6
    push r7
    push r16
    push r17

    lds  r18, dda + 0
    lds  r19, dda + 1
    lds  r20, dda + 2
    lds  r21, dda + 3
    lds  r22, dda + 4
    lds  r23, dda + 5
    lds  r24, dda + 6
    lds  r25, dda + 7
    lds  r26, dda + 8
    lds  r27, dda + 9
    lds  r4, dda + 10
    lds  r5, dda + 11
    lds  r2, win_x0
    lds  r3, win_y0
    ldi  r30, 0xF0
    mov  r7, r30
    rjmp d_step

d_far:
    lds  r0, win_x0 + 1
    mov  r30, r26
    sub  r30, r0
    lds  r0, win_y0 + 1
    mov  r31, r27
    sub  r31, r0
    mov  r0, r30
    or   r0, r31
    and  r0, r7
    breq 1f
    rjmp d_flash
1:
    swap r31
    or   r30, r31
    clr  r31
    subi r30, lo8(-(win + 256))
    sbci r31, hi8(-(win + 256))
    ld   r0, Z
    rjmp d_have

d_step:
    cp   r18, r20
    cpc  r19, r21
    brsh d_ystep
    movw r16, r18
    add  r18, r22
    adc  r19, r23
    add  r26, r4
    clr  r6
    rjmp d_cell
d_ystep:
    movw r16, r20
    add  r20, r24
    adc  r21, r25
    add  r27, r5
    clr  r6
    inc  r6
d_cell:
    cpi  r17, MAXD_CELLS
    brsh d_end
    mov  r30, r26
    sub  r30, r2
    mov  r31, r27
    sub  r31, r3
    mov  r0, r30
    or   r0, r31
    and  r0, r7
    brne d_far
    swap r31
    or   r30, r31
    clr  r31
    subi r30, lo8(-(win))
    sbci r31, hi8(-(win))
    ld   r0, Z
d_have:
    sbrs r0, 7
    rjmp d_step                         ; open ground: keep walking
    mov  r30, r0
    cpi  r30, CELL_EDGE
    breq d_edge
    lsr  r30
    lsr  r30
    lsr  r30
    andi r30, 0x0F
    inc  r30
    lds  r31, dda + 12
    cp   r31, r30
    brsh d_step                         ; not taller than what is already in front
    sts  dda + 12, r30
    rcall d_save
    ldi  r24, 1
    rjmp d_ret
d_edge:
d_end:
    rcall d_save
    ldi  r24, 0
d_ret:
    pop  r17
    pop  r16
    pop  r7
    pop  r6
    pop  r5
    pop  r4
    pop  r3
    pop  r2
    ret

d_save:
    sts  dda + 0, r18
    sts  dda + 1, r19
    sts  dda + 2, r20
    sts  dda + 3, r21
    sts  dda + 8, r26
    sts  dda + 9, r27
    sts  dda + 13, r16
    sts  dda + 14, r17
    sts  dda + 15, r6
    sts  dda + 16, r0
    ret

d_flash:
    push r18
    push r19
    push r20
    push r21
    push r22
    push r23
    push r24
    push r25
    push r26
    push r27
    mov  r24, r26
    mov  r22, r27
    call cell_flash_c
    mov  r0, r24
    pop  r27
    pop  r26
    pop  r25
    pop  r24
    pop  r23
    pop  r22
    pop  r21
    pop  r20
    pop  r19
    pop  r18
    rjmp d_have

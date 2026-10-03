; Small Theft Auto - display refresh interrupt (ATmega32U4, 16 MHz, SPI at 8 MHz).
;
; Runs 156 times a second. Each run sends one 1-bit plane of the picture and
; lets the panel do exactly one scan of it:
;
;   1. HUD strip (128 bytes)       -> bottom 8 rows; the last row is kept black
;   2. command A8 3F               -> panel leaves its parked row and scans once
;   3. 3D view (7 pages x 128)     -> built on the fly from the two bit planes
;   4. command A8 00               -> panel parks again when the scan is done
;
; The 3D view is stored as two bit planes (hi, lo), level = 2*hi + lo. One
; plane in three is lit where level >= 2 (hi), one where level >= 1 (hi|lo),
; one where level == 3 (hi&lo). Every column is sent twice: view pixels are
; 2 wide.
;
; With disp_wide set the same memory is a page in black and white, 128 dots
; wide (title, map, settings): of every two columns on the screen the left one
; comes from hi, the right one from lo, the same in all three planes.
;
; With disp_nav set the way to go is shown at the top of the 3D view, in
; single dots, black and white:
;   the arrow     NAV_ARROW_COLS columns of the view from NAV_C0, 16 rows. It
;                 is laid over the view: nav_over holds, for every column of
;                 dots, what to keep of the view and what to light up
;   the distance  NAV_BOX_COLS columns from NAV_BOX_C0, 8 rows, taken from
;                 the picture the way a page is: left dots hi, right dots lo
;
; With disp_mono set the picture is shown in two shades, for panels that do
; not keep in step (the FX-C is said to be one). Every third run sends it,
; the other two only count the clock. Level 3 is lit and level 0 dark as
; before; the two levels in between are patterns over the two panel dots of
; a view dot and two rows: level 2 a checkerboard, level 1 one dot in four
; (the top left one). The panel is not parked then: disp_park says 64 rows
; as well, so it scans by itself as it does for any other game.
;
; Bytes go out back to back with no waiting on the SPI flag: one byte every 18
; CPU cycles, which is as fast as the hardware can shift them (a little slower
; does no harm, and happens where one run of columns ends and the next one
; begins). Data is sent least significant bit first because the panel counts
; rows from the bottom.

#include <avr/io.h>
#include "consts.h"

#define rZERO  r18
#define rPAGE  r19
#define rPLANE r20
#define rCOL   r21
#define rDOTS  r22

.section .text

delay7:                                 ; rcall (3) + ret (4)
    ret

; rCOL columns of the 3D view, from X (hi) and Y (lo), in the plane that is
; due: bit 0 of rPLANE says hi|lo, bit 1 hi&lo, neither hi. Whichever it is
; takes the same time: an instruction that is skipped costs what it would have.
; With rPLANE 3 (two shades) mono_run does the work.
view_run:
    cpi  rPLANE, 3
    brne 1f
    rjmp mono_run
1:  ld   r24, X                         ; 2
    ld   r25, Y                         ; 2
    sbrc rPLANE, 0                      ; 1, or 2 when it skips
    or   r24, r25                       ; 1
    sbrc rPLANE, 1                      ; 1, or 2
    and  r24, r25                       ; 1
    out  _SFR_IO_ADDR(SPDR), r24        ; 1   first copy
    adiw r26, COLBYTES                  ; 2
    adiw r28, COLBYTES                  ; 2
    rcall delay7                        ; 7
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2   (17 since the write)
    out  _SFR_IO_ADDR(SPDR), r24        ; 1   second copy
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2
    dec  rCOL                           ; 1
    brne 1b                             ; 2   (+8 at the loop top = 17)
    ret

; the same for a page: hi is the left column of dots, lo the right one
wide_run:
1:  ld   r24, X                         ; 2
    ld   r25, Y                         ; 2
    nop                                 ; 1
    out  _SFR_IO_ADDR(SPDR), r24        ; 1   left column
    adiw r26, COLBYTES                  ; 2
    adiw r28, COLBYTES                  ; 2
    rcall delay7                        ; 7
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2   (17 since the write)
    out  _SFR_IO_ADDR(SPDR), r25        ; 1   right column
    rcall delay7                        ; 7
    rjmp .+0                            ; 2
    dec  rCOL                           ; 1
    brne 1b                             ; 2   (+5 at the loop top = 17)
    ret

; the view with something laid over it: for every column of the view four
; bytes at Z, what to keep of the view and what to light up, for the left
; column of dots and for the right one
over_run:
    cpi  rPLANE, 3
    brne 1f
    rjmp mono_over_run
1:  ld   r24, X                         ; 2
    ld   r25, Y                         ; 2
    sbrc rPLANE, 0                      ; 1, or 2
    or   r24, r25                       ; 1
    sbrc rPLANE, 1                      ; 1, or 2
    and  r24, r25                       ; 1
    mov  r25, r24                       ; 1
    ld   rDOTS, Z+                      ; 2
    and  r25, rDOTS                     ; 1
    ld   rDOTS, Z+                      ; 2
    or   r25, rDOTS                     ; 1
    out  _SFR_IO_ADDR(SPDR), r25        ; 1   left column
    adiw r26, COLBYTES                  ; 2
    adiw r28, COLBYTES                  ; 2
    ld   rDOTS, Z+                      ; 2
    and  r24, rDOTS                     ; 1
    ld   rDOTS, Z+                      ; 2
    or   r24, rDOTS                     ; 1
    rcall delay7                        ; 7   (17 since the write)
    out  _SFR_IO_ADDR(SPDR), r24        ; 1   right column
    dec  rCOL                           ; 1
    brne 1b                             ; 2   (+15 at the loop top = 18)
    ret

; rCOL columns of the view in two shades: level 3 lit in both panel dots, level
; 2 the top left and bottom right of the four dots of two rows, level 1 the
; top left one. r23 holds level 3, rDOTS the left column, r25 the right one.
mono_run:
1:  ld   r24, X                         ; 2   hi
    ld   r25, Y                         ; 2   lo
    mov  r23, r24                       ; 1
    and  r23, r25                       ; 1   level 3
    mov  rDOTS, r24                     ; 1
    eor  rDOTS, r25                     ; 1   levels 1 and 2
    mov  r25, rDOTS                     ; 1
    and  r25, r24                       ; 1   level 2 alone
    andi rDOTS, 0x55                    ; 1   levels 1 and 2 in the even rows of the left column
    or   rDOTS, r23                     ; 1
    out  _SFR_IO_ADDR(SPDR), rDOTS      ; 1   left column
    andi r25, 0xAA                      ; 1   level 2 in the odd rows of the right column
    or   r25, r23                       ; 1
    adiw r26, COLBYTES                  ; 2
    adiw r28, COLBYTES                  ; 2
    rcall delay7                        ; 7
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2   (17 since the write)
    out  _SFR_IO_ADDR(SPDR), r25        ; 1   right column
    rjmp .+0                            ; 2
    dec  rCOL                           ; 1
    brne 1b                             ; 2   (+12 at the loop top = 17)
    ret

; the same with something laid over it, as over_run has it (a few cycles
; slower than the bus needs, which does no harm)
mono_over_run:
1:  ld   r24, X                         ; 2
    ld   r25, Y                         ; 2
    mov  r23, r24                       ; 1
    and  r23, r25                       ; 1   level 3
    mov  rDOTS, r24                     ; 1
    eor  rDOTS, r25                     ; 1   levels 1 and 2
    mov  r25, rDOTS                     ; 1
    and  r25, r24                       ; 1   level 2 alone
    andi rDOTS, 0x55                    ; 1
    or   rDOTS, r23                     ; 1   the left column of the view
    ld   r24, Z+                        ; 2
    and  rDOTS, r24                     ; 1   what to keep of it
    ld   r24, Z+                        ; 2
    or   rDOTS, r24                     ; 1   and what to light up
    out  _SFR_IO_ADDR(SPDR), rDOTS      ; 1   left column
    andi r25, 0xAA                      ; 1
    or   r25, r23                       ; 1   the right column of the view
    ld   r24, Z+                        ; 2
    and  r25, r24                       ; 1
    ld   r24, Z+                        ; 2
    or   r25, r24                       ; 1
    adiw r26, COLBYTES                  ; 2
    adiw r28, COLBYTES                  ; 2
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2
    nop                                 ; 1   (17 since the write)
    out  _SFR_IO_ADDR(SPDR), r25        ; 1   right column
    dec  rCOL                           ; 1
    brne 1b                             ; 2   (+18 at the loop top = 21)
    ret

; the same, second byte taken from memory
.macro COMMAND_VAR b0 var
    rcall delay7
    rcall delay7
    rjmp .+0                            ; 16 + cbi
    cbi  _SFR_IO_ADDR(PORTD), 4         ; command mode
    ldi  r24, \b0
    out  _SFR_IO_ADDR(SPDR), r24
    rcall delay7
    rcall delay7
    nop
    lds  r24, \var                      ; 17 since the write
    out  _SFR_IO_ADDR(SPDR), r24
    rcall delay7
    rcall delay7
    rjmp .+0
    nop
    sbi  _SFR_IO_ADDR(PORTD), 4         ; data mode
.endm

.global TIMER3_COMPA_vect
TIMER3_COMPA_vect:
    push r24
    in   r24, _SFR_IO_ADDR(SREG)
    push r24
    push r25
    push rZERO
    push rPAGE
    push rPLANE
    push rCOL
    push rDOTS
    push r23
    push r26
    push r27
    push r28
    push r29
    push r30
    push r31
    clr  rZERO
    lds  rPLANE, disp_plane
    lds  r24, disp_mono
    tst  r24
    breq 1f                             ; four shades: every run sends one plane of three
    tst  rPLANE
    breq 0f
    rjmp .Lclock                        ; two shades: the picture goes out every third run, the others only count
0:  ldi  rPLANE, 3                      ; what the routines take as "two shades"

1:  cbi  _SFR_IO_ADDR(PORTD), 6         ; select the display
    ldi  r24, (1<<SPE)|(1<<MSTR)|(1<<DORD)
    out  _SFR_IO_ADDR(SPCR), r24

    ; ---- HUD strip -------------------------------------------------------
    ldi  r26, lo8(hud)
    ldi  r27, hi8(hud)
    ldi  r25, 128
2:  ld   r24, X+                        ; 2
    andi r24, 0x7F                      ; 1   bottom row is the park row
    out  _SFR_IO_ADDR(SPDR), r24        ; 1
    rcall delay7                        ; 7
    rjmp .+0                            ; 2
    rjmp .+0                            ; 2
    dec  r25                            ; 1
    brne 2b                             ; 2   = 18

    COMMAND_VAR 0x15, disp_release      ; A8 3F, bit-reversed

    ; ---- 3D view, bottom page first ---------------------------------------
    ldi  rPAGE, COLBYTES
3:  ldi  r26, lo8(fb_hi - 1)
    ldi  r27, hi8(fb_hi - 1)
    add  r26, rPAGE
    adc  r27, rZERO
    ldi  r28, lo8(fb_lo - 1)
    ldi  r29, hi8(fb_lo - 1)
    add  r28, rPAGE
    adc  r29, rZERO
    ldi  rCOL, COLS
    lds  r24, disp_wide
    tst  r24
    breq 4f
    rcall wide_run                      ; a page: all of it black and white
    rjmp 7f
4:  lds  r24, disp_nav                  ; 0, or 3: the two pages at the top hold the way to go
    cp   rPAGE, r24
    brsh 6f
    ldi  rCOL, NAV_C0                   ; the view up to the arrow
    rcall view_run
    ldi  r30, lo8(nav_over)
    ldi  r31, hi8(nav_over)
    ldi  rCOL, NAV_ARROW_COLS
    cpi  rPAGE, 1
    breq 5f
    adiw r30, NAV_ARROW_BYTES / 2       ; the lower half of the arrow,
    rcall over_run
    ldi  rCOL, COLS - NAV_C0 - NAV_ARROW_COLS
    rjmp 6f                             ; and nothing else in these 8 rows
5:  rcall over_run                      ; the upper half of the arrow,
    ldi  rCOL, NAV_BOX_C0 - NAV_C0 - NAV_ARROW_COLS
    rcall view_run
    ldi  rCOL, NAV_BOX_COLS             ; the distance next to it
    rcall wide_run
    ldi  rCOL, COLS - NAV_BOX_C0 - NAV_BOX_COLS
6:  rcall view_run                      ; (the rest of) the view
7:  dec  rPAGE
    breq 8f
    rjmp 3b
8:
    COMMAND_VAR 0x15, disp_park         ; A8 00

    ldi  r24, (1<<SPE)|(1<<MSTR)
    out  _SFR_IO_ADDR(SPCR), r24
    sbi  _SFR_IO_ADDR(PORTD), 6         ; release the display
    ; this routine never looks at the "transfer done" flag, so it is left set;
    ; clear it (read status, then data) or the flash code would trust a stale flag
    in   r24, _SFR_IO_ADDR(SPSR)
    in   r24, _SFR_IO_ADDR(SPDR)

    ; ---- next plane, frame clock -------------------------------------------
.Lclock:
    lds  rPLANE, disp_plane
    inc  rPLANE
    cpi  rPLANE, 3
    brlo 9f
    clr  rPLANE
9:  sts  disp_plane, rPLANE
    lds  r24, plane_ticks
    lds  r25, plane_ticks + 1
    adiw r24, 1
    sts  plane_ticks + 1, r25
    sts  plane_ticks, r24

    pop  r31
    pop  r30
    pop  r29
    pop  r28
    pop  r27
    pop  r26
    pop  r23
    pop  rDOTS
    pop  rCOL
    pop  rPLANE
    pop  rPAGE
    pop  rZERO
    pop  r25
    pop  r24
    out  _SFR_IO_ADDR(SREG), r24
    pop  r24
    reti

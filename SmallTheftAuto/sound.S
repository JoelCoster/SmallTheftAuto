; Small Theft Auto - sound interrupt (timer 4 overflow: the start of every period).
;
; Rolls the dice for the length of the period that has just begun, and moves
; on through the steps of the sound as display planes go by. See sound.h for
; what a sound is made of. In assembly because it is short that way: the state
; is reached through one pointer instead of by address, byte for byte.

#include <avr/io.h>

; struct Sound (sound.h)
#define NEXT 0
#define LEFT 2
#define SEEN 3
#define BASE 4
#define MASK 5
#define DICE 6

.section .text

.global TIMER4_OVF_vect
TIMER4_OVF_vect:
    push r24
    in   r24, _SFR_IO_ADDR(SREG)
    push r24
    push r25
    push r28
    push r29
    push r30
    push r31
    ldi  r28, lo8(snd)
    ldi  r29, hi8(snd)

    ; ---- how many planes have gone by since the last look? ------------------
    lds  r24, plane_ticks               ; the low byte will do
    ldd  r25, Y+SEEN
    std  Y+SEEN, r24
    sub  r24, r25
    breq 3f
    ldd  r25, Y+LEFT
    sub  r25, r24
    breq 1f                             ; the step is over
    brcs 1f
    std  Y+LEFT, r25
    rjmp 3f

    ; ---- the next step -------------------------------------------------------
1:  ldd  r30, Y+NEXT
    ldd  r31, Y+NEXT+1
    lpm  r24, Z+
    tst  r24
    brne 2f
    sts  TCCR4A, r24                    ; the end: let go of the pins,
    sts  TCCR4B, r24                    ; stop the timer
    sts  TIMSK4, r24
    rjmp 9f
2:  std  Y+LEFT, r24
    lpm  r24, Z+
    std  Y+BASE, r24
    lpm  r24, Z+
    std  Y+MASK, r24
    lpm  r24, Z+
    clr  r25
    sts  TC4H, r25
    sts  OCR4A, r24                     ; pulse width: takes effect with the next period
    std  Y+NEXT, r30
    std  Y+NEXT+1, r31

    ; ---- roll the dice: s ^= s << 7, s ^= s >> 9, s ^= s << 8 ---------------
3:  ldd  r24, Y+DICE
    ldd  r25, Y+DICE+1
    mov  r30, r25                       ; s << 7: the high byte is bits 1..8 of s,
    lsr  r30
    mov  r30, r24
    ror  r30
    eor  r25, r30
    clr  r30                            ; the low byte is bit 0 of s, at the top
    ror  r30                            ; (neither eor nor clr touches the carry)
    eor  r24, r30
    mov  r30, r25                       ; s >> 9: half the high byte
    lsr  r30
    eor  r24, r30
    eor  r25, r24                       ; s << 8: the low byte
    std  Y+DICE, r24
    std  Y+DICE+1, r25

    ; ---- the period: base + (dice & mask) ------------------------------------
    ldd  r30, Y+MASK
    and  r24, r30
    ldd  r30, Y+BASE
    add  r24, r30
    ; Never set the end of the period below where the counter already is: it
    ; would miss it and run on to its limit. Reading the counter puts its high
    ; bits into TC4H, which the write would use: clear that again.
    lds  r30, TCNT4L
    lds  r31, TC4H
    clr  r25
    sts  TC4H, r25
    tst  r31
    brne 9f
    cpi  r30, 253
    brsh 9f
    subi r30, -2
    cp   r30, r24
    brsh 9f
    sts  OCR4C, r24

9:  pop  r31
    pop  r30
    pop  r29
    pop  r28
    pop  r25
    pop  r24
    out  _SFR_IO_ADDR(SREG), r24
    pop  r24
    reti

; Small Theft Auto - hand-written arithmetic for the inner loops (ATmega32U4).
;
; The C compiler turns a 16 x 16 multiply into a 32-bit library call followed
; by bit shifts, about 115 CPU cycles. The renderer needs two of those per
; ground pixel, so these routines use the chip's hardware multiplier directly.

#include <avr/io.h>

.section .text

; int16_t mulhi_su(int16_t a, uint16_t b)
;   high 16 bits of the 32-bit product of signed a and unsigned b
;   a in r25:r24, b in r23:r22, result in r25:r24        (about 28 cycles with the call)
.global mulhi_su
mulhi_su:
    movw r20, r24               ; a -> r21:r20
    clr  r26
    mul  r20, r22               ; aL * bL
    mov  r18, r1                ; keep byte 1 for the carries
    mulsu r21, r23              ; aH * bH   (signed * unsigned)
    movw r24, r0                ; bytes 3:2
    mulsu r21, r22              ; aH * bL   (signed * unsigned)
    sbc  r25, r26               ; sign-extend the partial product
    add  r18, r0
    adc  r24, r1
    adc  r25, r26
    mul  r20, r23               ; aL * bH
    add  r18, r0
    adc  r24, r1
    adc  r25, r26
    clr  r1
    ret

; uint16_t mulhi_uu(uint16_t a, uint16_t b)
;   high 16 bits of the 32-bit product of two unsigned values
.global mulhi_uu
mulhi_uu:
    movw r20, r24
    clr  r26
    mul  r20, r22               ; aL * bL
    mov  r18, r1
    mul  r21, r23               ; aH * bH
    movw r24, r0
    mul  r21, r22               ; aH * bL
    add  r18, r0
    adc  r24, r1
    adc  r25, r26
    mul  r20, r23               ; aL * bH
    add  r18, r0
    adc  r24, r1
    adc  r25, r26
    clr  r1
    ret

; uint16_t fx_vector_page(uint16_t dev_page)
;   Where our data starts on the flash chip. A flashcart build has the answer
;   patched into an unused interrupt vector (key 0x9518 at 0x14, then the page,
;   high byte first); a development build uses the page passed in.
;   The instruction sequence is the same one the ArduboyFX library uses, which
;   is what emulators and tools look for to recognise an FX game.
.global fx_vector_page
fx_vector_page:
    ldi  r30, 0x14
    ldi  r31, 0x00
    lpm  r18, Z+
    lpm  r19, Z+
    lpm  r21, Z+
    lpm  r20, Z+
    subi r18, 0x18
    sbci r19, 0x95
    brne 1f
    movw r24, r20
1:  ret

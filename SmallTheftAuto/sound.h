// Small Theft Auto - sound.
//
// The speaker sits between two pins (port C, bits 6 and 7) that timer 4 can
// drive by itself, one the opposite of the other. The timer makes one pulse
// per period and counts in steps of 8 microseconds. A sound is a list of steps
// (tools/sound.py): how long the step lasts, how short the periods are, how
// much chance stretches each one (that is what makes noise out of a tone), and
// how wide the pulses are. Narrow pulses are quieter: it is the only volume
// control a pin has.
//
// A short interrupt at the start of every period (sound.S) rolls the dice for
// the period's length. While the display is being refreshed (1.2 ms, 156 times
// a second) it has to wait; the timer keeps going with the period it has.
//
// The timer's set-up is the one the ATMlib music library uses on the Arduboy
// (PWM on OCR4A, both pins connected), with a slower clock and a period that
// changes.
#pragma once

#include <avr/eeprom.h>

static const uint8_t *const SOUNDS[] PROGMEM = {SOUND_LIST};

// what is being played (layout shared with sound.S, where the interrupt is)
struct Sound {
  const uint8_t *next;               // +0  the step after the one being played
  uint8_t left;                      // +2  planes left of the step being played
  uint8_t seen;                      // +3  the plane count when last looked at
  uint8_t base, mask;                // +4 +5
  uint16_t dice;                     // +6
};
static_assert(sizeof(Sound) == 8, "Sound layout is shared with sound.S");

extern "C" {
  Sound snd __attribute__((used)) = {0, 0, 0, 0, 0, 0xACE1};
}

static void sound_begin() {
  TIMSK4 = 0;
  TCCR4B = 0;                        // stopped
  TCCR4C = 0;                        // (written first: it shares bits with TCCR4A)
  TCCR4A = 0;                        // pins let go
  TCCR4D = 0;                        // count up to OCR4C, start again
  TCCR4E = 0;
  PORTC &= ~(_BV(6) | _BV(7));       // both ends of the speaker low when nothing plays
}

// Sound off means the pins stay inputs; everything else runs as if it were
// on. Whether it is on is up to the settings page; until the player has been
// there, it is as the console has it for all its games (byte 2 of its
// settings memory, the place the Arduboy2 library looks too).
void sound_enable(bool on) {
  if (on) DDRC |= _BV(6) | _BV(7);
  else DDRC &= ~(_BV(6) | _BV(7));
}

void sound_play(uint8_t which) {
  const uint8_t *p = (const uint8_t *)pgm_read_word(&SOUNDS[which]);
  uint8_t sreg = SREG;
  cli();
  TIMSK4 = 0;
  TCCR4B = 0;
  TCCR4A = 0;                        // out of PWM mode: what is written now counts at once
  TCNT4 = 0;                         // (this leaves the shared high byte, TC4H, at 0 as well)
  snd.left = pgm_read_byte(p);
  snd.base = pgm_read_byte(p + 1);
  snd.mask = pgm_read_byte(p + 2);
  OCR4C = snd.base;
  OCR4A = pgm_read_byte(p + 3);
  snd.next = p + 4;
  snd.seen = (uint8_t)plane_ticks;
  TIFR4 = _BV(TOV4);
  TCCR4A = _BV(COM4A0) | _BV(PWM4A);
  TIMSK4 = _BV(TOIE4);
  TCCR4B = _BV(CS43);                // go: 16 MHz / 128
  SREG = sreg;
}

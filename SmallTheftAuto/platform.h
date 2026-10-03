// Small Theft Auto - hardware layer.
//
// Everything that touches the console lives here: flash chip, display, buttons
// and the frame clock. The desktop test build (HOST) swaps in a fake version so
// the same engine code can be run and inspected on a computer.
#pragma once

#include <stdint.h>

#ifdef HOST
  #include <string.h>
  #define PROGMEM
  #define pgm_read_byte(p) (*(const uint8_t *)(p))
  #define pgm_read_word(p) (*(const uint16_t *)(p))
  typedef uint32_t uint24_t;
#else
  #include <Arduino.h>
  #include <avr/pgmspace.h>
  #include <avr/interrupt.h>
  typedef __uint24 uint24_t;
#endif

#include "tables.h"
#include "fxdata.h"

#define BTN_B     0x04
#define BTN_A     0x08
#define BTN_DOWN  0x10
#define BTN_LEFT  0x20
#define BTN_RIGHT 0x40
#define BTN_UP    0x80

#define FB_BYTES (COLS * COLBYTES)
#define PLANE_HZ 156
#define PLANE_PERIOD 1602          // timer counts per plane, less one: 16 MHz / 64 / 1603 = 155.96 Hz

#define ALWAYS_INLINE inline __attribute__((always_inline))
#define NOINLINE __attribute__((noinline))

// The picture: two bit planes (level = 2*hi + lo), column-major, 7 bytes per
// column, bit 0 = top row. The bottom 8 rows of the panel are a 1-bit HUD strip.
// With disp_wide set the two planes are a page in black and white instead,
// 128 dots wide: hi holds the even columns of dots, lo the odd ones.
extern uint8_t fb_hi[FB_BYTES];
extern uint8_t fb_lo[FB_BYTES];
extern uint8_t hud[128];
// With disp_nav set (to DISP_NAV) the way to go is shown at the top of the 3D
// view, in single dots. The arrow is laid over the view: nav_over holds, for
// its 16 rows in two halves and for every column of dots, what to keep of the
// view and what to light up. The distance next to it, 8 rows, is in the
// picture itself, the way a page is: left dots in hi, right dots in lo.
extern uint8_t nav_over[NAV_ARROW_BYTES];
#define DISP_NAV 3

// what the player has chosen on the settings page
#define SET_SOUND 1
#define SET_LED 2
#define SET_MONO 4      // two shades instead of four: for panels that flicker with the four (the FX-C is said to)
// the light next to the screen
#define LIGHT_OFF 0
#define LIGHT_RED 1
#define LIGHT_BLUE 2

#ifdef HOST
// ---------------------------------------------------------------- desktop
extern const uint8_t *host_flash;
extern uint32_t host_flash_pos;
extern uint32_t host_flash_reads, host_flash_seeks;
extern uint16_t host_ticks;
extern uint8_t host_buttons;

static inline void fx_begin(uint24_t addr) { host_flash_pos = addr; host_flash_seeks++; }
static inline uint8_t fx_next() { host_flash_reads++; return host_flash[host_flash_pos++]; }
static inline void fx_end() {}
static inline void fx_read(uint24_t addr, uint8_t *to, uint8_t n) {
  fx_begin(addr);
  while (n--) *to++ = fx_next();
  fx_end();
}
static inline void fb_commit(uint8_t c, const uint8_t *hi, const uint8_t *lo) {
  memcpy(fb_hi + c * COLBYTES, hi, COLBYTES);
  memcpy(fb_lo + c * COLBYTES, lo, COLBYTES);
}
static inline uint8_t buttons() { return host_buttons; }
static inline uint16_t ticks() { return host_ticks; }
static inline void platform_init() {}
static inline bool flash_ok() { return true; }
static inline void exit_to_menu() {}
extern uint16_t host_sounds;
extern uint8_t host_sound;         // the last one played
static inline void sound_play(uint8_t which) { host_sound = which; host_sounds++; }
static inline bool sound_busy() { return false; }
extern uint8_t disp_wide, disp_nav;
extern uint8_t host_light;
void save_load();          // what was kept: the settings, the money, the missions done
void save_store();
static inline void sound_enable(bool on) { (void)on; }
static inline void light(uint8_t which) { host_light = which; }
static inline void display_shades(bool two) { (void)two; }

#else
// ---------------------------------------------------------------- console
// Pins (Arduboy FX): display CS PD6, D/C PD4, reset PD7; flash CS PD1; SPI on PB1..PB3.
#define OLED_CS_BIT 6
#define OLED_DC_BIT 4
#define OLED_RST_BIT 7
#define FLASH_CS_BIT 1
#define FLASH_CS_BIT_E 2          // port E: the FX-C and the Mini keep SDA for the link cable

extern volatile uint16_t plane_ticks;
extern volatile uint8_t disp_plane;
extern volatile uint8_t disp_wide;
extern volatile uint8_t disp_nav;
extern volatile uint8_t disp_mono;  // two shades: see display.S
extern uint8_t flash_on_e;          // the chip answers on PE2 (an FX-C or a Mini), not on PD1
void display_shades(bool two);      // four shades, or two
extern uint16_t fx_page;          // where our data starts on the chip, in 256-byte pages

// a byte takes 16 CPU cycles to shift out; idle through most of that, then
// poll the flag for the last few
#define SPI_IDLE() __asm__ __volatile__("rjmp .+0\n\trjmp .+0\n\trjmp .+0\n\trjmp .+0\n\trjmp .+0\n\trjmp .+0")

static ALWAYS_INLINE void spi_wait() {
  while (!(SPSR & _BV(SPIF))) {}
}

static ALWAYS_INLINE void spi_out(uint8_t v) {
  SPDR = v;
  SPI_IDLE();
  spi_wait();
}

// the same as a call, for where a few cycles more do not matter: it is shorter
void spi_send(uint8_t v);

// Flash reads happen with interrupts off, so the display refresh (which shares
// the SPI bus) can never land in the middle of one. Each read is a few dozen
// microseconds, far below what the refresh timing can notice.
void fx_begin(uint24_t addr);

// the next byte, written out in place: for where many are read in a row
static ALWAYS_INLINE uint8_t fx_next_fast() {
  SPDR = 0;
  SPI_IDLE();
  spi_wait();
  return SPDR;
}

// the same as a call, for everywhere else: it is shorter
uint8_t fx_next();

void fx_end();         // lets go of the chip's select line, whichever it is, and interrupts back on

// so many bytes from there, in one go (no more than a few dozen: the display
// has to wait meanwhile)
void fx_read(uint24_t addr, uint8_t *to, uint8_t n);

static inline void fb_commit(uint8_t c, const uint8_t *hi, const uint8_t *lo) {
  uint8_t *ph = fb_hi + (uint16_t)c * COLBYTES;
  uint8_t *pl = fb_lo + (uint16_t)c * COLBYTES;
  cli();
  for (uint8_t i = 0; i < COLBYTES; i++) { *ph++ = *hi++; *pl++ = *lo++; }
  sei();
}

static inline uint8_t buttons() {
  // same bit layout as Arduboy2: pressed = 1
  uint8_t b = ((~PINF) & 0xF0);            // up, right, left, down
  b |= (((~PINE) & _BV(6)) >> 3);          // A
  b |= (((~PINB) & _BV(4)) >> 2);          // B
  return b;
}

static inline uint16_t ticks() {
  cli();
  uint16_t t = plane_ticks;
  sei();
  return t;
}

void platform_init();
void refresh_period(uint16_t period);
bool flash_ok();       // is our data readable? wakes the chip again if it is not
void exit_to_menu();   // restart into the console's game menu; does not return
void sound_play(uint8_t which);   // one of SOUND_*; whatever was playing is cut off
static inline bool sound_busy() { return TIMSK4 != 0; }
void sound_enable(bool on);       // connect the speaker, or leave it alone
void save_load();                 // what was kept: the settings (the first time, as the console has
                                  // them), the money, the missions done
void save_store();

// The light next to the screen: red on PB6, blue on PB5, lit when the pin is
// low. Timer 1 runs as Arduino's start-up code leaves it (490 times a second,
// counting to 255); letting it drive the pin dims the light to a quarter,
// which next to a screen this small is plenty.
static inline void light(uint8_t which) {
#ifndef PROFILE
  TCCR1A = _BV(WGM10) | (which == LIGHT_RED ? _BV(COM1B1) : which == LIGHT_BLUE ? _BV(COM1A1) : 0);
#endif
}
#endif

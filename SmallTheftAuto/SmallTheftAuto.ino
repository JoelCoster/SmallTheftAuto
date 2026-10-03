// Small Theft Auto - a 3D open-world crime game for the Arduboy FX.
//
// This file is the console side of the hardware layer: start-up, the flash
// chip, and the display driver that produces four brightness levels. Sound is
// in sound.h.
//
// Grayscale works by showing three 1-bit pictures ("planes") in turn, 156 times
// a second, in step with the panel's own refresh. The step-keeping trick is the
// one pioneered by Peter Brown's ArduboyG library: the panel is told it has a
// single row, which makes it wait ("park") on that row, and is released for
// exactly one full scan each time a new plane has been sent. The parked row is
// the bottom row of the screen and always stays black.
//
// Unlike ArduboyG the game is drawn once, into a 2-bit picture, and the three
// planes are derived from that on the fly while they are sent. That is what
// lets a slow 3D renderer run underneath a fast flicker-free display. It is
// also what lets the display routine lay the arrow that shows the way over
// the picture, in dots half as wide as the picture's own.
//
// The FX-C and the Mini are said to flicker with the four shades (their panel
// does not keep in step the same way). For them, and for whoever prefers it,
// the settings page has GRAYSCALE OFF: the same picture in two shades, the
// two grey levels as patterns of dots (display.S, disp_mono), and the panel
// scanning by itself as it does for any other game. The flash chip's select
// line is found at start-up: PD1 on the FX, PE2 on the FX-C and the Mini.

// The game as it is played has no USB connection. That and Arduino's start-up
// code are 3.6 KB of program and 150 bytes of memory that the game has better
// use for. The test build (-DDIAG) has both, and so has a build with
// -DUSB_LINK, which answers "s" with a line of status. No build uses the
// Arduboy library: the console is set up here (console_boot).
#if !defined(DIAG) && !defined(USB_LINK) && !defined(NO_USB)
#define NO_USB
#endif

#include <Arduino.h>
#include <util/delay.h>
#include <avr/wdt.h>
#include "platform.h"
#include "game.h"
#include "pages.h"
#include "sound.h"

uint8_t fb_hi[FB_BYTES] __attribute__((used));
uint8_t fb_lo[FB_BYTES] __attribute__((used));
uint8_t hud[128] __attribute__((used));
volatile uint16_t plane_ticks __attribute__((used));
volatile uint8_t disp_plane __attribute__((used));
volatile uint8_t disp_wide __attribute__((used));
volatile uint8_t disp_nav __attribute__((used));
volatile uint8_t disp_mono __attribute__((used));
uint8_t nav_over[NAV_ARROW_BYTES] __attribute__((used));
// second byte of the two "number of rows" commands the refresh sends, bit-reversed
// like everything that goes to the panel: 64 rows to scan, 1 row to park
volatile uint8_t disp_release __attribute__((used)) = 0xFC;
volatile uint8_t disp_park __attribute__((used)) = 0x00;
uint16_t fx_page;
uint8_t flash_on_e;

// shared with the assembly routines in render.S
extern "C" {
  uint8_t colbuf[16] __attribute__((used));
  uint16_t view_x __attribute__((used)), view_y __attribute__((used));
  uint8_t win[512] __attribute__((used));
  uint8_t win_x0[2] __attribute__((used)), win_y0[2] __attribute__((used));
  WallJob wall_job __attribute__((used));
  Dda dda __attribute__((used));
}

// The refresh interrupt itself is in display.S (hand-timed assembly).

static const uint8_t OLED_SETUP[] PROGMEM = {
  0xD5, 0xF0,       // the panel's own clock as fast as it goes
  0x8D, 0x14,       // its charge pump on
  0xAF,             // and the panel itself
  0xC0,             // rows counted from the bottom, so the park row is the bottom row
  0xA1,             // columns left to right
  0xD9, 0x21,       // short pre-charge, as ArduboyG uses for clean grays
  0x81, 0xFF,       // full contrast
  0x20, 0x00,       // horizontal addressing
  0x21, 0x00, 0x7F,
  0x22, 0x00, 0x07, // write pointer to the start
  0xA8, 0x00,       // park
};

extern "C" uint16_t fx_vector_page(uint16_t dev_page);

// Two shades: every third refresh sends the picture as it is, and the panel
// is never parked (the "park" command says 64 rows as well), so it scans by
// itself. Four shades: as described above.
void display_shades(bool two) {
  disp_mono = two;
  disp_park = two ? 0xFC : 0x00;
}

void spi_send(uint8_t v) {
  spi_out(v);
}

// The chip's select line is PD1 (SDA) on the Arduboy FX and PE2 (HWB) on the
// FX-C and the Mini, which keep SDA and SCL for the link cable. platform_init()
// looks for our data on PD1 and then on PE2, and from then on only the line
// it was found on is driven. Interrupts are off while the chip is selected:
// the display shares the bus.
static void flash_select() {
  cli();
  if (flash_on_e) PORTE &= ~_BV(FLASH_CS_BIT_E);
  else PORTD &= ~_BV(FLASH_CS_BIT);
}

void fx_end() {
  if (flash_on_e) PORTE |= _BV(FLASH_CS_BIT_E);
  else PORTD |= _BV(FLASH_CS_BIT);
  sei();
}

void fx_begin(uint24_t addr) {
  addr += (uint24_t)fx_page << 8;
  flash_select();
  spi_send(0x03);
  spi_send((uint8_t)(addr >> 16));
  spi_send((uint8_t)(addr >> 8));
  spi_send((uint8_t)addr);
}

uint8_t fx_next() {
  return fx_next_fast();
}

void fx_read(uint24_t addr, uint8_t *to, uint8_t n) {
  fx_begin(addr);
  while (n--) *to++ = fx_next_fast();
  fx_end();
}

static void flash_wake() {
  flash_select();
  spi_send(0xAB);                   // leave power-down (the bootloader puts the chip to sleep)
  fx_end();
  _delay_ms(1);
}

bool flash_ok() {
  fx_begin(FX_HEADER);
  uint8_t a = fx_next(), b = fx_next();
  fx_end();
  if (a == 'S' && b == 'M') return true;
  flash_wake();
  return false;
}

// Is our data there with PE2 as the select line? Woken and asked the way
// flash_wake() and flash_ok() do it, but PE2 is never driven high: to
// deselect it is let go and pulled up, so the FX's HWB pin, held low on that
// board, takes no load, while an FX-C's chip sees its line go high all the
// same. (The way Pocket Stage's flash.h does it.)
static void probe_e_select() {
  PORTE &= ~_BV(FLASH_CS_BIT_E);
  DDRE |= _BV(FLASH_CS_BIT_E);
}

static void probe_e_let_go() {
  DDRE &= ~_BV(FLASH_CS_BIT_E);
  PORTE |= _BV(FLASH_CS_BIT_E);
}

static bool flash_probe_e() {
  probe_e_select();
  spi_send(0xAB);
  probe_e_let_go();
  _delay_ms(1);
  probe_e_select();
  uint24_t addr = (uint24_t)fx_page << 8;         // FX_HEADER, which is 0
  spi_send(0x03);
  spi_send((uint8_t)(addr >> 16));
  spi_send((uint8_t)(addr >> 8));
  spi_send((uint8_t)addr);
  uint8_t a = fx_next_fast(), b = fx_next_fast();
  probe_e_let_go();
  return a == 'S' && b == 'M';
}

// ------------------------------------------------------------------ what is kept
// The game has 4 KB of the flash chip to write to: the list of games gives
// every game that asks for it a place of its own, and tells it where through
// an unused interrupt vector (key 0x9518 at 0x18, then the page, high byte
// first), the way the ArduboyFX library has it. A development build uses the
// last 4 KB of the chip.
//
// The place starts with four letters. After them comes what was stored, one
// entry each time, the last one counts; bytes never written read 0xFF. When
// the place is full it is wiped and begun again. An entry is
//
//   one byte below 0x80     the settings, as the game kept them before it had
//                           missions
//   7 bytes                 what is kept (Kept, game.h: the settings, with
//                           0x80 on top to tell them from the above, the
//                           money, the missions done), and a byte that makes
//                           the sum of all of them SAVE_SUM: an entry the
//                           console was switched off in the middle of does
//                           not count
#define SAVE_BYTES (sizeof(Kept) + 1)
#define SAVE_SUM 0x5A
static uint16_t save_page;         // where the 4 KB start, in pages
static uint16_t save_next;         // where the next entry goes; 0: the place has to be wiped first
static const uint8_t SAVE_KEY[4] PROGMEM = {'S', 'T', 'A', 1};

// one command that changes what is on the chip: 0x02 writes a byte, 0x20 wipes 4 KB
static void flash_change(uint8_t command, uint16_t at, int16_t value) {
  flash_select();
  spi_send(0x06);                   // the chip wants to be asked first
  fx_end();
  flash_select();
  spi_send(command);
  uint24_t addr = ((uint24_t)save_page << 8) + at;
  spi_send((uint8_t)(addr >> 16));
  spi_send((uint8_t)(addr >> 8));
  spi_send((uint8_t)addr);
  if (value >= 0) spi_send((uint8_t)value);
  fx_end();
  // it is busy for a while; the display goes on meanwhile
  uint8_t busy;
  do {
    flash_select();
    spi_send(0x05);
    busy = fx_next();
    fx_end();
  } while (busy & 1);
}

// so many bytes of the place, from there
static NOINLINE void save_read(uint16_t at, uint8_t *to, uint8_t n) {
  fx_read(((uint24_t)(uint16_t)(save_page - fx_page) << 8) + at, to, n);
}

void save_load() {
  save_page = FX_SAVE_PAGE;
  if (pgm_read_word(0x18) == 0x9518) save_page = ((uint16_t)pgm_read_byte(0x1A) << 8) | pgm_read_byte(0x1B);
  // sound as the console has it, until the player says otherwise
  settings = eeprom_read_byte((const uint8_t *)2) ? SET_SOUND : 0;
  // an FX-C or a Mini: two shades until the player says otherwise (the four are said to flicker there)
  if (flash_on_e) settings |= SET_MONO;
  uint8_t e[SAVE_BYTES];
  save_read(0, e, 4);
  for (uint8_t i = 0; i < 4; i++)
    if (e[i] != pgm_read_byte(&SAVE_KEY[i])) return;      // not ours yet (save_next is 0)
  save_next = 4;
  while (save_next <= 4096 - SAVE_BYTES) {
    save_read(save_next, e, SAVE_BYTES);
    if (e[0] == 0xFF) return;
    save_next++;
    if (e[0] < 0x80) {
      settings = e[0];
      continue;
    }
    save_next += SAVE_BYTES - 1;
    e[0] &= 0x7F;
    uint8_t sum = 0x80;
    for (uint8_t i = 0; i < SAVE_BYTES; i++) sum += e[i];
    if (sum != SAVE_SUM) continue;
    for (uint8_t i = 0; i < sizeof(Kept); i++) ((uint8_t *)&kept)[i] = e[i];
  }
}

static void save_byte(uint8_t v) {
  flash_change(0x02, save_next++, v);
}

void save_store() {
  if (save_next == 0 || save_next > 4096 - SAVE_BYTES) {
    flash_change(0x20, 0, -1);
    save_next = 0;
    for (uint8_t i = 0; i < 4; i++) save_byte(pgm_read_byte(&SAVE_KEY[i]));
  }
  uint8_t sum = SAVE_SUM;
  for (uint8_t i = 0; i < sizeof(Kept); i++) {
    uint8_t v = ((uint8_t *)&kept)[i];
    if (i == 0) v |= 0x80;
    sum -= v;
    save_byte(v);
  }
  save_byte(sum);
}

void exit_to_menu() {
  // the loader resets the display itself, so it does not matter that the
  // grayscale driver leaves the panel parked on one row
  // the word the loader looks for, and the watchdog to restart the console
  cli();
  *(uint8_t *)0x0800 = 0x77;
  *(uint8_t *)0x0801 = 0x77;
  wdt_reset();
  WDTCSR = _BV(WDCE) | _BV(WDE);
  WDTCSR = _BV(WDE);
  for (;;) {}
}

// With -DUSB_LINK a computer can ask the game how it is doing: send "s" over
// USB and one line comes back (tools/diag.py watch 5 1:s). Every build did
// that until the game needed the room; see the top of this file.
#ifdef USB_LINK
static void link_value(const __FlashStringHelper *name, uint16_t v) {
  Serial.print(name);
  Serial.print(v);
}

static void link_poll() {
  if (Serial.available() <= 0 || Serial.read() != 's') return;
  link_value(F("S fps="), fps_value);
  link_value(F(" frames="), frames_total);
  link_value(F(" ticks="), ticks());
  link_value(F(" fail="), flash_fails);
  link_value(F(" e2="), flash_on_e);
  link_value(F(" page="), fx_page);
  Serial.println();
}
#endif

#include "diag.h"                  // (down here: the test build looks into what is kept)
#include "probe.h"

// send one command byte to the panel (not from the refresh interrupt)
void display_command(uint8_t v) {
  cli();
  PORTD &= ~_BV(OLED_CS_BIT);
  PORTD &= ~_BV(OLED_DC_BIT);
  spi_send(v);
  PORTD |= _BV(OLED_DC_BIT);
  PORTD |= _BV(OLED_CS_BIT);
  sei();
}

void display_setup() {
  for (uint8_t i = 0; i < sizeof(OLED_SETUP); i++) display_command(pgm_read_byte(&OLED_SETUP[i]));
}

// Timer 3 gives one interrupt per plane: 16 MHz / 64 / (period + 1).
//
// The order matters on the real chip. Arduino's start-up code leaves the timer
// in an 8-bit PWM mode, and in that mode the chip keeps only the low 8 bits of
// a period written to it: 1602 became 66, the interrupt ran 3700 times a second
// instead of 156, and the game got no processor time at all (black screen).
// So: stop the timer, leave PWM mode, and only then write the period. "Clear on
// compare" mode takes the period at once, with no buffering.
void refresh_period(uint16_t period) {
  cli();
  TIMSK3 = 0;
  TCCR3B = 0;
  TCCR3A = 0;
  OCR3A = period;
  TCNT3 = 0;
  TIFR3 = _BV(OCF3A);
  TCCR3B = _BV(WGM32) | _BV(CS31) | _BV(CS30);
  TIMSK3 = _BV(OCIE3A);
  sei();
}

// The console is set up here, pin by pin. Without the USB connection the
// program needs nothing of Arduino's start-up code (which is there for USB,
// and for a clock the game does not use).
static void console_boot() {
#ifdef NO_USB
  // the loader leaves USB switched on, and nobody here would answer it
  UDIEN = 0;
  UDCON = _BV(DETACH);
  USBCON = _BV(FRZCLK);
  UHWCON = 0;
  // no interrupt but the ones the game has: display, sound
  TIMSK0 = 0;
  TIMSK1 = 0;
  PRR1 = _BV(PRUSB) | _BV(PRUSART1);
#endif
  // no clock for what is not used: two-wire bus, converter
  PRR0 = _BV(PRTWI) | _BV(PRADC);
  // port B: button B (4), the light (5 blue, 6 red, 7 green; off is high),
  // the SPI bus (1, 2 out; 3 in, pulled up: where no chip answers, a read gives
  // 0xFF), the small light for "receiving" (0, off is high)
  PORTB = _BV(4) | _BV(5) | _BV(6) | _BV(7) | _BV(3) | _BV(0);
  DDRB = _BV(5) | _BV(6) | _BV(7) | _BV(2) | _BV(1) | _BV(0);
  // port D: the display (select high, reset low for now), the flash chip
  // (select high), the small light for "sending" (5, off is high)
  PORTD = _BV(OLED_CS_BIT) | _BV(FLASH_CS_BIT) | _BV(5);
  DDRD = _BV(OLED_RST_BIT) | _BV(OLED_CS_BIT) | _BV(OLED_DC_BIT) | _BV(FLASH_CS_BIT) | _BV(5);
  // the buttons
  PORTE = _BV(6);
  DDRE = 0;
  PORTF = 0xF0;
  DDRF = 0;
  // the SPI bus: the console in charge, 8 MHz
  SPCR = _BV(SPE) | _BV(MSTR);
  SPSR = _BV(SPI2X);
  // timer 1, for the light: counting to 255, 490 times a second
  TCCR1B = _BV(CS11) | _BV(CS10);
  // the display comes out of its reset
  _delay_ms(5);
  PORTD |= _BV(OLED_RST_BIT);
  _delay_ms(5);
}

#ifdef NO_USB
int main() {
  setup();
  for (;;) loop();
}
#endif

void platform_init() {
  console_boot();
#ifdef DIAG
  diag_begin();
#endif
#ifdef PROBE
  probe_begin();
#endif

  // the flash chip shares the SPI bus with the display: give each its own select
  PORTD |= _BV(FLASH_CS_BIT) | _BV(OLED_CS_BIT);
  DDRD |= _BV(FLASH_CS_BIT);
  probe_e_let_go();                 // PE2 pulled up: an FX-C's chip stays out of it while PD1 is tried
  _delay_ms(1);
  flash_wake();

  fx_page = fx_vector_page(FX_DATA_PAGE);
  // Where is our data: on PD1 (the FX) or on PE2 (the FX-C, the Mini)? Asked
  // here and never again. Twenty rounds, 5 ms apart; when nothing answers the
  // game goes on as on the FX, as it always did.
  for (;;) {
    if (flash_ok()) break;                          // (wakes the chip again when it is not)
    if (flash_probe_e()) {
      DDRD &= ~_BV(FLASH_CS_BIT);                   // SDA let go: it goes to the link cable there
      PORTD &= ~_BV(FLASH_CS_BIT);
      DDRE |= _BV(FLASH_CS_BIT_E);                  // PE2 driven from now on
      flash_on_e = 1;
      break;
    }
    if (++flash_fails >= 20) break;
    _delay_ms(5);
  }
  if (!flash_on_e) PORTE &= ~_BV(FLASH_CS_BIT_E);   // PE2 back as it was: an input without pull-up
  display_setup();
  refresh_period(PLANE_PERIOD);
  // the light: a quarter of its brightness, and off
  OCR1A = OCR1B = 191;
  light(LIGHT_OFF);
  sound_begin();
}

void setup() {
  platform_init();
  save_load();
  settings_apply();
  game_init();
  page_open(PAGE_TITLE);
}

void loop() {
  game_loop();
#ifdef DIAG
  diag_loop();
#elif !defined(NO_USB)
  link_poll();
#endif
}

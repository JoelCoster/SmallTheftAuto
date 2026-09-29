// Small Theft Auto - test build only (-DDIAG).
//
// Lets a computer look inside a console: the program takes commands over USB.
// tools/diag.py is the other end. It knows from the build where everything
// is in the console's memory, so that looking at something new takes no new
// code here, and no room in the program, of which the test build has
// little.
//
//   rAAAANNNN    what is in memory from address AAAA on, NNNN bytes (all hex):
//                a line "R AAAA " and the bytes. The console's ports and
//                timers are in memory too, from address 0x20 on
//   pAAAAVV      put VV into memory at AAAA. The buttons the computer holds
//                down are a byte in memory (diag_buttons) like any other
//   wN           wait N frames (one hex digit) before the next command is
//                looked at: "p....04w1r..." fetches the frame in which the
//                shot is fired
//   x            back to the console's game menu
//   nX           play sound X (n0 the shot, n1 cash ...), whatever the game is doing
//   eXX          forget what was stored on the flash chip (e00), or store what
//                there is to store with XX as the settings (e01 sound, e02
//                police light, e03 both)
//
// Commands are taken between two frames, as many as have come in: what is
// fetched by several of them sent in one go belongs to the same frame.
//
// Earlier versions reported a line of 30 values every second, could set the
// player's record and health by commands of their own, measure the refresh
// timer and the speaker pins and count what the sound interrupt did (the
// lessons are in the README). All of that is memory, looked at from the
// other end now, and so is the line of status that "s" used to bring
// (frames a second, ticks): 0.4 KB that the game needs.
#pragma once
#ifdef DIAG

extern uint8_t __bss_end;

extern volatile uint8_t disp_release, disp_park;
static uint8_t diag_wait;          // frames until the next command is looked at

// The memory between the variables and the stack is filled with a pattern:
// what is left of it says how far the stack has come down (tools/diag.py
// counts).
static void diag_begin() {
  uint8_t *p = &__bss_end;
  uint8_t *top = (uint8_t *)(SP - 16);
  while (p < top) *p++ = 0xA5;
}

static void diag_hex(uint8_t v) {
  static const char H[] PROGMEM = "0123456789ABCDEF";
  Serial.write((char)pgm_read_byte(&H[v >> 4]));
  Serial.write((char)pgm_read_byte(&H[v & 15]));
}

// The next hex digits from the computer, so many, into diag_value. False if
// something else came, or nothing.
static uint16_t diag_value;

static bool diag_number(uint8_t digits) {
  diag_value = 0;
  while (digits--) {
    uint8_t t0 = (uint8_t)millis();
    while (!Serial.available()) if ((uint8_t)((uint8_t)millis() - t0) > 200) return false;
    uint8_t c = (uint8_t)Serial.peek();
    if (c >= 'a') c -= 'a' - 'A';
    c -= '0';
    if (c > 9) {
      c -= 'A' - '0' - 10;
      if (c < 10 || c > 15) return false;
    }
    Serial.read();
    diag_value = (diag_value << 4) | c;
  }
  return true;
}

static void diag_loop() {
  if (diag_wait) {
    diag_wait--;
    return;
  }
  while (Serial.available()) {
    char c = (char)Serial.peek();
    Serial.read();
    if (c == 'x') exit_to_menu();
    if (c == 'r' || c == 'p') {
      if (!diag_number(4)) continue;
      uint8_t *p = (uint8_t *)diag_value;
      if (!diag_number(c == 'r' ? 4 : 2)) continue;
      if (c == 'p') {
        *p = (uint8_t)diag_value;
        continue;
      }
      Serial.write('R');
      Serial.write(' ');
      diag_hex((uint8_t)((uint16_t)p >> 8));
      diag_hex((uint8_t)(uint16_t)p);
      Serial.write(' ');
      while (diag_value--) diag_hex(*p++);
      Serial.println();
      continue;
    }
    if (c != 'w' && c != 'n' && c != 'e') continue;        // (nothing we know)
    if (!diag_number(c == 'e' ? 2 : 1)) continue;
    uint8_t v = (uint8_t)diag_value;
    if (c == 'w' && v) {
      diag_wait = v;
      return;
    }
    if (c == 'n') sound_play(v);
    if (c == 'e') {
      if (v) {
        settings = v;
        save_store();
      } else {
        save_next = 0;
        flash_change(0x20, 0, -1);
      }
    }
  }
}

#endif

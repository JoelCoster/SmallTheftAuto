// Small Theft Auto - a build that tries itself out (-DPROBE).
//
// For builds without a USB connection, which cannot be asked how they are
// doing: it starts the game by itself, stands for 2 seconds, turns the player
// round and round for 12, writes down how many pictures that made, how much
// of the stack was never used and the picture as it is at the end, and goes
// back to the console's menu. What
// it writes goes to the last 4 KB of the flash chip, which belong to test
// builds; tools/lab/probe.py loads such a build and reads what it wrote.
#pragma once
#ifdef PROBE

extern uint8_t __bss_end;

#define PROBE_FROM (2 * PLANE_HZ)
#define PROBE_TO (14 * PLANE_HZ)
#define PROBE_PAGE 0xFFF0

static uint16_t probe_frames, probe_since;

// the memory between the variables and the stack is filled with a pattern:
// what is left of it says how far the stack has come down
static void probe_begin() {
  uint8_t *p = &__bss_end;
  uint8_t *top = (uint8_t *)(SP - 16);
  while (p < top) *p++ = 0xA5;
}

static uint8_t probe_buttons(uint16_t now) {
  if (page == PAGE_TITLE) return BTN_B;
  if (now < PROBE_FROM) return 0;
  if (!probe_since) {
    probe_since = now;
    probe_frames = frames_total;
  }
  if (now < PROBE_TO) return BTN_LEFT;

  uint16_t frames = frames_total - probe_frames, took = now - probe_since;
  uint16_t unused = 0;
  for (uint8_t *p = &__bss_end; *p == 0xA5; p++) unused++;
  uint8_t rec[12] = {'P', 'R', 'B', 1,
                     (uint8_t)frames, (uint8_t)(frames >> 8), (uint8_t)took, (uint8_t)(took >> 8),
                     (uint8_t)unused, (uint8_t)(unused >> 8), flash_fails, fps_value};
  save_page = PROBE_PAGE;
  flash_change(0x20, 0, -1);
  for (uint8_t i = 0; i < sizeof(rec); i++) flash_change(0x02, i, rec[i]);
  // and the picture as it is at this moment: the HUD, then the two bit planes
  uint16_t at = 256;
  for (uint8_t i = 0; i < 128; i++) flash_change(0x02, at++, hud[i]);
  for (uint16_t i = 0; i < FB_BYTES; i++) flash_change(0x02, at++, fb_hi[i]);
  for (uint16_t i = 0; i < FB_BYTES; i++) flash_change(0x02, at++, fb_lo[i]);
  exit_to_menu();
  return 0;
}

#endif

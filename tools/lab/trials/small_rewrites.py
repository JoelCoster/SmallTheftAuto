TRIALS = [
    ("iabs as a routine of its own", [
        ("game.h", "static inline int16_t iabs(int16_t v) { return v < 0 ? -v : v; }",
                   "static NOINLINE int16_t iabs(int16_t v) { return v < 0 ? -v : v; }"),
    ]),
    ("dir_x, dir_y as routines", [
        ("game.h", "static inline int8_t dir_x(uint8_t d) { return (int8_t)pgm_read_byte(&DIRX[d]); }",
                   "static NOINLINE int8_t dir_x(uint8_t d) { return (int8_t)pgm_read_byte(&DIRX[d]); }"),
        ("game.h", "static inline int8_t dir_y(uint8_t d) { return (int8_t)pgm_read_byte(&DIRY[d]); }",
                   "static NOINLINE int8_t dir_y(uint8_t d) { return dir_x(d + 3); }"),
        ("game.h", "static const int8_t DIRX[4] PROGMEM = {0, 1, 0, -1};\nstatic const int8_t DIRY[4] PROGMEM = {-1, 0, 1, 0};\n",
                   "static const int8_t DIRX[7] PROGMEM = {0, 1, 0, -1, 0, 1, 0};\n"),
    ]),
    ("fx_next as a routine (but for fx_read)", [
        ("platform.h", "static ALWAYS_INLINE uint8_t fx_next() {\n  SPDR = 0;\n  SPI_IDLE();\n  spi_wait();\n  return SPDR;\n}\n",
                       "static ALWAYS_INLINE uint8_t fx_next_fast() {\n  SPDR = 0;\n  SPI_IDLE();\n  spi_wait();\n  return SPDR;\n}\nuint8_t fx_next();\n"),
        ("SmallTheftAuto.ino", "void fx_read(uint24_t addr, uint8_t *to, uint8_t n) {\n  fx_begin(addr);\n  while (n--) *to++ = fx_next();\n",
                               "uint8_t fx_next() {\n  return fx_next_fast();\n}\n\nvoid fx_read(uint24_t addr, uint8_t *to, uint8_t n) {\n  fx_begin(addr);\n  while (n--) *to++ = fx_next_fast();\n"),
    ]),
    ("the flash chip is asked at the start only, not every 32 frames", [
        ("game.h", "  if ((++check & 31) == 0 && !flash_ok()) {\n    if (flash_fails != 255) flash_fails++;\n    win_valid[0] = win_valid[1] = false;\n    prop_valid = false;\n  }\n",
                   ""),
        ("game.h", "  static uint8_t check;\n", ""),
    ]),
    ("props: chunks counted in 8 bits", [
        ("engine.h", "      int16_t chx = (pcx >> 4) + dx, chy = (pcy >> 4) + dy;\n      if (chx < 0 || chx > 15 || chy < 0 || chy > 15) continue;\n",
                     "      uint8_t chx = (uint8_t)((pcx >> 4) + dx), chy = (uint8_t)((pcy >> 4) + dy);\n      if (chx > 15 || chy > 15) continue;\n"),
        ("engine.h", "      fx_read(FX_PROP_TABLE + (uint24_t)((uint8_t)chy * 16 + (uint8_t)chx) * 4, e, 4);",
                     "      fx_read(FX_PROP_TABLE + (uint16_t)((uint8_t)(chy * 16 + chx)) * 4, e, 4);"),
    ]),
    ("props: one entry moved as a whole", [
        ("engine.h", "            prop_list[k][0] = prop_list[k - 1][0];\n            prop_list[k][1] = prop_list[k - 1][1];\n            prop_list[k][2] = prop_list[k - 1][2];\n",
                     "            for (uint8_t j = 0; j < 3; j++) prop_list[k][j] = prop_list[k - 1][j];\n"),
        ("engine.h", "          prop_list[k][0] = p[0];\n          prop_list[k][1] = p[1];\n          prop_list[k][2] = p[2];\n",
                     "          for (uint8_t j = 0; j < 3; j++) prop_list[k][j] = p[j];\n"),
    ]),
    ("hud_icon: no test for the edge", [
        ("game.h", "  for (uint8_t k = 0; k < w; k++)\n    if (x + k < 128) hud[x + k] = pgm_read_byte(icon + k);\n  return x + w + 1;",
                   "  while (w--) hud[x++] = pgm_read_byte(icon++);\n  return x + 1;"),
    ]),
    ("hud_money by way of digit_off", [
        ("game.h", "    hud_char(x, '0' + v % 10);\n    v /= 10;\n    x -= 4;",
                   "    hud_char(x, '0' + digit_off(v));\n    x -= 4;"),
    ]),
    ("pick a cell near a place: one routine for cars, parked cars, people", [
        ("game.h", "static void parked_spawn(Car &c, bool close) {",
                   "// a cell by chance, up to so many cells from a place each way; false if it\n// is off the map\nstatic int16_t pick_x, pick_y;\nstatic int8_t pick_dx, pick_dy;\nstatic NOINLINE bool pick_cell(uint16_t ax, uint16_t ay, uint8_t spread) {\n  pick_dx = (int8_t)(rnd8() % (uint8_t)(2 * spread + 1)) - spread;\n  pick_dy = (int8_t)(rnd8() % (uint8_t)(2 * spread + 1)) - spread;\n  pick_x = (int16_t)(ax >> 8) + pick_dx;\n  pick_y = (int16_t)(ay >> 8) + pick_dy;\n  return !(pick_x < 2 || pick_x > 253 || pick_y < 2 || pick_y > 253);\n}\n\nstatic void parked_spawn(Car &c, bool close) {"),
        ("game.h", "    int8_t dx = (int8_t)(rnd8() % 25) - 12;\n    int8_t dy = (int8_t)(rnd8() % 25) - 12;\n    int16_t cx = (int16_t)(ax >> 8) + dx;\n    int16_t cy = (int16_t)(ay >> 8) + dy;\n    if (cx < 2 || cx > 253 || cy < 2 || cy > 253) continue;\n",
                   "    if (!pick_cell(ax, ay, 12)) continue;\n    int16_t cx = pick_x, cy = pick_y;\n"),
        ("game.h", "  int16_t cx = (int16_t)(ax >> 8) + (int8_t)(rnd8() % 17) - 8;\n  int16_t cy = (int16_t)(ay >> 8) + (int8_t)(rnd8() % 17) - 8;\n  if (cx < 2 || cx > 253 || cy < 2 || cy > 253) return;\n",
                   "  if (!pick_cell(ax, ay, 8)) return;\n  int16_t cx = pick_x, cy = pick_y;\n"),
    ]),
    ("what is drawn is handed over in registers, not as a record", [
        ("engine.h", "static void draw_add(const Entity &e) {\n  int16_t qx = (int16_t)(e.x - view_x);\n  int16_t qy = (int16_t)(e.y - view_y);",
                     "static NOINLINE void draw_at(uint16_t ex, uint16_t ey, uint8_t ehd, uint8_t eset) {\n  int16_t qx = (int16_t)(ex - view_x);\n  int16_t qy = (int16_t)(ey - view_y);"),
        ("engine.h", "  const uint8_t *st = &SPRITE_SETS[(uint16_t)e.set * 4];", "  const uint8_t *st = &SPRITE_SETS[(uint16_t)eset * 4];"),
        ("engine.h", "  uint8_t rel = viewyaw - (uint8_t)(e.hd >> 8);", "  uint8_t rel = viewyaw - ehd;"),
        ("engine.h", "static void view_begin(const Camera &cam) {",
                     "static inline void draw_add(const Entity &e) {\n  draw_at(e.x, e.y, (uint8_t)(e.hd >> 8), e.set);\n}\n\nstatic void view_begin(const Camera &cam) {"),
        ("engine.h", "    Entity en;\n    en.x = ((uint16_t)prop_list[i][1] << 8) | ((k & 0x0C) << 4) | 0x20;\n    en.y = ((uint16_t)prop_list[i][2] << 8) | ((k & 0x03) << 6) | 0x20;\n    en.hd = 0;\n    en.set = (k >> 4) == PROP_TREE ? SPR_TREE : SPR_LAMP;\n    en.flags = 0;\n    draw_add(en);\n",
                     "    draw_at(((uint16_t)prop_list[i][1] << 8) | ((k & 0x0C) << 4) | 0x20,\n            ((uint16_t)prop_list[i][2] << 8) | ((k & 0x03) << 6) | 0x20,\n            0, (k >> 4) == PROP_TREE ? SPR_TREE : SPR_LAMP);\n"),
    ]),
]

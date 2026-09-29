// Small Theft Auto - 3D city renderer.
//
// One ray per screen column walks the city grid cell by cell. Each column is
// built in a small scratch buffer (ground, walls, sky, sprites) and then copied
// into the frame buffer in one go, so the display never shows a half-drawn
// column.
//
// The three inner loops exist twice: in plain C++ here (ground_c, wall_c,
// dda_c), which is the definition of what they do and what the desktop build
// runs, and in assembly (render.S), which is what the console runs. SELFTEST
// builds run both on the console and count differences.
//
// Fixed point formats:
//   positions and depths  8.8  cells   (1 cell = 4 m, 256 units)
//   directions            Q14          (16384 = 1.0)
//   perspective scale     10.6 pixels per cell of height
#pragma once

#include "platform.h"

struct Camera {
  uint16_t x, y;      // 8.8 cells
  uint16_t yaw;       // 65536 = full turn, 0 = north (-y), clockwise
};

struct Entity {
  uint16_t x, y;      // 8.8 cells
  uint16_t hd;        // heading, same units as yaw
  uint8_t set;        // sprite set, 0xFF = unused slot
  uint8_t flags;
};

#define MAX_DRAW 16
#define MAX_PROPS 10

struct DrawSprite {
  int8_t c0;          // leftmost screen column
  int8_t r0;          // top screen row
  uint8_t w, h;       // columns, rows
  uint8_t depth;      // quarter cells
  uint24_t addr;      // flash address of the first column
};

// One wall segment to draw (layout shared with render.S)
struct WallJob {
  uint8_t lv[4];          // +0   level for texel codes 0..3
#ifdef HOST
  const uint8_t *texm;    //      texture column, upper floors
  const uint8_t *texg;    //      texture column, ground floor
#else
  uint16_t texm;          // +4
  uint16_t texg;          // +6
#endif
  uint8_t top;            // +8   index of the top floor
  uint16_t zstep;         // +9   cells per pixel, 0.16
  uint8_t z[3];           // +11  height of the first pixel, 8.16 cells, signed
} __attribute__((packed));

// One ray being walked through the grid (layout shared with render.S)
struct Dda {
  uint16_t tmx, tmy;      // +0 +2   depth of the next x / y grid line
  uint16_t tdx, tdy;      // +4 +6   depth between grid lines
  uint8_t ix, iy;         // +8 +9   current cell
  int8_t sx, sy;          // +10 +11 step direction
  uint8_t hmax;           // +12     tallest height class entered so far, plus one
  uint16_t t;             // +13     depth of the last crossing
  uint8_t side;           // +15     0 = crossed an x line, 1 = a y line
  uint8_t cell;           // +16     map byte of the cell entered
} __attribute__((packed));

extern "C" {
  extern uint8_t colbuf[16];        // column scratch: [0..7] high plane, [8..15] low plane
  extern uint16_t view_x, view_y;   // camera position
  // two 16 x 16 cell windows of the map kept in memory: one around the camera,
  // one further along the line of sight. Cells outside both come from flash.
  extern uint8_t win[512];
  extern uint8_t win_x0[2], win_y0[2];
  extern WallJob wall_job;
  extern Dda dda;
  uint8_t cell_flash_c(uint8_t ix, uint8_t iy);
  uint8_t cell_far_c(uint8_t ix, uint8_t iy);
#ifndef HOST
  void ground_asm(uint8_t y0, int16_t rx, int16_t ry);
  void wall_asm(uint8_t y0, uint8_t n);
  uint8_t dda_asm(void);
  int16_t mulhi_su(int16_t a, uint16_t b);
  uint16_t mulhi_uu(uint16_t a, uint16_t b);
#endif
}

#ifndef HOST
static_assert(sizeof(WallJob) == 14, "WallJob layout is shared with render.S");
static_assert(sizeof(Dda) == 17, "Dda layout is shared with render.S");
#endif
static_assert(COLS == 64, "the order in which columns are drawn is worked out for 64 of them");

#define colhi (colbuf)
#define collo (colbuf + 8)

static DrawSprite draw_list[MAX_DRAW];
static uint8_t draw_count;

// The way to go, at the top of the picture. The arrow is the display
// routine's business (platform.h, nav_over). The distance next to it is drawn
// here, into the top 8 rows of its columns: black, with four signs of the
// HUD's lettering in white, two columns of dots to every column of the view.
static uint8_t label_show;          // 0 no label; 1 its place is black; 2 the distance is in it
static uint8_t label_text[4];       // the four signs, as places in the lettering

static int16_t viewFx, viewFy, viewRx, viewRy;   // Q14
static uint16_t view_yaw;
static bool win_valid[2];

static uint8_t prop_list[MAX_PROPS][3];
static uint8_t prop_count;
static uint8_t prop_cx, prop_cy, prop_yaw;
static bool prop_valid;

#ifdef HOST
static uint32_t stat_cells, stat_wall_px, stat_ground_px, stat_far_cells, stat_walls, stat_props, stat_spr_cols;
#define STAT(x) (x)
#else
#define STAT(x)
#endif

#if defined(PROFILE) && !defined(HOST)
static uint32_t prof[6];                  // ground, wall, sky, sprite, column total, setup
#define PROF_BEGIN() uint16_t prof_t0 = TCNT1
#define PROF_END(k) prof[k] += (uint16_t)(TCNT1 - prof_t0)
#else
#define PROF_BEGIN()
#define PROF_END(k)
#endif

// which implementation of the inner loops to run
#ifdef HOST
  #define ASM_ON 0
#elif defined(SELFTEST)
  static bool st_asm;
  static uint16_t st_bad, st_cols;
  #define ASM_ON (st_asm)
#else
  #define ASM_ON 1
#endif

// ------------------------------------------------------------------ math
#ifdef HOST
typedef int32_t int24_t;
static inline int16_t mulhi_su(int16_t a, uint16_t b) { return (int16_t)(((int32_t)a * (int32_t)b) >> 16); }
static inline uint16_t mulhi_uu(uint16_t a, uint16_t b) { return (uint16_t)(((uint32_t)a * b) >> 16); }
#else
typedef __int24 int24_t;
#endif

static NOINLINE int16_t isin(uint16_t a) {
  uint16_t i = a >> 6;                 // 0..1023
  uint8_t q = (uint8_t)(i >> 8);
  uint8_t k = (uint8_t)i;
  int16_t v;
  if (q & 1) v = (int16_t)pgm_read_word(&SIN_Q14[256 - k]);
  else v = (int16_t)pgm_read_word(&SIN_Q14[k]);
  return (q & 2) ? -v : v;
}

static inline int16_t icos(uint16_t a) { return isin(a + 16384u); }

// a * b for a Q14 factor b in -1..1 (b is scaled up so the high word is the answer)
static NOINLINE int16_t mul_q14(int16_t a, int16_t b) {
  bool neg = b < 0;
  uint16_t m = neg ? -b : b;
  m = m >= 16384 ? 65535 : m << 2;
  int16_t r = mulhi_su(a, m);
  return neg ? -r : r;
}

// direction (Q14) times depth (8.8 cells) -> offset in 8.8 cells
static inline int16_t dir_mul(int16_t d, uint16_t t) { return mulhi_su(d, t << 2); }

// normalised reciprocal: 2^24 / x ~ r * 2^(n - 7)
static inline uint16_t recip_m(uint16_t x, uint8_t &n) {
  uint8_t k = 0;
  while (!(x & 0x8000)) { x <<= 1; k++; }
  n = k;
  return pgm_read_word(&RECIP[(uint8_t)(x >> 8) & 0x7F]);
}

// depth travelled per cell crossed, for a ray direction component (Q14) -> 8.8
static NOINLINE uint16_t dir_recip(uint16_t a) {
  if (a < 140) return 0x7FFF;
  uint8_t n;
  uint16_t r = recip_m(a, n);          // 2^22 / a = r * 2^(n - 9)
  if (n >= 9) {
    n -= 9;
    while (n--) { if (r & 0x8000) return 0x7FFF; r <<= 1; }
    return r > 0x7FFF ? 0x7FFF : r;
  }
  if (n == 1) return r >> 8;           // the common case: |component| >= 0.5
  n = 9 - n;
  while (n--) r >>= 1;
  return r;
}

// perspective scale at depth t: screen pixels per cell of height, 10.6
static NOINLINE uint16_t scale_for(uint16_t t) {
  if (t < 20) t = 20;
  uint8_t n;
  uint16_t r = recip_m(t, n);
  uint16_t v = mulhi_uu(r, FY_K16);
  if (n >= 7) { n -= 7; while (n--) v <<= 1; }
  else { n = 7 - n; while (n--) v >>= 1; }
  return v;
}

// height difference (8.8 cells, below 64 cells) at scale s -> pixels
static inline int16_t proj(uint16_t dh, uint16_t s) { return (int16_t)mulhi_uu(dh << 2, s); }

// ------------------------------------------------------------------ map
uint8_t cell_flash_c(uint8_t ix, uint8_t iy) {
  STAT(stat_far_cells++);
  fx_begin(FX_MAP + ((uint24_t)iy << 8) + ix);
  uint8_t b = fx_next();
  fx_end();
  return b;
}

uint8_t cell_far_c(uint8_t ix, uint8_t iy) {
  uint8_t dx = ix - win_x0[1];
  uint8_t dy = iy - win_y0[1];
  if (((dx | dy) & 0xF0) == 0) return win[256 + ((uint8_t)(dy << 4) | dx)];
  return cell_flash_c(ix, iy);
}

static inline uint8_t cell_at(uint8_t ix, uint8_t iy) {
  uint8_t dx = ix - win_x0[0];
  uint8_t dy = iy - win_y0[0];
  if (((dx | dy) & 0xF0) == 0) return win[(uint8_t)(dy << 4) | dx];
  return cell_far_c(ix, iy);
}

static void window_load(uint8_t k, int16_t wx, int16_t wy) {
  if (wx < 0) wx = 0;
  if (wy < 0) wy = 0;
  if (wx > 240) wx = 240;
  if (wy > 240) wy = 240;
  if (win_valid[k]) {
    int16_t dx = wx - win_x0[k], dy = wy - win_y0[k];
    if (dx < 2 && dx > -2 && dy < 2 && dy > -2) return;
  }
  win_x0[k] = (uint8_t)wx;
  win_y0[k] = (uint8_t)wy;
  uint8_t *p = win + (k ? 256 : 0);
  for (uint8_t r = 0; r < 16; r++) {
    fx_read(FX_MAP + ((uint24_t)(uint8_t)(wy + r) << 8) + (uint8_t)wx, p, 16);
    p += 16;
  }
  win_valid[k] = true;
}

static void window_update() {
  int16_t cx = view_x >> 8, cy = view_y >> 8;
  // near window: camera just inside, stretching ahead
  int8_t ox = (int8_t)(viewFx >> 11), oy = (int8_t)(viewFy >> 11);      // -8..8
  if (ox > 7) ox = 7;
  if (ox < -7) ox = -7;
  if (oy > 7) oy = 7;
  if (oy < -7) oy = -7;
  window_load(0, cx - 8 + ox, cy - 8 + oy);
  // far window: centred three window-halves further along the view direction
  window_load(1, cx - 8 + ox * 3, cy - 8 + oy * 3);
}

// ------------------------------------------------------------------ reference inner loops
static void wall_c(uint8_t y0, uint8_t n) {
  const uint8_t *texm = (const uint8_t *)wall_job.texm;
  const uint8_t *texg = (const uint8_t *)wall_job.texg;
  uint8_t top = wall_job.top;
  uint16_t zstep = wall_job.zstep;
  int24_t z = (int24_t)wall_job.z[0] | ((int24_t)wall_job.z[1] << 8) | ((int24_t)(int8_t)wall_job.z[2] << 16);
  uint8_t *p = colbuf + (y0 >> 3);
  uint8_t bm = pgm_read_byte(&BITMASK[y0 & 7]);
  uint8_t ah = p[0], al = p[8];
  uint8_t lastm = 1, lasth = 0;        // a key no pixel can have
  uint8_t lh = 0, ll = 0;
  do {
    uint8_t zm = (uint8_t)(z >> 8) & 0xE0;
    uint8_t zh = (uint8_t)(z >> 16);
    if (zm != lastm || zh != lasth) {
      lastm = zm;
      lasth = zh;
      uint8_t fl = zh;
      uint8_t tv = 7 - (zm >> 5);
      if (fl & 0x80) { fl = 0; tv = 7; }          // rounding took us just below the ground
      uint8_t code;
      if (fl >= top && tv == 0) code = 2;
      else {
        uint8_t b = pgm_read_byte((fl == 0 ? texg : texm) + (tv >> 1));
        code = (tv & 1) ? (b >> 4) : (b & 15);
      }
      uint8_t l = wall_job.lv[code];
      lh = (l & 2) ? 0xFF : 0;
      ll = (l & 1) ? 0xFF : 0;
    }
    ah |= bm & lh;
    al |= bm & ll;
    bm <<= 1;
    if (!bm) {
      p[0] = ah;
      p[8] = al;
      p++;
      ah = p[0];
      al = p[8];
      bm = 1;
    }
    z -= zstep;
  } while (--n);
  p[0] = ah;
  p[8] = al;
}

static void ground_c(uint8_t y0, int16_t rx, int16_t ry) {
  uint8_t lastx = 0, lasty = 0;
  bool have = false;
  const uint8_t *tile = GTILES;
  uint8_t *p = colbuf + (y0 >> 3);
  uint8_t bm = pgm_read_byte(&BITMASK[y0 & 7]);
  uint8_t ah = p[0], al = p[8];
  const uint16_t *tp = &GROUND_T4[y0 - HORIZON - 1];
  uint8_t n = ROWS - y0;
  do {
    uint16_t t4 = pgm_read_word(tp++);
    uint16_t wx = view_x + (uint16_t)mulhi_su(rx, t4);
    uint16_t wy = view_y + (uint16_t)mulhi_su(ry, t4);
    uint8_t ix = (uint8_t)(wx >> 8), iy = (uint8_t)(wy >> 8);
    if (!have || ix != lastx || iy != lasty) {
      have = true;
      lastx = ix;
      lasty = iy;
      uint8_t b = cell_at(ix, iy);
      uint8_t ti;
      if (b & 0x80) ti = TILE_PLAIN_ROAD;
      else {
        ti = pgm_read_byte(&GTILE_LUT[b]);
        if ((b & 0xF3) == 0x22) {            // dashed lane line: only in every other cell
          uint8_t along = (b & 0x04) ? ix : iy;
          if (along & 1) ti = TILE_PLAIN_ROAD;
        }
      }
      tile = &GTILES[(uint16_t)ti * 16];
    }
    uint8_t um = pgm_read_byte(&BITMASK[(uint8_t)wx >> 5]);
    const uint8_t *row = tile + (((uint8_t)wy >> 4) & 0x0E);
    if (pgm_read_byte(row) & um) ah |= bm;
    if (pgm_read_byte(row + 1) & um) al |= bm;
    bm <<= 1;
    if (!bm) {
      p[0] = ah;
      p[8] = al;
      p++;
      ah = p[0];
      al = p[8];
      bm = 1;
    }
  } while (--n);
  p[0] = ah;
  p[8] = al;
}

static uint8_t dda_c() {
  for (;;) {
    uint16_t t;
    uint8_t side;
    if (dda.tmx < dda.tmy) {
      t = dda.tmx; dda.tmx += dda.tdx; side = 0;
      dda.ix += dda.sx;
    } else {
      t = dda.tmy; dda.tmy += dda.tdy; side = 1;
      dda.iy += dda.sy;
    }
    dda.t = t;
    dda.side = side;
    if ((uint8_t)(t >> 8) >= MAXD_CELLS) { dda.cell = 0; return 0; }
    STAT(stat_cells++);
    uint8_t b = cell_at(dda.ix, dda.iy);
    dda.cell = b;
    if (!(b & 0x80)) continue;
    if (b == CELL_EDGE) return 0;
    uint8_t hc = ((b >> 3) & 15) + 1;
    if (hc <= dda.hmax) continue;
    dda.hmax = hc;
    return 1;
  }
}

static inline void ground_run(uint8_t y0, int16_t rx, int16_t ry) {
  STAT(stat_ground_px += ROWS - y0);
#ifndef HOST
  if (ASM_ON) { ground_asm(y0, rx, ry); return; }
#endif
  ground_c(y0, rx, ry);
}

static inline void wall_run(uint8_t y0, uint8_t n) {
  STAT(stat_wall_px += n);
  STAT(stat_walls++);
#ifndef HOST
  if (ASM_ON) { wall_asm(y0, n); return; }
#endif
  wall_c(y0, n);
}

static inline uint8_t dda_run() {
#ifndef HOST
  if (ASM_ON) return dda_asm();
#endif
  return dda_c();
}

// ------------------------------------------------------------------ column pieces
static NOINLINE void draw_wall(uint8_t y0, uint8_t y1, uint16_t t, uint8_t cellb, uint8_t u3, uint8_t side, uint8_t hk) {
  uint8_t style = cellb & 7;
  wall_job.top = pgm_read_byte(&HEIGHT_FLOORS[(cellb >> 3) & 15]) - 1;
  uint8_t pal = pgm_read_byte(&WALLPAL[(uint8_t)(style * 2 + side)]);
  uint8_t tc = (uint8_t)(t >> 8);
  uint8_t band = tc < FOG_T0 ? 0 : tc < FOG_T1 ? 1 : tc < FOG_T2 ? 2 : tc < FOG_T3 ? 3 : 4;
  uint8_t fog = pgm_read_byte(&FOGMAP[band]);
  for (uint8_t c = 0; c < 4; c++) {
    uint8_t l = pal & 3;
    pal >>= 2;
    uint8_t f = fog;
    while (l--) f >>= 2;
    wall_job.lv[c] = f & 3;
  }
  const uint8_t *texm = &WALLTEX8[(uint8_t)(style * 8 + u3) * 4];
  uint8_t gs = pgm_read_byte(&GROUNDSEL[(uint8_t)(style * 4 + hk)]);
  const uint8_t *texg = gs ? &GFTEX8[(uint8_t)((gs - 1) * 8 + u3) * 4] : texm;
#ifdef HOST
  wall_job.texm = texm;
  wall_job.texg = texg;
#else
  wall_job.texm = (uint16_t)texm;
  wall_job.texg = (uint16_t)texg;
#endif

  // height above ground of each pixel, stepping down the wall: 8.16 cells
  uint16_t zstep = t * ZSTEP_INT + mulhi_uu(t, ZSTEP_FRAC);
  int16_t d2 = 2 * ((int16_t)y0 - HORIZON) + 1;
  int32_t z = ((int32_t)CAM_H << 8) - (((int32_t)d2 * zstep) >> 1);
  wall_job.zstep = zstep;
  wall_job.z[0] = (uint8_t)z;
  wall_job.z[1] = (uint8_t)(z >> 8);
  wall_job.z[2] = (uint8_t)(z >> 16);
  wall_run(y0, y1 - y0);
}

static NOINLINE void draw_sky(uint8_t ytop, uint8_t c) {
  if (ytop == 0) return;
  uint8_t pc = ((uint8_t)(view_yaw >> 8) + (uint8_t)pgm_read_byte(&SKYOFF[c])) & 63;
  const uint8_t *sky = &SKY[(uint16_t)pc * 6];
  for (uint8_t j = 0; j < 3; j++) {
    uint8_t base = j << 3;
    if (ytop <= base) break;
    uint8_t n = ytop - base;
    uint8_t m = n >= 8 ? 0xFF : (uint8_t)((1 << n) - 1);
    colhi[j] |= pgm_read_byte(sky + j) & m;
    collo[j] |= pgm_read_byte(sky + 3 + j) & m;
  }
}

static NOINLINE void draw_sprite_column(const DrawSprite &s, uint8_t sc) {
  uint8_t hb = (uint8_t)(s.h + 7) >> 3;       // bytes per bit plane per column
  uint8_t buf[24];
  uint8_t n = hb * 3;
  STAT(stat_spr_cols++);
  fx_read(s.addr + (uint24_t)((uint16_t)sc * n), buf, n);
  int8_t r0 = s.r0;
  uint8_t sh = (uint8_t)r0 & 7;
  int8_t b0 = r0 >> 3;                 // arithmetic shift: floor for negative rows
  for (uint8_t j = 0; j < hb; j++) {
    uint16_t m = (uint16_t)buf[j] << sh;
    if (!m) continue;
    uint16_t hi = (uint16_t)buf[hb + j] << sh;
    uint16_t lo = (uint16_t)buf[2 * hb + j] << sh;
    int8_t bi = b0 + j;
    if (bi >= 0 && bi < COLBYTES) {
      colhi[bi] = (colhi[bi] & ~(uint8_t)m) | (uint8_t)hi;
      collo[bi] = (collo[bi] & ~(uint8_t)m) | (uint8_t)lo;
    }
    bi++;
    if (bi >= 0 && bi < COLBYTES) {
      uint8_t mh = (uint8_t)(m >> 8);
      colhi[bi] = (colhi[bi] & ~mh) | (uint8_t)(hi >> 8);
      collo[bi] = (collo[bi] & ~mh) | (uint8_t)(lo >> 8);
    }
  }
}

// the distance to go, if this column is one of its own
static void label_column(uint8_t c) {
  c -= NAV_BOX_C0;
  if (c >= NAV_BOX_COLS) return;
  uint8_t dots[2];
  for (uint8_t i = 0; i < 2; i++) {
    // the lettering begins two dots in: three columns a sign, and one between
    uint8_t q = (uint8_t)(c * 2 + i - 2);
    uint8_t v = 0;
    if (label_show > 1 && q < 16 && (q & 3) != 3)
      v = pgm_read_byte(&FONT[(uint8_t)(label_text[q >> 2] * 3 + (q & 3))]) << 1;
    dots[i] = v;
  }
  colhi[0] = dots[0];
  collo[0] = dots[1];
}

// ------------------------------------------------------------------ one column
static NOINLINE void render_column(uint8_t c) {
  for (uint8_t i = 0; i < 16; i++) colbuf[i] = 0;

  // The direction of this column's ray, how far to the side for one ahead
  // (Q14): in even steps from the middle of the picture to its edges, so it
  // is worked out, not looked up. tools/build_assets.py has found the
  // numbers that give to the last bit what a table would hold.
  bool left = c < COLS / 2;
  uint8_t m = left ? (uint8_t)(COLS - 1 - 2 * c) : (uint8_t)(2 * c - (COLS - 1));
  int16_t tn = (int16_t)(m * TANC_A) - (uint8_t)((uint16_t)(m * TANC_B + TANC_C) >> 8);
  if (left) tn = -tn;
#if defined(SELFTEST) && !defined(HOST)
  if (tn != (int16_t)pgm_read_word(&TANC_Q14[c])) st_bad++;
#endif
  int16_t rx = viewFx + mul_q14(viewRx, tn);
  int16_t ry = viewFy + mul_q14(viewRy, tn);

  uint8_t fx = (uint8_t)view_x, fy = (uint8_t)view_y;
  uint16_t dist, a;
  dda.ix = (uint8_t)(view_x >> 8);
  dda.iy = (uint8_t)(view_y >> 8);
  if (rx >= 0) { dda.sx = 1; a = rx; dist = 256 - fx; } else { dda.sx = -1; a = -rx; dist = fx; }
  dda.tdx = dir_recip(a);
  dda.tmx = dist == 256 ? dda.tdx : mulhi_uu(dda.tdx, dist << 8);
  if (ry >= 0) { dda.sy = 1; a = ry; dist = 256 - fy; } else { dda.sy = -1; a = -ry; dist = fy; }
  dda.tdy = dir_recip(a);
  dda.tmy = dist == 256 ? dda.tdy : mulhi_uu(dda.tdy, dist << 8);
  dda.hmax = 0;

  uint8_t ytop = HORIZON;          // rows [0, ytop) are still empty (sky) when we finish
  uint8_t gtop = HORIZON + 1;      // ground occupies rows [gtop, ROWS)
  uint8_t wall_depth = 255;        // quarter cells, for sprite occlusion
  bool hit = false;

  while (dda_run()) {
    uint16_t t = dda.t;
    uint16_t s = scale_for(t);
    if (!hit) {
      hit = true;
      wall_depth = (uint8_t)(t >> 6);
      int16_t yb = HORIZON + 1 + proj(CAM_H, s);
      if (yb > ROWS) yb = ROWS;
      gtop = (uint8_t)yb;
      ytop = gtop;
    }
    uint16_t dh = ((uint16_t)pgm_read_byte(&HEIGHT_FLOORS[dda.hmax - 1]) << 8) - CAM_H;
    int16_t yw = HORIZON - proj(dh, s);
    if (yw < 0) yw = 0;
    if (yw < ytop) {
      uint16_t hp = dda.side ? (uint16_t)(view_x + (uint16_t)dir_mul(rx, t))
                             : (uint16_t)(view_y + (uint16_t)dir_mul(ry, t));
      uint8_t hk = (uint8_t)(dda.ix * 7 + dda.iy * 13) & 3;
      { PROF_BEGIN(); draw_wall((uint8_t)yw, ytop, t, dda.cell, (uint8_t)hp >> 5, dda.side, hk); PROF_END(1); }
      ytop = (uint8_t)yw;
      if (ytop == 0) break;
    }
  }
  if (!hit) {
    // open view to the horizon: one row of haze where ground meets sky
    colhi[HORIZON >> 3] |= (uint8_t)(1 << (HORIZON & 7));
  }
  if (gtop < ROWS) { PROF_BEGIN(); ground_run(gtop, rx, ry); PROF_END(0); }
  { PROF_BEGIN(); draw_sky(ytop, c); PROF_END(2); }

  for (uint8_t i = 0; i < draw_count; i++) {
    const DrawSprite &s = draw_list[i];
    int8_t sc = (int8_t)c - s.c0;
    if (sc < 0 || (uint8_t)sc >= s.w) continue;
    if (s.depth >= wall_depth) continue;
    { PROF_BEGIN(); draw_sprite_column(s, (uint8_t)sc); PROF_END(3); }
  }
  if (label_show) label_column(c);
}

// ------------------------------------------------------------------ sprites
static uint8_t size_index(uint16_t t) {
  // k = 6*log2(t in cells) + offset
  uint8_t n = 0;
  uint16_t x = t;
  while (!(x & 0x8000)) { x <<= 1; n++; }
  int8_t e = (int8_t)(15 - n) - 8;                    // exponent of t in cells
  uint8_t m = (uint8_t)(x >> 11) & 15;                // 4 mantissa bits
  int16_t k = (int16_t)e * 6 + pgm_read_byte(&LOG6[m]);
  k = k * 16 + SIZE_KOFF_X16 + 8;
  k >>= 4;
  if (k < 0) k = 0;
  if (k > N_SIZES - 1) k = N_SIZES - 1;
  return (uint8_t)k;
}

// Put one picture of the sprite index into the draw list: its origin goes to
// column colc, row base of the view.
static void draw_put(uint16_t entry, int16_t colc, int16_t base, uint8_t depth) {
  uint8_t h[7];
  fx_read(FX_SPRITE_INDEX + (uint24_t)entry * 7, h, 7);
  uint24_t off = h[0] | ((uint24_t)h[1] << 8) | ((uint24_t)h[2] << 16);

  int16_t c0 = colc - h[5];
  int16_t r0 = base - h[6];
  if (c0 >= COLS || c0 + h[3] <= 0) return;
  if (r0 >= ROWS || r0 + h[4] <= 0) return;
  if (c0 < -120 || r0 < -120) return;

  DrawSprite d;
  d.c0 = (int8_t)c0;
  d.r0 = (int8_t)r0;
  d.w = h[3];
  d.h = h[4];
  d.depth = depth;
  d.addr = FX_SPRITE_DATA + off;

  if (draw_count >= MAX_DRAW) {
    // the farthest one makes room
    for (uint8_t k = 1; k < MAX_DRAW; k++) draw_list[k - 1] = draw_list[k];
    draw_count--;
  }
  // keep the list sorted far to near
  uint8_t i = draw_count++;
  while (i > 0 && draw_list[i - 1].depth < d.depth) {
    draw_list[i] = draw_list[i - 1];
    i--;
  }
  draw_list[i] = d;
}

static void draw_add(const Entity &e) {
  int16_t qx = (int16_t)(e.x - view_x);
  int16_t qy = (int16_t)(e.y - view_y);
  if (qx > SPRITE_MAXD || qx < -SPRITE_MAXD || qy > SPRITE_MAXD || qy < -SPRITE_MAXD) return;
  int16_t t = mul_q14(qx, viewFx) + mul_q14(qy, viewFy);
  if (t < 90 || t > SPRITE_MAXD) return;
  // a full list only takes what is nearer than the farthest thing in it
  if (draw_count >= MAX_DRAW && (uint8_t)((uint16_t)t >> 6) >= draw_list[0].depth) return;
  int16_t lat = mul_q14(qx, viewRx) + mul_q14(qy, viewRy);
  int16_t lim = t + (t >> 1);
  if (lat > lim || lat < -lim) return;
  uint16_t s = scale_for((uint16_t)t);
  // lat (8.8 cells) * s (10.6 px per cell) = Q14 pixels; two pixels per column
  int16_t colc = COLS / 2 + (mulhi_su(lat, s) << 1);
  int16_t base = HORIZON + 1 + proj(CAM_H, s);

  const uint8_t *st = &SPRITE_SETS[(uint16_t)e.set * 4];
  uint8_t angles = pgm_read_byte(st), nsizes = pgm_read_byte(st + 1);
  uint16_t first = pgm_read_byte(st + 2) | ((uint16_t)pgm_read_byte(st + 3) << 8);

  int16_t cc = colc < 0 ? 0 : colc > COLS - 1 ? COLS - 1 : colc;
  uint8_t viewyaw = (uint8_t)(view_yaw >> 8) + (uint8_t)pgm_read_byte(&SKYOFF[cc]);
  uint8_t rel = viewyaw - (uint8_t)(e.hd >> 8);
  uint8_t a = 0;
  if (angles > 1) {
    uint16_t v = (uint16_t)rel * angles + 128;
    a = (uint8_t)(v >> 8);
    if (a >= angles) a -= angles;
  }
  uint8_t k = nsizes > 1 ? size_index((uint16_t)t) : 0;
  if (k >= nsizes) k = nsizes - 1;
  draw_put(first + (uint16_t)a * nsizes + k, colc, base, (uint8_t)((uint16_t)t >> 6));
}

static void view_begin(const Camera &cam) {
  view_x = cam.x;
  view_y = cam.y;
  view_yaw = cam.yaw;
  int16_t s = isin(cam.yaw), c = icos(cam.yaw);
  viewFx = s;
  viewFy = -c;
  viewRx = c;
  viewRy = s;
  window_update();
  draw_count = 0;
}

// Collect the nearest trees and lamps ahead of the camera. They never move, so
// the list is rebuilt only when the camera has travelled or turned a fair bit.
static void props_gather() {
  uint8_t pcx = (uint8_t)(view_x >> 8), pcy = (uint8_t)(view_y >> 8);
  int8_t f8x = (int8_t)(viewFx >> 8), f8y = (int8_t)(viewFy >> 8);      // -64..64
  uint8_t best[MAX_PROPS];
  prop_count = 0;
  for (int8_t dy = -1; dy <= 1; dy++) {
    for (int8_t dx = -1; dx <= 1; dx++) {
      // (one off the edge of the map is 255 or 16)
      uint8_t chx = (uint8_t)((pcx >> 4) + dx), chy = (uint8_t)((pcy >> 4) + dy);
      if (chx > 15 || chy > 15) continue;
      uint8_t e[4];
      fx_read(FX_PROP_TABLE + (uint16_t)((uint8_t)(chy * 16 + chx)) * 4, e, 4);
      uint24_t off = e[0] | ((uint24_t)e[1] << 8) | ((uint24_t)e[2] << 16);
      uint8_t n = e[3];
      if (n > PROP_CHUNK_MAX) n = 0;          // not our data: never trust a count
      for (uint8_t i0 = 0; i0 < n; i0 += 8) {
        // read a handful at a time so interrupts are never held off for long
        uint8_t buf[24];
        uint8_t m = n - i0 > 8 ? 8 : n - i0;
        fx_read(FX_PROP_DATA + off + (uint24_t)i0 * 3, buf, m * 3);
        for (uint8_t i = 0; i < m; i++) {
          STAT(stat_props++);
          uint8_t *p = buf + i * 3;
          int8_t ddx = (int8_t)(p[1] - pcx), ddy = (int8_t)(p[2] - pcy);
          if (ddx > 20 || ddx < -20 || ddy > 20 || ddy < -20) continue;
          int16_t fwd = (int16_t)ddx * f8x + (int16_t)ddy * f8y;        // cells * 64
          int16_t side = (int16_t)ddx * f8y - (int16_t)ddy * f8x;
          if (side < 0) side = -side;
          if (fwd < -64) continue;                                       // behind us
          if (side > fwd + (fwd >> 1) + 320) continue;                   // outside a generous cone
          uint8_t d = (uint8_t)((fwd < 0 ? 0 : fwd) >> 6) + (uint8_t)(side >> 7);
          // insert by distance, nearest first
          uint8_t k = prop_count;
          if (k == MAX_PROPS) {
            if (d >= best[k - 1]) continue;
            k--;
          } else prop_count++;
          while (k > 0 && best[k - 1] > d) {
            best[k] = best[k - 1];
            prop_list[k][0] = prop_list[k - 1][0];
            prop_list[k][1] = prop_list[k - 1][1];
            prop_list[k][2] = prop_list[k - 1][2];
            k--;
          }
          best[k] = d;
          prop_list[k][0] = p[0];
          prop_list[k][1] = p[1];
          prop_list[k][2] = p[2];
        }
      }
    }
  }
  prop_cx = pcx;
  prop_cy = pcy;
  prop_yaw = (uint8_t)(view_yaw >> 8);
  prop_valid = true;
}

static void view_props() {
  uint8_t pcx = (uint8_t)(view_x >> 8), pcy = (uint8_t)(view_y >> 8);
  int8_t mx = (int8_t)(pcx - prop_cx), my = (int8_t)(pcy - prop_cy);
  int8_t dyaw = (int8_t)((uint8_t)(view_yaw >> 8) - prop_yaw);
  if (!prop_valid || mx > 2 || mx < -2 || my > 2 || my < -2 || dyaw > 12 || dyaw < -12)
    props_gather();
  for (uint8_t i = 0; i < prop_count; i++) {
    uint8_t k = prop_list[i][0];
    Entity en;
    en.x = ((uint16_t)prop_list[i][1] << 8) | ((k & 0x0C) << 4) | 0x20;
    en.y = ((uint16_t)prop_list[i][2] << 8) | ((k & 0x03) << 6) | 0x20;
    en.hd = 0;
    en.set = SPR_TREE + (k >> 4);           // a tree, a lamp, a telephone box
    en.flags = 0;
    draw_add(en);
  }
}

static void view_render() {
  for (uint8_t k = 0; k < COLS; k++) {
    // the even columns first, then the odd ones: a picture arrives in two passes
    uint8_t c = (uint8_t)((k << 1) & (COLS - 1)) | (k >> 5);
#if defined(SELFTEST) && !defined(HOST)
    // draw the column with the reference code, then with the assembly, and compare
    uint8_t ref[16];
    st_asm = false;
    render_column(c);
    for (uint8_t i = 0; i < 16; i++) ref[i] = colbuf[i];
    st_asm = true;
    render_column(c);
    bool same = true;
    for (uint8_t i = 0; i < 16; i++) if (ref[i] != colbuf[i]) same = false;
    st_cols++;
    if (!same) st_bad++;
#else
    { PROF_BEGIN(); render_column(c); PROF_END(4); }
#endif
    fb_commit(c, colhi, collo);
  }
}

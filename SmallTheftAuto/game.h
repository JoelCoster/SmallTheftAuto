// Small Theft Auto - game logic (on foot and in cars, a pistol, people who run,
// cash to pick up, and the police).
//
// The simulation is flat: everything lives on the 2D city grid. Time is counted
// in display plane ticks (156 per second) so movement speed does not depend on
// how fast frames are drawn.
//
// The player is either on foot or driving. Every other car in the world sits in
// one small pool: traffic, cars the city parked, and cars the player left
// behind. Getting into a car takes it out of the pool; getting out puts the
// player's car into it.
//
// Buttons: B is the upper of the two, the one the thumb finds first. It does
// the main thing: the accelerator in a car, the trigger on foot.
//
// The police: what the player does wrong goes on a record, and the stars in
// the HUD follow from it. Police cars are traffic of their own kind that goes
// after the player instead of along the lanes; an officer is somebody on foot
// of their own kind who runs towards the player instead of away.
//
// The way to go: a place picked on the map (pages.h). An arrow at the top of
// the picture points to it, as the crow flies, and says how far it is.
//
// Missions: a telephone that rings has one to offer. What a mission asks for
// is not in the program: it is on the flash chip, step by step
// (tools/missions.py), and the program reads a step, waits until what it
// asks for has happened, and reads the next.
#pragma once

#include "engine.h"

#define N_CARS 12
#define MAX_TRAFFIC 7
#define N_PEDS 16
#define N_TAKEN 4

// what a slot of the car pool holds
#define CAR_FREE 0
#define CAR_TRAFFIC 1        // driving along the lanes
#define CAR_PARKED 2         // standing where the city put it
#define CAR_LEFT 3           // standing where the player left it

#define PED_FREE 0
#define PED_WALK 1
#define PED_RUN 2            // frightened: gets away from the player
#define PED_DOWN 3           // run over or shot
#define PED_CASH 0x40        // down, and what they carried is still there
#define PED_MARK 0x80        // the one a mission is about
#define PED_COP (N_PED_KINDS - 1)   // the kind that is a police officer; to them, running is going after the player

#define PAGE_GAME 0
#define PAGE_TITLE 1
#define PAGE_MAP 2
#define PAGE_SETTINGS 3
#define PAGE_JOB 4           // a telephone has been answered: what the mission is

#define NONE 0xFF

#define HEALTH 16            // full health: the dots of the bar in the HUD
#define CHASE_SPEED 160      // a police car that is after the player (traffic does 56 to 87)
// How long the police has not known where the player is, in steps of 16
// frames (0.7 s). Somebody calling them starts the clock at 0: they have to
// get there first. Seeing the player puts it to CALM_SEEN: they are there.
#define CALM_SEEN 6
#define CALM_LOST 12         // from here on they have lost the player: nobody goes after them, nobody new is sent
#define CALM_STAR 18         // and at this point a star is forgotten; the clock goes back to CALM_LOST
#define SIGHT (8 * 256)      // how far the police sees, streets added up
// An officer has to hold on to the player for this many frames to arrest
// them: time enough to run, or to turn round and shoot.
#define GRIP_BUSTED 45
#define COP_SPEED 450        // slower than the player runs (525), so whoever keeps moving gets away
#define NAV_THERE 12         // metres: this near to where the arrow leads counts as there
#define PHONE_REACH 300      // this near to a telephone it can be answered (as near as to a car to get in)
#define PHONE_HEARD (7 * 256)       // and from here it is heard
#define MARK_NEAR (12 * 256)        // whoever a mission is about is there when the player gets this near
#define NOTE_FRAMES 80       // how long MISSION PASSED stays in the picture

struct Hero {
  uint16_t x, y;       // 8.8 cells
  uint16_t hd;         // heading, 65536 = full turn, 0 = north, clockwise
  int16_t speed;       // 8.8 cells per 256 ticks  (20 m/s = 5 cells/s ~ 2100)
};

struct Car {
  uint16_t x, y;       // 8.8 cells
  uint8_t hd;          // heading, 256 = full turn
  uint8_t what;        // bits 0..1 CAR_*, bits 2..4 kind, bits 5..6 compass direction driven
  uint8_t speed;       // traffic: cruising speed, in steps of 16
  uint8_t wait;        // traffic: how long it has been held up, in steps of 4 frames;
                       // police after the player: frames to get over a crash
};

// what a mission asks for just now, as it is on the flash chip
struct Step {
  uint8_t op;          // STEP_GO, STEP_KILL, STEP_LOSE or STEP_END, and on top of it STEP_CAR ...
  uint8_t x, y;        // the place, in cells; x 0: none
  uint8_t n;           // how many people; STEP_CAR: the kind of car
  uint8_t time;        // the clock is set to this when the step begins, in steps of 256 ticks; 0: it is left alone
  uint8_t record;      // the player has at least this on their record when it begins (so many stars)
  uint8_t who;         // STEP_MARK: the kind of person it is about
};

// what is kept when the console is switched off (as it is on the flash chip)
struct Kept {
  uint8_t settings;          // SET_*: what the player has chosen on the settings page
  uint16_t cash;             // dollars
  uint8_t done[N_PHONES];    // how many of its missions every telephone has seen done
};

struct Ped {
  uint16_t x, y;       // 8.8 cells
  uint8_t what;        // bits 0..1 compass direction, bits 2..3 kind, bits 4..5 PED_*, bit 6 PED_CASH, bit 7 PED_MARK
  uint8_t timer;       // running: frames left; down: frames left, in steps of 4;
                       // an officer: frames until the next shot
};

static Hero hero;
static Car cars[N_CARS];
static Ped peds[N_PEDS];
static uint8_t taken[N_TAKEN][2];   // parking spots the player emptied: they stay empty
static uint8_t taken_next;
static bool on_foot;
static uint8_t hero_kind;           // the car being driven
static uint8_t walked;              // on foot: distance covered, for the step of the walk (four to a cell)
static uint8_t reach;               // on foot: the car that DOWN would get into, or NONE
static uint8_t held;                // buttons that must be let go before they count again
static uint8_t gun_wait;            // ticks until the pistol fires again
static uint8_t shot_show;           // frames the last shot stays in the picture
static uint16_t shot_x, shot_y;     // where it struck
static Kept kept;
static uint16_t &cash = kept.cash;
static uint8_t &settings = kept.settings;
static uint8_t health;              // HEALTH down to 0
static uint8_t hurt;                // frames the heart in the HUD blinks
static uint8_t crime;               // what the player has on the record
static uint8_t wanted;              // the stars that makes, 0 to 4
static uint8_t calm;                // how long no police has seen the player, in steps of 16 frames
static uint16_t seen_x, seen_y;     // where they saw the player last: that is where they go
static uint8_t cops;                // officers on foot who are after the player
static uint8_t grip;                // how long an officer has had hold of the player, in frames
static uint8_t over;                // frames left of WASTED or BUSTED; 0 while the game is on
static uint8_t over_set;            // which of the two: the sprite set of its lettering
static uint8_t nav_x, nav_y;        // where the player wants to go, in cells; nav_x 0: nowhere
static uint8_t nav_way;             // which of the 32 arrows is on the screen, NONE: none yet
static bool nav_near;               // the player is where the arrow leads
static uint8_t job = NONE;          // the mission that is on; NONE: none
static uint8_t job_at;              // which of its steps
static Step step;                   // what that step asks for
static uint8_t job_left;            // people still to go
static uint16_t job_clock;          // ticks left; 0: no mission is on
static bool job_fit;                // the player is in the car the step asks for, if it asks for one
static bool job_seen;               // whoever the step is about is in the game
static uint8_t job_from;            // the telephone it came from
static uint16_t job_paid;           // what the last one paid
static uint8_t phone = NONE;        // the telephone within reach, if it rings
static uint8_t note;                // frames left of MISSION PASSED or MISSION FAILED
static uint8_t note_set;            // which of the two: the sprite set of its lettering
static uint8_t page;                // what is on the screen: the game (0), or one of the pages (pages.h)
static uint8_t text_band = 7;       // where lettering goes: a band of 8 rows of a page (0 to 6), or the HUD (7)
static Camera cam;
static uint16_t cam_yaw;
static int8_t cam_side;             // how far to the right of the player the camera is
static int8_t cam_shoulder;         // on foot: where it wants to be, +CAM_SIDE or -CAM_SIDE
static uint16_t last_tick;
static uint16_t rng_state = 0xACE1;
static uint8_t fps_frames, fps_value;
static uint16_t fps_mark;
static uint16_t frame_ticks;
static uint16_t frames_total;       // frames drawn since start
static uint8_t flash_fails;         // times the flash chip did not answer with our data, at the start
#ifdef DIAG
// buttons held down by the computer, which puts them straight into memory:
// nothing in the program ever writes this
volatile uint8_t diag_buttons __attribute__((used));
#endif

static inline uint8_t car_state(const Car &c) { return c.what & 3; }
static inline uint8_t car_kind(const Car &c) { return (c.what >> 2) & 7; }
static inline uint8_t car_dir(const Car &c) { return (c.what >> 5) & 3; }
static inline uint8_t ped_state(const Ped &p) { return (p.what >> 4) & 3; }

static uint8_t rnd8() {
  uint16_t s = rng_state;
  s ^= s << 7;
  s ^= s >> 9;
  s ^= s << 8;
  rng_state = s;
  return (uint8_t)s;
}

static inline bool is_building(uint8_t b) { return b & 0x80; }
static inline bool is_road(uint8_t b) { return (b & 0xF0) == 0x20; }
static inline bool is_water(uint8_t b) { return (b & 0xF0) == 0x30; }
static inline bool is_pavement(uint8_t b) { return (b & 0xF0) == 0x10; }
static inline bool is_lot(uint8_t b) { return (b & 0xF0) == 0x60; }
// where people walk by themselves: pavement and squares
static inline bool is_walk(uint8_t b) { return (b & 0xF0) == 0x10 || (b & 0xF0) == 0x40; }
static inline bool is_wall(uint8_t b) { return is_building(b) || is_water(b); }

// a step north, east, south, west (0 to 3): how far east, and how far south,
// which is how far east three further on in the same list
static const int8_t DIRX[7] PROGMEM = {0, 1, 0, -1, 0, 1, 0};
static NOINLINE int8_t dir_x(uint8_t d) { return (int8_t)pgm_read_byte(&DIRX[d]); }
static NOINLINE int8_t dir_y(uint8_t d) { return dir_x(d + 3); }

// move (dx, dy) = heading * distance
static void advance(uint16_t &x, uint16_t &y, uint16_t hd, int16_t dist) {
  x += mul_q14(isin(hd), dist);
  y -= mul_q14(icos(hd), dist);
}

static NOINLINE int16_t iabs(int16_t v) { return v < 0 ? -v : v; }

// how far from the player, counted along the streets; far away counts as 32767
static int16_t apart(uint16_t x, uint16_t y) {
  int16_t dx = iabs((int16_t)(x - hero.x)), dy = iabs((int16_t)(y - hero.y));
  if (dx > 16000 || dy > 16000) return 32767;
  return dx + dy;
}

// ------------------------------------------------------------------ the law
// On the record: a shot 1, a car taken from its driver or shot at 2, somebody
// killed 4, an officer 16. 1 star from 8 on the record, 2 from 24, 3 from 56,
// 4 from 120.
static void stars_update() {
  uint8_t k = (crime >> 3) + 1, stars = 0;
  while (k >>= 1) stars++;
  wanted = stars > 4 ? 4 : stars;
}

// the police knows where the player is
static void seen(uint8_t clock) {
  calm = clock;
  seen_x = hero.x;
  seen_y = hero.y;
}

static void crime_add(uint8_t n) {
  uint8_t c = crime + n;
  if (c < n) c = 255;
  crime = c;
  seen(0);                          // somebody calls them and says where
  stars_update();
}

static void game_over(uint8_t set) {
  if (over) return;
  over = 110;
  over_set = set;
  sound_play(SOUND_OVER);
}

static void hurt_by(uint8_t n) {
  if (over) return;
  hurt = 12;
  if (health > n) {
    health -= n;
    sound_play(SOUND_HURT);
    return;
  }
  health = 0;
  game_over(SPR_WASTED);
}

// slow enough to be stopped by somebody on foot
static bool hero_slow() {
  return on_foot || (hero.speed < 500 && hero.speed > -500);
}

// is there a building between the player and this place?
static bool hidden(uint16_t x, uint16_t y) {
  int16_t dx = (int16_t)(x - hero.x) >> 3, dy = (int16_t)(y - hero.y) >> 3;
  uint16_t px = hero.x, py = hero.y;
  for (uint8_t i = 0; i < 7; i++) {
    px += dx;
    py += dy;
    if (is_building(cell_at((uint8_t)(px >> 8), (uint8_t)(py >> 8)))) return true;
  }
  return false;
}

// The police at this place has the player in sight, if near enough and with
// nothing in between: as long as that happens, no star is forgotten. Out of
// sight, the police goes to where the player was seen last, and after a
// while gives up.
static void police_at(uint16_t x, uint16_t y, int16_t far) {
  if (far < SIGHT && !hidden(x, y)) seen(CALM_SEEN);
}

// ------------------------------------------------------------------ cars as obstacles
// Is the point inside the footprint of this car? The footprint is a box along
// the compass direction nearest to the car's heading, a little wider than the
// car so that two cars side by side do not overlap in the picture.
static bool in_car(const Car &c, uint16_t x, uint16_t y) {
  int16_t dx = iabs((int16_t)(x - c.x)), dy = iabs((int16_t)(y - c.y));
  uint8_t o = (uint8_t)(c.hd + 16) >> 5;          // eighth of a turn
  uint8_t ex = 100, ey = 150;                     // facing north or south
  if (o & 1) ex = ey = 120;                       // diagonal: roughly round
  else if (o & 2) { ex = 150; ey = 100; }         // facing east or west
  return dx < ex && dy < ey;
}

static uint8_t car_at(uint16_t x, uint16_t y) {
  for (uint8_t i = 0; i < N_CARS; i++)
    if (car_state(cars[i]) != CAR_FREE && in_car(cars[i], x, y)) return i;
  return NONE;
}

// A tree or a lamp post? Only the ones the renderer has gathered are known,
// which are the ones in front of the camera: where the player is heading.
// Lamp posts stop people only; a car that stopped dead at every post it
// brushes would be no fun to drive.
static bool prop_at(uint16_t x, uint16_t y) {
  for (uint8_t i = 0; i < prop_count; i++) {
    uint8_t k = prop_list[i][0];
    int16_t r = 45;
    if ((k >> 4) != PROP_TREE) {
      if (!on_foot) continue;
      r = 30;
    }
    uint16_t px = ((uint16_t)prop_list[i][1] << 8) | ((k & 0x0C) << 4) | 0x20;
    uint16_t py = ((uint16_t)prop_list[i][2] << 8) | ((k & 0x03) << 6) | 0x20;
    if (iabs((int16_t)(x - px)) < r && iabs((int16_t)(y - py)) < r) return true;
  }
  return false;
}

// something neither a car nor a person gets through
static bool solid(uint16_t x, uint16_t y) {
  if (is_wall(cell_at((uint8_t)(x >> 8), (uint8_t)(y >> 8)))) return true;
  return car_at(x, y) != NONE || prop_at(x, y);
}

// ------------------------------------------------------------------ HUD
static void page_frame(uint8_t btn, uint8_t fresh);
#ifdef PROBE
static uint8_t probe_buttons(uint16_t now);
#endif
static void page_open(uint8_t which);

static void hud_clear() {
  for (uint8_t i = 0; i < 128; i++) hud[i] = 0;
}

// one column of dots of a page: 7 bytes, from the top
static uint8_t *page_column(uint8_t x) {
  return ((x & 1) ? fb_lo : fb_hi) + (uint16_t)(x >> 1) * COLBYTES;
}

// a sign of the lettering, by its place in it
static uint8_t hud_sign(uint8_t x, uint8_t i) {
  const uint8_t *g = &FONT[(uint16_t)i * 3];
  for (uint8_t k = 0; k < 3; k++, x++) {
    if (x > 127) continue;
    uint8_t v = pgm_read_byte(g + k);
    if (text_band == 7) hud[x] = v;
    else page_column(x)[text_band] = v;
  }
  return x + 1;
}

static uint8_t hud_char(uint8_t x, char ch) {
  const char *set = PSTR(FONT_CHARS);
  uint8_t i = 0;
  for (;;) {
    char c = (char)pgm_read_byte(set + i);
    if (c == 0) { i = 0; break; }
    if (c == ch) break;
    i++;
  }
  return hud_sign(x, i);
}

// something of a mission, from the flash chip: so many bytes from there
static NOINLINE void job_read(uint8_t which, uint16_t at, uint8_t *to, uint8_t n) {
  fx_read(FX_JOBS + (uint16_t)(((uint16_t)(which * 2) << 8) + at), to, n);
}

// lettering of a mission, which is kept as places in the lettering
static void hud_run(uint8_t x, uint8_t which, uint16_t at, uint8_t signs) {
  uint8_t text[JOB_LINE];
  job_read(which, at, text, signs);
  for (uint8_t i = 0; i < signs; i++) x = hud_sign(x, text[i]);
}

// What a telephone has to offer: of the missions that are its own, the
// first one not done yet; NONE: they are all done
static NOINLINE uint8_t job_of(uint8_t k) {
  uint8_t j = pgm_read_byte(&JOB_FIRST[k]) + kept.done[k];
  return j < pgm_read_byte(&JOB_FIRST[k + 1]) ? j : NONE;
}

// A telephone that rings (one that has something to offer, with no mission
// on): where it stands
static uint16_t spot_x, spot_y;

static NOINLINE bool phone_rings(uint8_t k) {
  spot_x = pgm_read_word(&PHONES[2 * k]);
  spot_y = pgm_read_word(&PHONES[2 * k + 1]);
  return job == NONE && job_of(k) != NONE;
}

static NOINLINE void cash_add(uint16_t gain) {
  cash += gain;
  if (cash < gain) cash = 65535;
}

// the last digit of a number, which loses it
static uint8_t digit_off(uint16_t &v) {
  uint8_t d = v % 10;
  v /= 10;
  return d;
}

static uint8_t hud_num(uint8_t x, uint16_t v, uint8_t digits) {
  char buf[5];
  for (uint8_t i = 0; i < digits; i++) buf[i] = '0' + digit_off(v);
  while (digits--) x = hud_char(x, buf[digits]);
  return x;
}

static uint8_t hud_text(uint8_t x, const char *text) {
  for (;;) {
    char c = (char)pgm_read_byte(text++);
    if (!c) return x;
    x = hud_char(x, c);
  }
}

static uint8_t hud_icon(uint8_t x, const uint8_t *icon, uint8_t w) {
  // (nothing is ever put where it would not fit)
  while (w--) hud[x++] = pgm_read_byte(icon++);
  return x + 1;
}

// an amount of money that ends at x; returns where the sign before it would go
static uint8_t hud_dollars(uint8_t x, uint16_t v) {
  do {
    hud_char(x, '0' + digit_off(v));
    x -= 4;
  } while (v);
  hud_char(x, '$');
  return x - 4;
}

// the money, against the right edge; with a mission on, the time that is left
static void hud_money() {
  if (job == NONE) {
    hud_dollars(125, cash);
    return;
  }
  uint16_t v = job_clock / PLANE_HZ;
  hud_num(117, v % 60, 2);
  hud_char(113, ':');
  hud_num(109, v / 60, 1);
}

static void hud_draw() {
  hud_clear();
  uint8_t x = 7;
  // the heart blinks for a moment after a hit
  if (!(hurt & 2)) hud_icon(1, ICON_HEART, 5);
  if (hurt) hurt--;
  for (uint8_t i = 0; i < HEALTH; i++) hud[x + i] = i < health ? 0x1C : 0x08;
  // the stars blink once the police has lost the player
  x = 25;
  if (calm < CALM_LOST || (frames_total & 4))
    for (uint8_t i = 0; i < wanted; i++) x = hud_icon(x, ICON_STAR, 5);
#if defined(SELFTEST) && !defined(HOST)
  {
    // columns drawn / columns where assembly and reference disagree
    hud_clear();
    hud_num(0, st_cols, 5);
    hud_num(28, st_bad, 5);
    hud_num(112, fps_value, 3);
    return;
  }
#endif
#if defined(PROFILE) && !defined(HOST)
  {
    // per-frame time of each part of the renderer, in units of 0.1 ms
    // (display refresh interrupts landing inside a part are counted with it)
    hud_clear();
    static uint8_t nfr;
    static uint16_t shown[6];
    if (++nfr >= 8) {
      for (uint8_t i = 0; i < 6; i++) { shown[i] = (uint16_t)(prof[i] / (8u * 1600u)); prof[i] = 0; }
      nfr = 0;
    }
    uint8_t x = 0;
    for (uint8_t i = 0; i < 6; i++) x = hud_num(x, shown[i], 3) + 3;
    hud_num(112, fps_value, 3);
    return;
  }
#endif
  if (grip) {
    // an officer has got hold of the player
    if (frames_total & 4) hud_text(51, PSTR("GET AWAY!"));
  } else if (phone != NONE) {
    hud_text(51, PSTR("DOWN:ANSWER"));
  } else if (on_foot && reach != NONE) {
    hud_text(51, PSTR("DOWN:GET IN"));
  } else if (note && note_set == SPR_PASSED) {
    // what it paid
    hud_char(hud_dollars(83, job_paid), '+');
  } else if (job != NONE) {
    // what the mission asks for: the hint of the step, the second one if
    // the car it takes is missing; and how many people are still to go
    hud_run(51, job, JOB_STEPS + 8 + (job_fit ? 0 : JOB_HINT) + ((uint16_t)job_at << 5), JOB_HINT);
    if (step.op & STEP_COUNT) hud_num(91, job_left, 2);
  } else if (on_foot) {
  } else if (hero.speed == 0) {
    hud_text(51, PSTR("DOWN:GET OUT"));
  } else {
    // speed in km/h: speed is cells per 256 ticks; 1 cell = 4 m, 156 ticks = 1 s
    uint16_t kmh = (uint16_t)(((uint32_t)iabs(hero.speed) * 2246) >> 16);   // * 4 * 156 / 256 / 256 * 3.6
    x = hud_num(51, kmh, 3);
    hud_text(x, PSTR("KMH"));
  }
  hud_money();
}

// ------------------------------------------------------------------ the car pool
// a free slot; failing that, the slot of the car that matters least
static uint8_t car_slot() {
  uint8_t best = 0;
  int16_t worth = 32767;
  for (uint8_t i = 0; i < N_CARS; i++) {
    const Car &c = cars[i];
    uint8_t s = car_state(c);
    if (s == CAR_FREE) return i;
    // far away matters less; what the player left behind matters most
    int16_t w = -(apart(c.x, c.y) >> 2);
    if (s == CAR_LEFT) w += 8000;
    if (w < worth) { worth = w; best = i; }
  }
  return best;
}

// Parking spots are not stored anywhere: whether a cell holds a parked car, and
// which, follows from its position. That way the same cars stand in the same
// places every time the player comes by.
static uint8_t spot_hash(uint8_t cx, uint8_t cy) {
  uint16_t h = (uint16_t)cx * 0x9E37u + (uint16_t)cy * 0x79B9u;
  h ^= h >> 7;
  h *= 0x2545u;
  h ^= h >> 9;
  return (uint8_t)h;
}

static bool spot_used(uint8_t cx, uint8_t cy) {
  for (uint8_t i = 0; i < N_TAKEN; i++)
    if (taken[i][0] == cx && taken[i][1] == cy) return true;
  for (uint8_t i = 0; i < N_CARS; i++) {
    const Car &c = cars[i];
    if (car_state(c) != CAR_FREE && (uint8_t)(c.x >> 8) == cx && (uint8_t)(c.y >> 8) == cy) return true;
  }
  return false;
}

// put the car the city parked in this cell into the slot, if there is one
static bool parked_here(Car &c, uint8_t cx, uint8_t cy) {
  uint8_t b = cell_at(cx, cy);
  uint8_t h = spot_hash(cx, cy);
  uint16_t x = ((uint16_t)cx << 8) | 0x80, y = ((uint16_t)cy << 8) | 0x80;
  uint8_t dir;
  if (is_lot(b)) {
    // a parking lot: one bay per cell, a quarter of them taken
    if (h & 3) return false;
    dir = (h & 4) ? 0 : 2;
  } else if (is_pavement(b)) {
    // at the curb, where a lane runs along exactly one side of the pavement;
    // never in two cells next to each other, the cars would touch
    if ((h & 3) || ((cx ^ cy) & 1)) return false;
    uint8_t side = b & 15;
    if (side == 1) dir = 0;
    else if (side == 2) dir = 1;
    else if (side == 4) dir = 2;
    else if (side == 8) dir = 3;
    else return false;
    int8_t sx = dir_x(dir), sy = dir_y(dir);
    uint8_t r = cell_at(cx + sx, cy + sy);
    if (!is_road(r) || (r & 3) == 0 || (r & 3) == 3) return false;   // a junction or a crossing
    // two wheels on the pavement, so the lane stays free
    if (sx) x = sx > 0 ? (((uint16_t)cx + 1) << 8) - 8 : ((uint16_t)cx << 8) + 8;
    else y = sy > 0 ? (((uint16_t)cy + 1) << 8) - 8 : ((uint16_t)cy << 8) + 8;
    dir = (r >> 2) & 3;                       // facing the way the lane goes
  } else return false;
  if (spot_used(cx, cy)) return false;
  c.x = x;
  c.y = y;
  c.hd = dir << 6;
  c.what = CAR_PARKED | (((h >> 4) % 6) << 2);
  return true;
}

static void parked_spawn(Car &c, bool close) {
  // a spot some way ahead; never so close that the car would pop up in view
  uint16_t ax = hero.x, ay = hero.y;
  if (!close) advance(ax, ay, cam_yaw, 1280);
  for (uint8_t tries = 0; tries < 4; tries++) {
    int8_t dx = (int8_t)(rnd8() % 25) - 12;
    int8_t dy = (int8_t)(rnd8() % 25) - 12;
    int16_t cx = (int16_t)(ax >> 8) + dx;
    int16_t cy = (int16_t)(ay >> 8) + dy;
    if (cx < 2 || cx > 253 || cy < 2 || cy > 253) continue;
    int16_t hx = iabs(cx - (int16_t)(hero.x >> 8)), hy = iabs(cy - (int16_t)(hero.y >> 8));
    if (hx + hy > 16) continue;                       // it would be out of range at once
    if (!close && hx < 6 && hy < 6) continue;
    if (parked_here(c, (uint8_t)cx, (uint8_t)cy)) return;
  }
}

static bool traffic_spawn(Car &c, bool police) {
  // pick a road cell a fair distance from the player; every other time one on
  // the player's own street, so that there is always something coming by.
  // Four tries, for the police as well: there is not always one near enough
  // to come, and then nobody comes.
  for (uint8_t tries = 0; tries < 4; tries++) {
    int8_t dx = (int8_t)(rnd8() % 41) - 20;
    int8_t dy = (int8_t)(rnd8() % 41) - 20;
    if (tries & 1) {
      if (dx & 1) dx = (int8_t)(dx % 3);
      else dy = (int8_t)(dy % 3);
    }
    if (dx > -9 && dx < 9 && dy > -9 && dy < 9) continue;
    if (iabs(dx) + iabs(dy) > 28) continue;               // it would be out of range at once
    int16_t cx = (int16_t)(hero.x >> 8) + dx;
    int16_t cy = (int16_t)(hero.y >> 8) + dy;
    if (cx < 1 || cx > 254 || cy < 1 || cy > 254) continue;
    uint8_t b = cell_at((uint8_t)cx, (uint8_t)cy);
    if (!is_road(b) || (b & 3) == 0) continue;          // lanes only, not junctions
    uint8_t dir = (b >> 2) & 3;
    uint8_t kind = rnd8() % 6;
    if (police) {
      // in a lane that leads towards the player, not away
      if ((int8_t)(dir_x(dir) * dx + dir_y(dir) * dy) >= 0) continue;
      kind = CAR_POLICE;
    }
    c.x = ((uint16_t)cx << 8) | 0x80;
    c.y = ((uint16_t)cy << 8) | 0x80;
    c.hd = dir << 6;
    c.speed = 56 + (rnd8() >> 3);
    c.wait = 0;
    c.what = CAR_TRAFFIC | (kind << 2) | (dir << 5);
    return true;
  }
  return false;
}

// is (ox, oy) on the stretch of road this car is about to drive over?
static bool in_the_way(const Car &c, uint16_t ox, uint16_t oy) {
  int16_t dx = (int16_t)(ox - c.x), dy = (int16_t)(oy - c.y);
  int16_t ahead, aside;
  switch (car_dir(c)) {
    case 0: ahead = -dy; aside = dx; break;
    case 1: ahead = dx; aside = dy; break;
    case 2: ahead = dy; aside = dx; break;
    default: ahead = -dx; aside = dy; break;
  }
  return ahead > 40 && ahead < 440 && aside > -120 && aside < 120;
}

static void ped_thrown_out(uint16_t x, uint16_t y, uint8_t away, uint8_t kind);

// A police car that is after the player. True if it goes on driving.
static bool police_step(Car &c, int16_t far) {
  if (c.wait) { c.wait--; return false; }
  if (far < 12 * 256 && (uint8_t)(frames_total & 31) == 0 && !sound_busy()) sound_play(SOUND_SIREN);
  if (calm != CALM_SEEN) return true;          // nobody sees the player just now
  if (hero_slow()) {
    if (far >= (on_foot ? 5 * 256 : 700)) return true;
    // near enough: the car stops where it is and the officer gets out, on the left
    uint8_t away = (car_dir(c) + 3) & 3;
    ped_thrown_out(c.x + dir_x(away) * 120, c.y + dir_y(away) * 120, away, PED_COP);
    c.what = (c.what & 0xFC) | CAR_PARKED;
    return false;
  }
  if (far >= 330) return true;
  // into the player's car; it takes a moment to get going again
  hurt_by(1);
  hero.speed -= hero.speed >> 2;
  c.wait = 40;
  return false;
}

static void traffic_step(Car &c, uint8_t dt) {
  int16_t far = apart(c.x, c.y);
  if (far > 30 * 256) { c.what = CAR_FREE; return; }

  uint8_t speed = c.speed;
  bool chasing = false;
  if (wanted && car_kind(c) == CAR_POLICE) {
    // on the lookout wherever it drives; after the player while it knows where to
    police_at(c.x, c.y, far);
    chasing = calm < CALM_LOST;
  }
  if (chasing) {
    if (!police_step(c, far)) return;
    speed = CHASE_SPEED;
  } else {
    // wait for whatever is in the way: the player always, other cars for a while
    // (two cars waiting for each other would wait for ever)
    bool stop = in_the_way(c, hero.x, hero.y);
    if (!stop && c.wait < 30) {
      for (uint8_t i = 0; i < N_CARS; i++) {
        const Car &o = cars[i];
        if (&o != &c && car_state(o) != CAR_FREE && in_the_way(c, o.x, o.y)) { stop = true; break; }
      }
    }
    if (stop) {
      if (c.wait < 255 && (uint8_t)(frames_total & 3) == 0) c.wait++;
      if (c.wait == 0) c.wait = 1;
      // a jam out of sight clears itself
      if (c.wait > 60 && far > 8 * 256) c.what = CAR_FREE;
      return;
    }
    // after a long wait the car pushes on regardless for a moment, then is patient again
    if (c.wait >= 30 && c.wait < 40) c.wait++;
    else c.wait = 0;
  }

  uint8_t dir = car_dir(c);
  uint8_t cx = (uint8_t)(c.x >> 8), cy = (uint8_t)(c.y >> 8);
  int16_t dist = (int16_t)(((uint16_t)speed * dt) >> 4);
  int8_t sx = dir_x(dir), sy = dir_y(dir);
  c.x += sx * dist;
  c.y += sy * dist;
  // keep centred in the lane
  if (sx == 0) c.x = (c.x & 0xFF00) | 0x80;
  else c.y = (c.y & 0xFF00) | 0x80;
  uint8_t nx = (uint8_t)(c.x >> 8), ny = (uint8_t)(c.y >> 8);
  if (nx == cx && ny == cy) return;
  // entered a new cell: follow the lane, turn where the road ends
  uint8_t b = cell_at(nx, ny);
  if (!is_road(b)) { c.what = CAR_FREE; return; }        // drove off the map somehow: recycle
  if (chasing) {
    // Whichever way brings it nearer to where the player was seen last,
    // lanes or no lanes: straight on, right or left. Back only out of a
    // dead end.
    int16_t best = 32767;
    uint8_t ahead = dir;
    dir ^= 2;
    for (uint8_t k = 0; k < 4; k++) {
      if (k == 2) continue;
      uint8_t d = (ahead + k) & 3;
      uint8_t tx = nx + dir_x(d), ty = ny + dir_y(d);
      if (!is_road(cell_at(tx, ty))) continue;
      // the long way first: a turn that is missed means once round the block
      int16_t ax = iabs((int16_t)((((uint16_t)tx << 8) | 0x80) - seen_x));
      int16_t ay = iabs((int16_t)((((uint16_t)ty << 8) | 0x80) - seen_y));
      int16_t a = ax + ay + (ax > ay ? ax : ay);
      if (a < best) { best = a; dir = d; }
    }
  } else {
    if (b & 3) dir = (b >> 2) & 3;                        // a lane: obey its direction
    // junction: keep going, unless the way ahead is closed
    if (!is_road(cell_at(nx + dir_x(dir), ny + dir_y(dir)))) {
      uint8_t r = (dir + 1) & 3;
      dir = is_road(cell_at(nx + dir_x(r), ny + dir_y(r))) ? r : ((dir + 3) & 3);
    }
  }
  c.what = (c.what & 0x9F) | (dir << 5);
  c.hd = dir << 6;
}

static void cars_step(uint8_t dt) {
  // the police that is out: officers on foot (counted since the last frame), and cars
  uint8_t traffic = 0, standing = 0, empty = NONE, police = cops;
  cops = 0;
  for (uint8_t i = 0; i < N_CARS; i++) {
    Car &c = cars[i];
    switch (car_state(c)) {
      case CAR_FREE:
        empty = i;
        break;
      case CAR_TRAFFIC:
        traffic++;
        if (car_kind(c) == CAR_POLICE) police++;
        traffic_step(c, dt);
        break;
      case CAR_PARKED:
        standing++;
        if (apart(c.x, c.y) > 20 * 256) c.what = CAR_FREE;
        break;
      default:
        standing++;
        if (apart(c.x, c.y) > 60 * 256) c.what = CAR_FREE;
        break;
    }
  }
  // One police car or officer for every star, as long as they know where
  // the player is; if need be, in the place of the car that matters least.
  // With one star they take their time: they look for a car to send every
  // three seconds, and about every other time there is none to be found
  // before the matter is forgotten.
  if (police < wanted && calm < CALM_LOST && (uint8_t)(frames_total & (wanted > 1 ? 15 : 63)) == 0) {
    traffic_spawn(cars[car_slot()], true);
    return;
  }
  if (empty == NONE) return;
  // one new car per frame at most, taking turns between the two sorts
  if (traffic < MAX_TRAFFIC && ((frames_total & 1) || standing >= N_CARS - MAX_TRAFFIC))
    traffic_spawn(cars[empty], false);
  else if (standing < N_CARS - MAX_TRAFFIC)
    parked_spawn(cars[empty], false);
}

// ------------------------------------------------------------------ people
static int16_t off_line(uint16_t x, uint16_t y, int16_t &ahead);

// outside what the camera shows: behind the player, or off to the side
static bool ped_aside(uint16_t x, uint16_t y, int16_t &ahead) {
  return off_line(x, y, ahead) > ahead;
}

static void ped_spawn(Ped &p) {
  // where the player is going to be soon: around a point some way ahead
  uint16_t ax = hero.x, ay = hero.y;
  advance(ax, ay, cam_yaw, 1536);
  int16_t cx = (int16_t)(ax >> 8) + (int8_t)(rnd8() % 17) - 8;
  int16_t cy = (int16_t)(ay >> 8) + (int8_t)(rnd8() % 17) - 8;
  if (cx < 2 || cx > 253 || cy < 2 || cy > 253) return;
  if (!is_pavement(cell_at((uint8_t)cx, (uint8_t)cy))) return;
  uint16_t x = ((uint16_t)cx << 8) | 0x80, y = ((uint16_t)cy << 8) | 0x80;
  // never right next to the player, and never out of nothing in front of the
  // camera: in view only a good way off, where people are a few dots high
  int16_t ahead;
  if (apart(x, y) < 3 * 256 || (!ped_aside(x, y, ahead) && ahead < 7 * 256)) return;
  uint8_t r = rnd8();
  // a step short of the middle of the cell, so that the first thing they do
  // is look where they can go
  p.x = x - dir_x(r & 3);
  p.y = y - dir_y(r & 3);
  p.what = (r & 3) | (((r >> 2) % PED_COP) << 2) | (PED_WALK << 4);
}

// may someone standing on ground `here` step on to ground `there`?
static bool ped_may(uint8_t here, uint8_t there, bool running) {
  if (is_wall(there)) return false;
  // whoever is on the pavement stays on it, unless they are running for their
  // life; whoever is not on it walks until they are
  return running || !is_walk(here) || is_walk(there);
}

// would going this way bring them closer to the player?
static bool ped_nearer(const Ped &p, uint8_t dir) {
  int8_t sx = dir_x(dir);
  int16_t d = sx ? (int16_t)(p.x - hero.x) : (int16_t)(p.y - hero.y);
  return (sx + dir_y(dir) > 0) ? d < 0 : d > 0;
}

static void ped_frighten(Ped &p) {
  p.what = (p.what & (0x0F | PED_MARK)) | (PED_RUN << 4);
  p.timer = 200;
  // turning round on the spot is always possible: it is the way they came
  if (ped_nearer(p, p.what & 3)) p.what ^= 2;
}

static void ped_drop(Ped &p) {
  // what they carried lies next to them, for whoever comes to pick it up
  p.what = (p.what & 0x0F) | (PED_DOWN << 4) | PED_CASH;
  p.timer = 150;
}

// by the player's doing
static void ped_kill(Ped &p) {
  bool cop = ((p.what >> 2) & 3) == PED_COP;
  // what a mission counts: the one it is about, officers, or anybody
  if (job_left && ((step.op & STEP_MARK) ? (p.what & PED_MARK) != 0 : (step.op & STEP_COPS) ? cop : true)) job_left--;
  crime_add(cop ? 16 : 4);
  ped_drop(p);
}

// An officer who is after the player: straight towards them, along the street
// or across it, whichever is the longer way. With one star, whoever they get
// hold of for long enough is under arrest; from two stars on they shoot.
static void cop_step(Ped &p, uint8_t dt, int16_t far) {
  cops++;
  police_at(p.x, p.y, far);
  // to where the player was seen last
  int16_t dx = (int16_t)(seen_x - p.x), dy = (int16_t)(seen_y - p.y);
  bool across = p.what & 1;                        // facing east or west
  if (across ? iabs(dy) > iabs(dx) + 64 : iabs(dx) > iabs(dy) + 64) across = !across;
  uint8_t dir = across ? (dx > 0 ? 1 : 3) : (dy > 0 ? 2 : 0);
  p.what = (p.what & 0xFC) | dir;
  // With one star they are out to arrest the player; with more they have
  // given that up. (Two, to make up for the one that every frame takes off.)
  if (wanted < 2 && far < 150 && hero_slow()) grip += 2;
  if (p.timer) p.timer--;
  else if (wanted > 1 && !over && far < 6 * 256 && !hidden(p.x, p.y)) {
    p.timer = 40;
    // the more stars, the more it hurts
    if (rnd8() & 1) hurt_by(wanted - 1);
    else sound_play(SOUND_SHOT);
  }
  if (p.timer > 30) return;                        // standing, pistol up
  // once there, or when the trail is cold, they stand and look
  if (calm >= CALM_LOST || iabs(dx) + iabs(dy) < 100) return;
  int8_t dist = (int8_t)(((uint16_t)COP_SPEED * dt) >> 8);
  for (uint8_t k = 0; k < 2; k++) {
    uint16_t nx = p.x + dir_x(dir) * dist, ny = p.y + dir_y(dir) * dist;
    if (!is_wall(cell_at((uint8_t)(nx >> 8), (uint8_t)(ny >> 8)))) {
      p.x = nx;
      p.y = ny;
      return;
    }
    // something in the way: along it
    across = !across;
    dir = across ? (dx > 0 ? 1 : 3) : (dy > 0 ? 2 : 0);
  }
}

static void ped_step(Ped &p, uint8_t dt) {
  uint8_t state = ped_state(p);
  if (state == PED_FREE) { ped_spawn(p); return; }
  // Too far away to matter, or left behind: the place is free for somebody
  // where the player is going. What lies on the ground stays for a while.
  // An officer who is after the player stays in the game for longer, up to
  // two stars: whoever outruns them has got away from them. From three stars
  // on the next one is on their way as soon as one is left behind.
  int16_t far = apart(p.x, p.y), ahead;
  bool cop = state == PED_RUN && ((p.what >> 2) & 3) == PED_COP;
  bool marked = p.what & PED_MARK;
  if (far > 18 * 256 ||
      (far > 8 * 256 && state != PED_DOWN && !marked && !(cop && wanted < 3) && ped_aside(p.x, p.y, ahead))) {
    p.what = 0;
    return;
  }
  if (marked) {
    // the one a mission is about: the arrow leads to wherever they are
    job_seen = true;
    nav_x = (uint8_t)(p.x >> 8);
    nav_y = (uint8_t)(p.y >> 8);
  }
  // an officer runs as long as there is somebody to go after
  if (cop) {
    if (!wanted) p.timer = 0;
  } else if (p.timer) {
    // running and lying down both end after a while
    if (state != PED_DOWN || (frames_total & 3) == 0) p.timer--;
  }
  if (state != PED_WALK && !p.timer && !(cop && wanted)) {
    if (state == PED_DOWN) { p.what = 0; return; }
    p.what = (p.what & (0x0F | PED_MARK)) | (PED_WALK << 4);
    state = PED_WALK;
    cop = false;
  }
  if (state == PED_DOWN) {
    if ((p.what & PED_CASH) && far < 160) {
      p.what &= ~PED_CASH;
      if (p.timer > 25) p.timer = 25;             // nothing left to come back for
      cash_add(10 + (rnd8() & 63));
      sound_play(SOUND_CASH);
    }
    return;
  }

  // run over by the player's car?
  if (!on_foot && (hero.speed > 500 || hero.speed < -500)) {
    uint16_t fx = hero.x, fy = hero.y;
    advance(fx, fy, hero.hd, hero.speed > 0 ? 100 : -100);
    if (iabs((int16_t)(p.x - fx)) < 90 && iabs((int16_t)(p.y - fy)) < 90) {
      ped_kill(p);
      return;
    }
  }
  if (cop) { cop_step(p, dt, far); return; }

  uint8_t dir = p.what & 3;
  int8_t sx = dir_x(dir), sy = dir_y(dir);
  int8_t dist = (int8_t)(((state == PED_RUN ? 600u : 150u) * dt) >> 8);
  uint8_t before = (uint8_t)(sx ? p.x : p.y);
  p.x += sx * dist;
  p.y += sy * dist;
  uint8_t after = (uint8_t)(sx ? p.x : p.y);
  // passing the middle of a cell: decide where to go from here
  bool middle = (sx + sy > 0) ? (before < 0x80 && after >= 0x80) : (before >= 0x80 && after < 0x80);
  if (!middle) return;
  uint8_t cx = (uint8_t)(p.x >> 8), cy = (uint8_t)(p.y >> 8);
  uint8_t here = cell_at(cx, cy);
  uint8_t turn = (rnd8() & 1) ? 1 : 3;                 // right or left first, by chance
  uint8_t pick = dir;
  if ((rnd8() & 15) == 0) pick = (dir + turn) & 3;     // now and then, turn off for no reason
  for (uint8_t k = 0; k < 8; k++) {
    // Whoever is running takes no way that leads towards the player, unless
    // there is no other: the second time round any way that is one will do.
    // (Without that, somebody with their back to the wall ran through it.)
    if (ped_may(here, cell_at(cx + dir_x(pick), cy + dir_y(pick)), state == PED_RUN) &&
        !(k < 4 && state == PED_RUN && ped_nearer(p, pick))) break;
    uint8_t j = k & 3;
    pick = j == 0 ? dir : j == 1 ? ((dir + turn) & 3) : j == 2 ? ((dir - turn) & 3) : ((dir + 2) & 3);
  }
  if (pick != dir) {
    p.what = (p.what & 0xFC) | pick;
    // turn on the spot, in the middle of the cell
    if (sx) p.x = (p.x & 0xFF00) | 0x80;
    else p.y = (p.y & 0xFF00) | 0x80;
  }
}

// Somebody gets out of a car and runs: the driver of a car the player takes,
// or an officer. Nobody the player would miss makes room if there is none.
static Ped *ped_put(uint16_t x, uint16_t y, uint8_t what) {
  Ped *p = &peds[0];
  for (uint8_t i = 0; i < N_PEDS; i++) {
    if (ped_state(peds[i]) == PED_FREE) { p = &peds[i]; break; }
    if (ped_state(peds[i]) == PED_WALK) p = &peds[i];
  }
  p->x = x;
  p->y = y;
  p->what = what;
  return p;
}

static void ped_thrown_out(uint16_t x, uint16_t y, uint8_t away, uint8_t kind) {
  Ped *p = ped_put(x, y, away | (kind << 2));
  ped_frighten(*p);
  if (kind == PED_COP) p->timer = 25;
}

// the driver of a car leaves it: by the door on the left, and away
static void driver_out(const Car &c) {
  uint8_t away = (car_dir(c) + 3) & 3;
  uint8_t kind = car_kind(c) == CAR_POLICE ? PED_COP : rnd8() % PED_COP;
  ped_thrown_out(c.x + dir_x(away) * 120, c.y + dir_y(away) * 120, away, kind);
  crime_add(2);
}

// ------------------------------------------------------------------ player, driving
static void drive_step(uint8_t dt, uint8_t btn) {
  // throttle / brake, speeds in 8.8 cells per 256 ticks
  const int16_t VMAX = 3000;       // ~ 105 km/h
  const int16_t VREV = -800;
  if (btn & BTN_B) {
    hero.speed += 7 * dt;
  } else if (btn & BTN_A) {
    hero.speed -= (hero.speed > 0 ? 16 : 6) * dt;
  } else {
    // rolling resistance
    int16_t drag = 2 * dt;
    if (hero.speed > drag) hero.speed -= drag;
    else if (hero.speed < -drag) hero.speed += drag;
    else hero.speed = 0;
  }
  if (hero.speed > VMAX) hero.speed = VMAX;
  if (hero.speed < VREV) hero.speed = VREV;

  // steering: turn rate grows with speed up to a limit
  int16_t sp = iabs(hero.speed);
  int16_t rate = sp >> 3;
  if (rate > 150) rate = 150;
  if (hero.speed < 0) rate = -rate;
  if (btn & BTN_LEFT) hero.hd -= rate * dt;
  if (btn & BTN_RIGHT) hero.hd += rate * dt;

  int16_t dist = (int16_t)(((int32_t)hero.speed * dt) >> 8);
  uint16_t nx = hero.x, ny = hero.y;
  advance(nx, ny, hero.hd, dist);
  // probe a little ahead of the car centre in the direction of travel
  uint16_t px = nx, py = ny;
  advance(px, py, hero.hd, hero.speed >= 0 ? 150 : -150);
  if (solid(px, py)) {
    // try sliding along each axis before giving up
    if (!solid(px, hero.y)) { hero.x = nx; hero.speed -= hero.speed >> 2; }
    else if (!solid(hero.x, py)) { hero.y = ny; hero.speed -= hero.speed >> 2; }
    else hero.speed = -(hero.speed >> 2);
  } else {
    hero.x = nx;
    hero.y = ny;
  }
}

static void get_out() {
  // the driver's door is on the left; if there is no room, use the other one
  uint16_t px, py;
  uint8_t side = 0;
  for (;;) {
    px = hero.x;
    py = hero.y;
    advance(px, py, hero.hd + (side ? 16384u : 49152u), 135);
    if (!solid(px, py)) break;
    if (++side == 2) return;                       // boxed in: stay in the car
  }
  Car &c = cars[car_slot()];
  c.x = hero.x;
  c.y = hero.y;
  c.hd = (uint8_t)((hero.hd + 128) >> 8);
  c.what = CAR_LEFT | (hero_kind << 2);
  hero.x = px;
  hero.y = py;
  hero.speed = 0;
  on_foot = true;
  held = BTN_UP | BTN_DOWN | BTN_A | BTN_B;
}

// ------------------------------------------------------------------ player, on foot
static void get_in(uint8_t i) {
  Car &c = cars[i];
  uint8_t state = car_state(c);
  if (state == CAR_PARKED) {
    taken[taken_next][0] = (uint8_t)(c.x >> 8);
    taken[taken_next][1] = (uint8_t)(c.y >> 8);
    taken_next = (taken_next + 1) & (N_TAKEN - 1);
  }
  if (state == CAR_TRAFFIC) driver_out(c);
  hero.x = c.x;
  hero.y = c.y;
  hero.hd = (uint16_t)c.hd << 8;
  hero.speed = 0;
  hero_kind = car_kind(c);
  c.what = CAR_FREE;
  on_foot = false;
  reach = NONE;
  held = BTN_UP | BTN_DOWN | BTN_A | BTN_B;
}

static void walk_step(uint8_t dt, uint8_t btn) {
  if (btn & BTN_LEFT) hero.hd -= 200 * dt;         // a full turn takes two seconds
  if (btn & BTN_RIGHT) hero.hd += 200 * dt;
  int16_t v = 0;
  if (btn & BTN_UP) v = (btn & BTN_A) ? 840 : 525;  // 5 m/s; with A held, 8 m/s
  else if (btn & BTN_DOWN) v = -260;
  hero.speed = v;
  if (v) {
    int16_t dist = (int16_t)(((int32_t)v * dt) >> 8);
    int16_t feel = v > 0 ? 45 : -45;               // keep this far from walls and cars
    uint16_t nx = hero.x, ny = hero.y, px, py;
    advance(nx, ny, hero.hd, dist);
    px = nx;
    py = ny;
    advance(px, py, hero.hd, feel);
    if (!solid(px, py)) { hero.x = nx; hero.y = ny; }
    else if (!solid(px, hero.y)) hero.x = nx;      // slide along whatever it is
    else if (!solid(hero.x, py)) hero.y = ny;
    walked += (uint8_t)iabs(dist);
  } else walked = 0;

  // which car is within reach? One that is driving past counts too: its
  // driver stops for whoever pulls the door open
  reach = NONE;
  int16_t nearest = 300;
  for (uint8_t i = 0; i < N_CARS; i++) {
    const Car &c = cars[i];
    if (car_state(c) == CAR_FREE) continue;
    int16_t d = apart(c.x, c.y);
    if (d < nearest) { nearest = d; reach = i; }
  }
}

// ------------------------------------------------------------------ the pistol
// Where is (x, y) from the muzzle's point of view: how far ahead (negative:
// behind), and (the value returned) how far off the line of fire. Good for
// anything near enough to be in the game at all.
#define GUN_RANGE (12 * 256)

static int16_t off_line(uint16_t x, uint16_t y, int16_t &ahead) {
  int16_t dx = (int16_t)(x - hero.x), dy = (int16_t)(y - hero.y);
  int16_t s = isin(hero.hd), c = icos(hero.hd);
  ahead = mul_q14(dx, s) - mul_q14(dy, c);
  return iabs(mul_q14(dx, c) + mul_q14(dy, s));
}

static void fire() {
  // the bullet stops at the first thing on its line: a person, a car, a wall
  int16_t range = GUN_RANGE, ahead;
  uint8_t who = NONE, car = NONE;
  for (uint8_t i = 0; i < N_PEDS; i++) {
    uint8_t state = ped_state(peds[i]);
    if (state != PED_WALK && state != PED_RUN) continue;
    // nobody aims to the degree with a cross of buttons: a near miss is a hit
    int16_t off = off_line(peds[i].x, peds[i].y, ahead);
    if (ahead < 40 || ahead >= range || off > 40 + (ahead >> 3)) continue;
    range = ahead;
    who = i;
  }
  for (uint8_t i = 0; i < N_CARS; i++) {
    if (car_state(cars[i]) == CAR_FREE) continue;
    int16_t off = off_line(cars[i].x, cars[i].y, ahead);
    if (ahead < 40 || ahead >= range || off > 110) continue;
    range = ahead - 120;                         // the side of the car that faces us
    who = NONE;
    car = i;
  }
  uint16_t x = hero.x, y = hero.y;
  for (int16_t d = 96; d < range; d += 96) {
    advance(x, y, hero.hd, 96);
    if (!is_building(cell_at((uint8_t)(x >> 8), (uint8_t)(y >> 8)))) continue;
    range = d - 192;                             // a little before the wall, so it shows
    who = car = NONE;
    break;
  }
  if (range < 0) range = 0;
  shot_x = hero.x;
  shot_y = hero.y;
  advance(shot_x, shot_y, hero.hd, range);

  crime_add(1);
  if (who != NONE) {
    ped_kill(peds[who]);
    shot_x = peds[who].x;
    shot_y = peds[who].y;
  }
  if (car != NONE && car_state(cars[car]) == CAR_TRAFFIC) {
    // the driver has had enough
    Car &c = cars[car];
    driver_out(c);
    c.what = (c.what & 0xFC) | CAR_LEFT;
  }
  // everybody who hears it runs (an officer: towards the player)
  for (uint8_t i = 0; i < N_PEDS; i++) {
    uint8_t state = ped_state(peds[i]);
    if (state == PED_WALK && apart(peds[i].x, peds[i].y) < 16 * 256) ped_frighten(peds[i]);
  }
  sound_play(SOUND_SHOT);
  shot_show = 5;
  gun_wait = 60;
}

// On foot the camera looks over the player's shoulder: somebody who stands
// right in front of the camera hides exactly what they are aiming at. Which
// shoulder depends on where there is room; next to a wall, the other one.
#define CAM_SIDE 44

static bool camera_room(int8_t side) {
  uint16_t x = hero.x, y = hero.y;
  advance(x, y, cam_yaw, -CAM_BACK);
  advance(x, y, cam_yaw + 16384, side * 3);        // the camera's place and as much again twice
  return !is_building(cell_at((uint8_t)(x >> 8), (uint8_t)(y >> 8)));
}

static void camera_step(uint8_t dt) {
  // the camera swings behind the player with a little lag
  int16_t d = (int16_t)(hero.hd - cam_yaw);
  int16_t stepv = (int16_t)(((int32_t)d * dt) >> 5);
  if (stepv == 0 && d != 0) stepv = d > 0 ? 1 : -1;
  if ((d > 0 && stepv > d) || (d < 0 && stepv < d)) stepv = d;
  cam_yaw += stepv;
  cam.yaw = cam_yaw;
  // from one place to the other it moves over in a few frames
  int8_t want = 0;
  if (on_foot) {
    if (!camera_room(cam_shoulder) && camera_room(-cam_shoulder)) cam_shoulder = -cam_shoulder;
    want = cam_shoulder;
  }
  if (cam_side < want) cam_side += 4;
  if (cam_side > want) cam_side -= 4;
  // back off from the player, but never into a building
  int16_t back = CAM_BACK;
  int8_t side = cam_side;
  for (;;) {
    uint16_t x = hero.x, y = hero.y;
    advance(x, y, cam_yaw, -back);
    advance(x, y, cam_yaw + 16384, side);
    if (!is_building(cell_at((uint8_t)(x >> 8), (uint8_t)(y >> 8))) || back <= 96) {
      cam.x = x;
      cam.y = y;
      break;
    }
    if (side) side = 0;
    else back -= 64;
  }
}

// ------------------------------------------------------------------ the way to go
static void nav_step() {
  nav_near = false;
  if (nav_x) {
    // how far east and south of the player, in sixteenths of a metre (a cell
    // is 4 m): fine enough to tell the directions apart from close by
    int16_t dx = (int16_t)(((uint16_t)nav_x << 6) | 32) - (int16_t)(hero.x >> 2);
    int16_t dy = (int16_t)(((uint16_t)nav_y << 6) | 32) - (int16_t)(hero.y >> 2);
    // Of 32 directions, counted from where the camera looks: in which one is
    // the place furthest ahead? That is the way, and that far it is.
    int16_t far = 0;
    uint8_t way = 0;
    uint16_t a = cam_yaw;
    for (uint8_t k = 0; k < 32; k++) {
      int16_t d = mul_q14(dx, isin(a)) - mul_q14(dy, icos(a));
      if (d > far) { far = d; way = k; }
      a += 2048;
    }
    nav_near = far < NAV_THERE * 16;
    if (nav_near && job == NONE) {
      nav_x = 0;
      sound_play(SOUND_THERE);
    } else {
      if (way != nav_way) {
        // the arrow, for the display routine: in two halves, so that it never
        // has to wait long for the flash chip to be let go
        nav_way = way;
        uint24_t at = FX_ARROWS + (uint16_t)way * NAV_ARROW_BYTES;
        fx_read(at, nav_over, NAV_ARROW_BYTES / 2);
        fx_read(at + NAV_ARROW_BYTES / 2, nav_over + NAV_ARROW_BYTES / 2, NAV_ARROW_BYTES / 2);
      }
      // 374M; from a kilometre on, 1.2K
      uint16_t v = (uint16_t)far >> 4;
      uint8_t unit = FONT_M;
      if (v > 999) {
        v = (v + 50) / 100;
        unit = FONT_K;
      }
      label_text[3] = unit;
      for (uint8_t i = 3; i--;) label_text[i] = FONT_0 + digit_off(v);
      if (unit == FONT_K) {
        label_text[0] = label_text[1];
        label_text[1] = FONT_DOT;
      }
    }
  }
  // The label comes and goes by way of one picture in which its place is
  // black: black is black, whichever way the display routine takes it.
  if (nav_x) {
    if (label_show < 2) label_show++;
  } else if (label_show) label_show--;
}

// ------------------------------------------------------------------ missions
void save_store();

static inline uint16_t cell_middle(uint8_t c) { return ((uint16_t)c << 8) | 0x80; }

// the step that is due begins
static void job_step() {
  job_read(job, JOB_STEPS + ((uint16_t)job_at << 5), (uint8_t *)&step, sizeof(step));
  if (step.time) job_clock = (uint16_t)step.time << 8;
  if (step.record) {
    if (crime < step.record) crime = step.record;
    crime_add(0);
  }
  job_left = step.n;
  nav_x = step.x;
  nav_y = step.y;
  nav_way = NONE;
}

// over: passed (SPR_PASSED) or failed (SPR_FAILED)
static void job_end(uint8_t set) {
  note = NOTE_FRAMES;
  note_set = set;
  if (set == SPR_PASSED) {
    uint8_t pay;
    job_read(job, 1, &pay, 1);           // (after the telephone it belongs to)
    job_paid = pay * JOB_PAY_UNIT;
    cash_add(job_paid);
    kept.done[job_from]++;
    save_store();
    sound_play(SOUND_PASSED);
  } else if (over) {
    // WASTED or BUSTED says it first
    note += over;
  } else sound_play(SOUND_FAILED);
  job = NONE;
  job_left = 0;
  job_clock = 0;
  nav_x = 0;
  for (uint8_t i = 0; i < N_PEDS; i++) peds[i].what &= ~PED_MARK;
}

static void job_frame(uint8_t dt) {
  if (note) note--;
  phone = NONE;
  if (job == NONE) {
    // the telephones that ring: heard from a way off, answered from close by
    for (uint8_t k = 0; k < N_PHONES; k++) {
      if (!phone_rings(k)) continue;
      int16_t far = apart(spot_x, spot_y);
      if (far < PHONE_HEARD && (uint8_t)(frames_total & 63) == 0 && !sound_busy()) sound_play(SOUND_RING);
      if (far < PHONE_REACH && on_foot) phone = k;
    }
    return;
  }
  if (over || job_clock <= dt) {
    job_end(SPR_FAILED);
    return;
  }
  job_clock -= dt;
  uint8_t op = step.op;
  job_fit = !(op & STEP_CAR) || (!on_foot && (step.n == STEP_ANY_CAR || step.n == hero_kind));
  if ((op & STEP_MARK) && !job_seen) {
    // whoever it is about is there when the player gets near: on their
    // rounds, and with a sign over them
    uint16_t x = cell_middle(step.x), y = cell_middle(step.y);
    nav_x = step.x;
    nav_y = step.y;
    if (apart(x, y) < MARK_NEAR) ped_put(x, y, (step.who << 2) | (PED_WALK << 4) | PED_MARK);
  }
  bool done;
  switch (op & 3) {
    case STEP_GO:
      // (to stop is to come down to walking pace: nobody should have to
      // fiddle with brake and accelerator until the car stands to the dot)
      done = nav_near && job_fit && (!(op & STEP_STOP) || hero_slow());
      break;
    case STEP_KILL:
      done = !job_left;
      break;
    case STEP_LOSE:
      done = !wanted;
      break;
    default:
      job_end(SPR_PASSED);
      return;
  }
  if (done) {
    job_at++;
    job_step();
    if (step.op != STEP_END) sound_play(SOUND_THERE);
  }
}

// a telephone has been answered and the mission taken
static void job_take() {
  job_from = phone;
  job = job_of(phone);
  job_at = 0;
  job_step();
}

// ------------------------------------------------------------------ frame
// the lettering of WASTED and BUSTED, across the middle of the picture
static void banner(uint8_t set) {
  draw_put(pgm_read_word(&SPRITE_SETS[(uint16_t)set * 4 + 2]), COLS / 2, ROWS / 2, 0);
}

// From the start: at the beginning, and after WASTED or BUSTED. The money stays.
static void game_init() {
  for (uint8_t i = 0; i < N_CARS; i++) cars[i].what = CAR_FREE;
  for (uint8_t i = 0; i < N_PEDS; i++) peds[i].what = 0;
  health = HEALTH;
  crime = 0;
  wanted = 0;
  grip = 0;
  // whatever button is down at this moment has to be let go first: nobody
  // wants to come back from the police station firing
  held = BTN_UP | BTN_DOWN | BTN_A | BTN_B;
  // the player starts on the pavement of a wide street, a few steps from a
  // car of their own at the curb
  hero.x = (85u << 8) | 0xA0;
  hero.y = (154u << 8) | 0x90;
  hero.hd = 16384;
  hero.speed = 0;
  on_foot = true;
  reach = NONE;
  cam_yaw = hero.hd;
  cam_shoulder = camera_room(CAM_SIDE) ? CAM_SIDE : -CAM_SIDE;
  cam_side = cam_shoulder;
  cars[0].x = (86u << 8) | 0xD0;
  cars[0].y = (154u << 8) + 8;
  cars[0].hd = 64;
  cars[0].what = CAR_LEFT | (CAR_SPORTS << 2);
  last_tick = ticks();
  fps_mark = last_tick;
  cam.x = hero.x;
  cam.y = hero.y;
  cam.yaw = cam_yaw;
  view_begin(cam);
  camera_step(1);
  // the cars parked round about are there from the start
  for (uint8_t i = 1; i < N_CARS - MAX_TRAFFIC; i++)
    for (uint8_t k = 0; k < 60 && car_state(cars[i]) == CAR_FREE; k++) parked_spawn(cars[i], true);
}

static void game_frame(uint8_t btn, uint8_t fresh, uint8_t dt) {
  if (dt > 24) dt = 24;
  if (shot_show) shot_show--;
  if (over) {
    // the world goes on for a moment, without the player
    btn = fresh = 0;
    if (--over == 0) {
      cash -= cash >> 1;            // what the hospital charges, or what the police keep
      game_init();
      return;
    }
  }
  if (grip) {
    if (--grip >= GRIP_BUSTED) game_over(SPR_BUSTED);
  }
  if ((uint8_t)(frames_total & 15) == 0) {
    if (!wanted) {
      // what does not kill heals, as long as nobody is after the player
      if (health < HEALTH && (uint8_t)(frames_total & 63) == 0) health++;
    } else if (++calm >= CALM_STAR) {
      // out of sight for a good while: one star less, and the next one
      // sooner, as long as nobody sees the player
      crime = (uint8_t)(((1 << (wanted - 1)) - 1) << 3);
      calm = CALM_LOST;
      stars_update();
    }
  }
  // the light next to the screen, for whoever wants it: red, blue, red, blue
  // while the police is after the player
  light(!(settings & SET_LED) || !wanted ? LIGHT_OFF : (frames_total & 8) ? LIGHT_RED : LIGHT_BLUE);
  if (on_foot) {
    gun_wait = gun_wait > dt ? gun_wait - dt : 0;
    if ((fresh & BTN_DOWN) && phone != NONE) {
      page_open(PAGE_JOB);
      return;
    }
    if ((fresh & BTN_DOWN) && reach != NONE) get_in(reach);
    else {
      walk_step(dt, btn);
      if ((btn & BTN_B) && !gun_wait) fire();
    }
  } else {
    drive_step(dt, btn);
    // getting out works at walking pace and below: the car stops where it is
    if ((fresh & BTN_DOWN) && hero.speed > -500 && hero.speed < 500) get_out();
  }
  cars_step(dt);
  job_seen = false;
  for (uint8_t i = 0; i < N_PEDS; i++) ped_step(peds[i], dt);
  camera_step(dt);
  nav_step();
  job_frame(dt);

#if defined(PROFILE) && !defined(HOST)
  TCCR1A = 0;
  TCCR1B = 1;
  uint16_t prof_s0 = TCNT1;
#endif
  view_begin(cam);
  Entity e;
  e.flags = 0;
  e.x = hero.x;
  e.y = hero.y;
  e.hd = hero.hd;
  // the pistol is in the hand on the camera's side, so that nothing hides the shot
  int8_t hand = cam_side < 0 ? -27 : 27;
  if (!on_foot) e.set = SPR_HERO_CAR + hero_kind;
  else if (over && !health) e.set = SPR_PED_DOWN;
  else if (shot_show) e.set = SPR_HERO_AIM + (shot_show > 3 ? 1 : 0) + (hand < 0 ? 2 : 0);
  else e.set = SPR_HERO_STAND + (hero.speed ? 1 + (walked >> 6) : 0);
  draw_add(e);
  for (uint8_t i = 0; i < N_PEDS; i++) {
    const Ped &p = peds[i];
    uint8_t state = ped_state(p);
    if (state == PED_FREE) continue;
    uint8_t kind = (p.what >> 2) & 3;
    e.x = p.x;
    e.y = p.y;
    e.hd = (uint16_t)(p.what & 3) << 14;
    if (state == PED_DOWN) e.set = SPR_PED_DOWN + kind;
    else if (kind == PED_COP && p.timer > 30) e.set = SPR_COP_AIM + (p.timer > 37 ? 1 : 0);
    else {
      // the step of the walk comes from where they are; going north or west
      // that counts down, and nobody walks backwards
      uint8_t step = (uint8_t)p.x + (uint8_t)p.y;
      if (!((p.what + 1) & 2)) step = ~step;
      e.set = SPR_PED + kind * 4 + ((step >> (state == PED_RUN ? 6 : 5)) & 3);
    }
    draw_add(e);
    if (p.what & (PED_CASH | PED_MARK)) {
      // it goes up and down a little, to catch the eye
      e.set = ((p.what & PED_MARK) ? SPR_MARK : SPR_CASH) + ((uint8_t)frames_total >> 3 & 1);
      draw_add(e);
    }
  }
  // What a mission is about has a sign hanging over it: where to go to, or,
  // with no mission on, the telephones that ring
  e.set = SPR_MARK + ((uint8_t)frames_total >> 3 & 1);
  for (uint8_t k = 0; k <= N_PHONES; k++) {
    if (k == N_PHONES) {
      if (job == NONE || !nav_x || job_seen) break;
      spot_x = cell_middle(nav_x);
      spot_y = cell_middle(nav_y);
    } else if (!phone_rings(k)) continue;
    e.x = spot_x;
    e.y = spot_y;
    draw_add(e);
  }
  for (uint8_t i = 0; i < N_CARS; i++) {
    const Car &c = cars[i];
    if (car_state(c) == CAR_FREE) continue;
    e.x = c.x;
    e.y = c.y;
    e.hd = (uint16_t)c.hd << 8;
    e.set = SPR_CAR + car_kind(c);
    // the lights on the roof of a police car, left and right in turn
    if (e.set == SPR_POLICE && (frames_total & 4)) e.set = SPR_POLICE_B;
    draw_add(e);
  }
  if (shot_show > 3) {
    // the bullet's trail from the pistol, and a flash where it struck
    uint16_t gx = hero.x, gy = hero.y;
    advance(gx, gy, hero.hd + 16384, hand);
    int16_t dx = (int16_t)(shot_x - gx), dy = (int16_t)(shot_y - gy);
    e.set = SPR_TRACER;
    for (uint8_t k = 1; k < 4; k++) {
      e.x = gx + ((dx * k) >> 2);
      e.y = gy + ((dy * k) >> 2);
      draw_add(e);
    }
    e.x = shot_x;
    e.y = shot_y;
    e.set = SPR_SPARK;
    draw_add(e);
  }
  view_props();
  if (over) banner(over_set);
  else if (note) banner(note_set);
#if defined(PROFILE) && !defined(HOST)
  prof[5] += (uint16_t)(TCNT1 - prof_s0);
#endif
  view_render();
  disp_nav = nav_x && label_show ? DISP_NAV : 0;
  hud_draw();
}

static void game_loop() {
  uint16_t now = ticks();
  uint16_t dt = now - last_tick;
  if (dt == 0) dt = 1;
  last_tick = now;
  // UP and DOWN held for two seconds: back to the console's game menu, the
  // same way out the other games on the Arduboy FX offer
  static uint16_t both_since;
  static uint8_t before;
  uint8_t pressed = buttons();
#ifdef DIAG
  pressed |= diag_buttons;
#endif
#ifdef PROBE
  // (Up and Down still get out of it by hand)
  pressed = probe_buttons(now) | (pressed & (BTN_UP | BTN_DOWN));
#endif
  if ((pressed & (BTN_UP | BTN_DOWN)) != (BTN_UP | BTN_DOWN)) both_since = now;
  else if ((uint16_t)(now - both_since) >= 2 * PLANE_HZ) {
    // (what the player has is kept)
    save_store();
    exit_to_menu();
  }
  uint8_t fresh = pressed & ~before;
  before = pressed;
  // a button that was down while getting in or out counts again once let go
  held &= pressed;
  pressed &= ~held;
  frame_ticks = dt;
  frames_total++;
  fps_frames++;
  if ((uint16_t)(now - fps_mark) >= PLANE_HZ) {
    fps_mark = now;
    fps_value = fps_frames;
    fps_frames = 0;
  }
  if (page) {
    page_frame(pressed, fresh);
    return;
  }
  // LEFT and RIGHT together: the map
  if ((pressed & (BTN_LEFT | BTN_RIGHT)) == (BTN_LEFT | BTN_RIGHT) && !over) {
    page_open(PAGE_MAP);
    return;
  }
  game_frame(pressed, fresh, dt > 255 ? 255 : (uint8_t)dt);
}

// Small Theft Auto - desktop test build.
//
// Runs the real engine and game code on the computer with a fake flash chip,
// then writes every frame to disk so tools/frames_to_gif.py can turn the run
// into pictures. A small autopilot presses the buttons: it walks to the car,
// gets in, drives a route, stops, gets out, walks on and fires the pistol.
//
//   ./host_sim <fxdata.bin> <frames.raw> [frames] [ticks per frame: 7, or 6.5 for 24 pictures a second]
//
// With STILL set in the environment nothing is pressed at all. SCENE picks
// another test: "jack" stands in a lane until a car stops and takes it,
// "people" drives along a pavement into whoever walks there, "shoot" walks
// the pavements with the pistol, "car" fires at the traffic, "range" fires
// one shot and fetches the money. With the police: "busted" shoots somebody
// and waits for what comes, "wasted" walks off with two stars and little
// health left, "chase" drives the route with three stars, "calm" shoots
// somebody and runs until the stars are gone. "walk" walks, runs, stops and
// turns, and says which step of the walk is shown. "flee" starts with STARS
// stars (1 if not set) in a car, on foot with FOOT set, and gets away from
// the police like somebody who knows how: round the corners, away from them.
// "nav" brings up the map, puts the cross where the drive of the tour ends,
// and goes on the tour: it says what the arrow shows on the way, and what it
// should show. SEED: other dice.
//
// PLAY plays by a list of orders, one after the other, with ; between them:
//   walk:x,y   on foot to that place (cells)     drive:x,y  the same in a car
//   run:x,y    the same, running                 car        into the nearest car
//   stop       brake until the car stands        out        stop, and out of the car
//   down, a, b, map   the button, once (map: LEFT and RIGHT)
//   wait:n     so many frames with nothing pressed
//   hold:80,40 buttons (hex: 04 B, 08 A, 10 down, 20 left, 40 right, 80 up) held for so many frames
//   hunt       go after whoever a mission is about (or the nearest person),
//              and shoot, until the mission's step is done (hunt:3: from no
//              further away than 3 cells)
//   spree      the same with whoever comes along
//   flee       away from the police until the stars are gone
//   at:x,y     put the player there (to set a scene up)
//   stars:n    put so many stars on the record
//   kind:n     the car the player sits in is of this kind
//   health:n   so much health is left
// DONE=210: how many of its missions every telephone has seen done (the
// first one two, the second one one, the third none); CASH=100: money to
// begin with.
// What a mission does is printed as it happens.
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <vector>
#include <string>
#include <algorithm>
#include <utility>

#include "../SmallTheftAuto/platform.h"

uint8_t fb_hi[FB_BYTES];
uint8_t fb_lo[FB_BYTES];
uint8_t hud[128];
const uint8_t *host_flash;
uint32_t host_flash_pos;
uint32_t host_flash_reads, host_flash_seeks;
uint16_t host_ticks;
uint8_t host_buttons;
uint16_t host_sounds;
uint8_t host_sound;
uint8_t disp_wide, disp_nav;
uint8_t nav_over[NAV_ARROW_BYTES];
uint8_t host_saved = SET_SOUND, host_light;
uint16_t host_cash;
uint8_t host_jobs[8];
int host_stores;

#define PSTR(s) (s)
#include "../SmallTheftAuto/engine.h"

uint8_t colbuf[16];
uint16_t view_x, view_y;
uint8_t win[512];
uint8_t win_x0[2], win_y0[2];
WallJob wall_job;
Dda dda;

#include "../SmallTheftAuto/game.h"
#include "../SmallTheftAuto/pages.h"

// what is kept, on the desktop: in three variables
void save_load() {
  settings = host_saved;
  cash = host_cash;
  for (int k = 0; k < N_PHONES; k++) kept.done[k] = host_jobs[k];
}

void save_store() {
  host_saved = settings;
  host_cash = cash;
  for (int k = 0; k < N_PHONES; k++) host_jobs[k] = kept.done[k];
  host_stores++;
}

// what every telephone has seen done, as one number: 210 is two, one, none
static int done_says() {
  int v = 0;
  for (int k = 0; k < N_PHONES; k++) v = v * 10 + kept.done[k];
  return v;
}

static void write_frame(FILE *f) {
  static uint8_t img[64][128];
  for (int c = 0; c < COLS; c++) {
    for (int r = 0; r < ROWS; r++) {
      int hi = (fb_hi[c * COLBYTES + (r >> 3)] >> (r & 7)) & 1;
      int lo = (fb_lo[c * COLBYTES + (r >> 3)] >> (r & 7)) & 1;
      if (disp_wide) {
        // a page: black and white, the two planes side by side
        img[r][2 * c] = (uint8_t)(hi * 3);
        img[r][2 * c + 1] = (uint8_t)(lo * 3);
      } else img[r][2 * c] = img[r][2 * c + 1] = (uint8_t)(hi * 2 + lo);
    }
  }
  if (disp_nav && !disp_wide) {
    // the way to go, as the display routine shows it: the arrow laid over
    // the view, the distance taken from the picture the way a page is
    for (int half = 0; half < 2; half++)
      for (int c = 0; c < NAV_ARROW_COLS; c++)
        for (int side = 0; side < 2; side++) {
          const uint8_t *o = nav_over + half * (NAV_ARROW_BYTES / 2) + c * 4 + side * 2;
          for (int b = 0; b < 8; b++) {
            uint8_t &dot = img[half * 8 + b][(NAV_C0 + c) * 2 + side];
            if (!((o[0] >> b) & 1)) dot = 0;
            if ((o[1] >> b) & 1) dot = 3;
          }
        }
    for (int c = NAV_BOX_C0; c < NAV_BOX_C0 + NAV_BOX_COLS; c++)
      for (int b = 0; b < 8; b++) {
        img[b][2 * c] = (uint8_t)(((fb_hi[c * COLBYTES] >> b) & 1) * 3);
        img[b][2 * c + 1] = (uint8_t)(((fb_lo[c * COLBYTES] >> b) & 1) * 3);
      }
  }
  for (int x = 0; x < 128; x++)
    for (int b = 0; b < 8; b++)
      img[ROWS + b][x] = ((hud[x] >> b) & 1) ? 3 : 0;
  fwrite(img, 1, sizeof(img), f);
}

// what the label at the top of the picture says
static const char *label_says() {
  static char text[8];
  for (int i = 0; i < 4; i++) text[i] = FONT_CHARS[label_text[i]];
  text[4] = 0;
  return text;
}

// turn towards a point; returns the buttons to press and how far off the heading is
static uint8_t steer(float tx, float ty, float *off, float *dist) {
  float hx = hero.x / 256.0f, hy = hero.y / 256.0f;
  float want = atan2f(tx - hx, -(ty - hy));
  float have = hero.hd / 65536.0f * 6.2831853f;
  float d = want - have;
  while (d > 3.14159f) d -= 6.2831853f;
  while (d < -3.14159f) d += 6.2831853f;
  *off = d;
  *dist = hypotf(tx - hx, ty - hy);
  if (d > 0.03f) return BTN_RIGHT;
  if (d < -0.03f) return BTN_LEFT;
  return 0;
}

// the nearest person still on their feet (or, with cash set, the nearest
// one down who has not been robbed yet), or -1
static int nearest_person(float *dist, bool cash_only = false) {
  int best = -1;
  float bd = 1e9f;
  for (int i = 0; i < N_PEDS; i++) {
    uint8_t st = ped_state(peds[i]);
    if (cash_only) {
      if (st != PED_DOWN || !(peds[i].what & PED_CASH)) continue;
    } else if (st != PED_WALK && st != PED_RUN) continue;
    float d = hypotf((peds[i].x - hero.x) / 256.0f, (peds[i].y - hero.y) / 256.0f);
    if (d < bd) { bd = d; best = i; }
  }
  *dist = bd;
  return best;
}

// Somebody who wants to get away, in a car or on foot: along the lanes like
// the traffic, and at every junction the way that leads away from the
// police. The way ahead is laid out cell by cell; the buttons steer towards
// a cell a little way along it.
static std::vector<std::pair<int, int>> flee_way;
static int flee_dir = -1;

static int police_near(int cx, int cy) {
  // streets added up, to the nearest police car or officer that is out
  int best = 9999;
  for (int i = 0; i < N_CARS; i++)
    if (car_state(cars[i]) == CAR_TRAFFIC && car_kind(cars[i]) == CAR_POLICE)
      best = std::min(best, abs((cars[i].x >> 8) - cx) + abs((cars[i].y >> 8) - cy));
  for (int i = 0; i < N_PEDS; i++)
    if (ped_state(peds[i]) == PED_RUN && ((peds[i].what >> 2) & 3) == PED_COP)
      best = std::min(best, abs((peds[i].x >> 8) - cx) + abs((peds[i].y >> 8) - cy));
  return best;
}

static uint8_t flee() {
  int cx = hero.x >> 8, cy = hero.y >> 8;
  if (flee_dir < 0) {
    uint8_t b = cell_at((uint8_t)cx, (uint8_t)cy);
    flee_dir = (is_road(b) && (b & 3)) ? ((b >> 2) & 3) : (((hero.hd + 8192) >> 14) & 3);
    flee_way.clear();
  }
  // what has been reached is done with
  while (!flee_way.empty() && abs(flee_way[0].first - cx) + abs(flee_way[0].second - cy) <= 1)
    flee_way.erase(flee_way.begin());
  if (flee_way.size() > 1 && abs(flee_way[1].first - cx) + abs(flee_way[1].second - cy) <= 1)
    flee_way.erase(flee_way.begin());
  if (flee_way.empty()) flee_way.push_back({cx + dir_x(flee_dir), cy + dir_y(flee_dir)});
  while (flee_way.size() < 8) {
    int x = flee_way.back().first, y = flee_way.back().second;
    uint8_t b = cell_at((uint8_t)x, (uint8_t)y);
    int d = flee_dir;
    if (is_road(b) && (b & 3)) d = (b >> 2) & 3;          // a lane: the way it goes
    else {
      // a junction: straight on, or into a lane that leaves to the right or
      // to the left, whichever ends up furthest from the police
      int best = -1;
      for (int k : {0, 1, 3}) {
        int t = (flee_dir + k) & 3;
        int nx = x + dir_x(t), ny = y + dir_y(t);
        uint8_t nb = cell_at((uint8_t)nx, (uint8_t)ny);
        if (!is_road(nb)) continue;
        if (k && !((nb & 3) && ((nb >> 2) & 3) == t)) continue;
        int far = police_near(x + 8 * dir_x(t), y + 8 * dir_y(t));
        if (k == 0) far += 2;                             // when in doubt, straight on
        if (far > best) { best = far; d = t; }
      }
      if (best < 0) {
        // the road ends here: right, left or back, like the traffic
        for (int k : {1, 3, 2}) {
          int t = (flee_dir + k) & 3;
          if (is_road(cell_at((uint8_t)(x + dir_x(t)), (uint8_t)(y + dir_y(t))))) { d = t; break; }
        }
      }
    }
    if (!is_road(cell_at((uint8_t)(x + dir_x(d)), (uint8_t)(y + dir_y(d))))) {
      for (int k : {1, 3, 2}) {
        int t = (d + k) & 3;
        if (is_road(cell_at((uint8_t)(x + dir_x(t)), (uint8_t)(y + dir_y(t))))) { d = t; break; }
      }
    }
    flee_dir = d;
    flee_way.push_back({x + dir_x(d), y + dir_y(d)});
  }
  float off, dist;
  // the faster, the further ahead the eyes
  size_t aim = on_foot ? 1 : 2 + (size_t)(hero.speed > 0 ? hero.speed / 900 : 0);
  // something in the way (the car does not get on): past it on the left, or
  // on the right if there is no road on the left
  static int dodge = 0, side = 0, held_up = 0;
  static uint16_t was_x, was_y;
  if (!on_foot) {
    held_up = (was_x == hero.x && was_y == hero.y) ? held_up + 1 : 0;
    was_x = hero.x;
    was_y = hero.y;
    if (held_up >= 2 && !dodge) {
      int d = flee_dir, x = flee_way[1].first, y = flee_way[1].second;
      side = is_road(cell_at((uint8_t)(x + dir_x((d + 3) & 3)), (uint8_t)(y + dir_y((d + 3) & 3)))) ? 3 : 1;
      dodge = 45;
    }
  }
  float ax = flee_way[aim].first + 0.5f, ay = flee_way[aim].second + 0.5f;
  if (dodge) {
    dodge--;
    ax += dir_x((flee_dir + side) & 3);
    ay += dir_y((flee_dir + side) & 3);
  }
  uint8_t b = steer(ax, ay, &off, &dist);
  if (getenv("TRACE") && !on_foot)
    printf("  flee: at %.2f,%.2f aim %d,%d off %.2f speed %d\n", hero.x / 256.0, hero.y / 256.0, flee_way[aim].first,
           flee_way[aim].second, off, hero.speed);
  if (on_foot) return b | BTN_UP | BTN_A;
  // up against something: back a little, the wheel the other way
  static int stuck = 0, backing = 0;
  if (backing) {
    backing--;
    return (uint8_t)(BTN_A | ((b & BTN_LEFT) ? BTN_RIGHT : (b & BTN_RIGHT) ? BTN_LEFT : 0));
  }
  stuck = (hero.speed < 250 && hero.speed > -250) ? stuck + 1 : 0;
  if (stuck > 25) { stuck = 0; backing = 22; }
  // round a corner at no more than a trot, and no faster than the way is clear
  bool corner = flee_way[6].first != flee_way[1].first && flee_way[6].second != flee_way[1].second;
  int limit = fabsf(off) > 0.5f ? 700 : (fabsf(off) > 0.25f || corner) ? 1300 : 2900;
  if (hero.speed < limit) b |= BTN_B;
  else if (hero.speed > limit + 300) b |= BTN_A;
  return b;
}

// Other dice for every SEED: a place in their sequence that is far from the
// others (a few throws further on would be nearly the same game again).
static void host_dice(int seed) {
  uint32_t h = (uint32_t)seed * 2654435761u + 12345u;
  h ^= h >> 15;
  rng_state = (uint16_t)(h ^ (h >> 16));
  if (!rng_state) rng_state = 0xACE1;
  for (int k = 0; k < 16; k++) rnd8();
}

static void report(int frame) {
  printf("frame %d: %s at %.2f, %.2f heading %.0f speed %d sounds %u cash $%u health %d stars %d (record %d, calm %d)",
         frame, on_foot ? "on foot" : "driving",
         hero.x / 256.0, hero.y / 256.0, hero.hd / 65536.0 * 360.0, hero.speed, host_sounds, cash, health, wanted,
         crime, calm);
  if (!on_foot) printf(" car kind %d", hero_kind);
  if (nav_x) printf(" on the way to %d, %d: arrow %d, %s", nav_x, nav_y, nav_way, label_says());
  printf("\n  cars:");
  for (int i = 0; i < N_CARS; i++) {
    const Car &c = cars[i];
    if (car_state(c) == CAR_FREE) continue;
    printf(" [%c %s%d %.1f,%.1f%s]", "-TPL"[car_state(c)], car_kind(c) == CAR_POLICE ? "POLICE " : "k", car_kind(c),
           c.x / 256.0, c.y / 256.0, car_state(c) == CAR_TRAFFIC && c.wait ? " waiting" : "");
  }
  printf("\n  people:");
  for (int i = 0; i < N_PEDS; i++) {
    const Ped &p = peds[i];
    if (ped_state(p) == PED_FREE) continue;
    printf(" [%s%c%s %.1f,%.1f]", ((p.what >> 2) & 3) == PED_COP ? "COP " : "", "-wrd"[ped_state(p)],
           (p.what & PED_CASH) ? "$" : "", p.x / 256.0, p.y / 256.0);
  }
  printf("\n");
}

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: host_sim fxdata.bin frames.raw [frames] [ticks per frame]\n");
    return 1;
  }
  FILE *f = fopen(argv[1], "rb");
  if (!f) { perror(argv[1]); return 1; }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  std::vector<uint8_t> flash((size_t)n + 65536, 0xFF);
  if (fread(flash.data(), 1, (size_t)n, f) != (size_t)n) { perror("read"); return 1; }
  fclose(f);
  host_flash = flash.data();

  int frames = argc > 3 ? atoi(argv[3]) : 200;
  // (6.5 is allowed: 6 and 7 ticks in turn, 24 pictures a second as on the console)
  double tpf_exact = argc > 4 ? atof(argv[4]) : 7;
  double ticks_owed = 0;
  FILE *out = fopen(argv[2], "wb");
  if (!out) { perror(argv[2]); return 1; }

  if (getenv("SETTINGS")) host_saved = (uint8_t)atoi(getenv("SETTINGS"));   // 1 sound, 2 police light
  if (getenv("DONE")) {
    const char *d = getenv("DONE");
    for (int k = 0; k < N_PHONES && d[k]; k++) host_jobs[k] = (uint8_t)(d[k] - '0');
  }
  if (getenv("CASH")) host_cash = (uint16_t)atoi(getenv("CASH"));
  save_load();
  game_init();
  const char *scene = getenv("SCENE");
  int phase = 0;
  // SEED: other dice (the flee scene takes them once it is set up)
  if (getenv("SEED") && !(scene && !strcmp(scene, "flee"))) host_dice(atoi(getenv("SEED")));
  if (scene && !strcmp(scene, "pages")) {
    // the title, the settings from there, the game, the map, the settings from there
    page_open(PAGE_TITLE);
    phase = 70;
  }
  if (scene && !strcmp(scene, "jack")) {
    // in the outer northbound lane of the avenue, looking at the traffic coming
    hero.x = (uint16_t)(81.5f * 256);
    hero.y = (uint16_t)(136.5f * 256);
    hero.hd = 32768;
    cam_yaw = hero.hd;
    phase = 10;
  } else if (scene && !strcmp(scene, "people")) {
    // in a car on the pavement on the west side of the avenue
    hero.x = (uint16_t)(77.5f * 256);
    hero.y = (uint16_t)(160.5f * 256);
    hero.hd = 0;
    on_foot = false;
    hero_kind = CAR_VAN;
    phase = 20;
  } else if (scene && !strcmp(scene, "flee")) {
    // In a car (on foot with FOOT set), with STARS stars, the police called
    // to where the player is: away, and how long does it take?
    int stars = getenv("STARS") ? atoi(getenv("STARS")) : 1;
    hero.x = (uint16_t)(93.5f * 256);
    hero.y = (uint16_t)(153.5f * 256);
    if (!getenv("FOOT")) {
      on_foot = false;
      hero_kind = CAR_SPORTS;
    }
    uint8_t lane = cell_at((uint8_t)(hero.x >> 8), (uint8_t)(hero.y >> 8));
    hero.hd = (uint16_t)(((lane >> 2) & 3) << 14);
    cam_yaw = hero.hd;
    if (getenv("SEED")) host_dice(atoi(getenv("SEED")));
    crime_add((uint8_t)(((1 << stars) - 1) << 3));
    phase = 90;
  } else if (scene && !strcmp(scene, "walk")) {
    // on foot on the same pavement, looking up the avenue: walk, run, stop,
    // turn around, walk back
    hero.x = (uint16_t)(77.5f * 256);
    hero.y = (uint16_t)(160.5f * 256);
    hero.hd = 0;
    cam_yaw = hero.hd;
    phase = 80;
  } else if (scene && !strcmp(scene, "shoot")) {
    // on foot on the same pavement, looking up the avenue
    hero.x = (uint16_t)(77.5f * 256);
    hero.y = (uint16_t)(160.5f * 256);
    hero.hd = 0;
    cam_yaw = hero.hd;
    phase = 30;
  } else if (scene && !strcmp(scene, "range")) {
    // where the game starts, with somebody standing on the pavement ahead;
    // RANGE is how many cells ahead
    float far = getenv("RANGE") ? (float)atof(getenv("RANGE")) : 5.0f;
    peds[0].x = (uint16_t)(hero.x + (int)(far * 256));
    peds[0].y = hero.y;
    peds[0].what = 1 | (1 << 2) | (PED_WALK << 4);
    phase = 50;
  } else if (scene && !strcmp(scene, "nav")) {
    // HERO_AT: the player somewhere else to begin with, in cells ("20.5,30.5")
    if (getenv("HERO_AT")) {
      float x, y;
      if (sscanf(getenv("HERO_AT"), "%f,%f", &x, &y) == 2) {
        hero.x = (uint16_t)(x * 256);
        hero.y = (uint16_t)(y * 256);
      }
    }
    phase = 100;
  } else if (scene && !strcmp(scene, "busted")) {
    phase = 60;
  } else if (scene && !strcmp(scene, "calm")) {
    phase = 62;
  } else if (scene && !strcmp(scene, "escape")) {
    // shoot somebody, then to the car and away along the route of the tour
    phase = 64;
  } else if (scene && !strcmp(scene, "forget")) {
    // three stars, and the police kept away (below): how long until they are gone?
    crime = 56;
    stars_update();
    phase = 63;
  } else if (scene && !strcmp(scene, "wasted")) {
    health = 3;
    crime = 24;
    stars_update();
    phase = 61;
  } else if (scene && !strcmp(scene, "chase")) {
    crime = 56;
    stars_update();
  } else if (scene && !strcmp(scene, "car")) {
    // on the pavement beside the avenue, looking across the lanes
    hero.x = (uint16_t)(77.5f * 256);
    hero.y = (uint16_t)(140.5f * 256);
    hero.hd = 16384;
    cam_yaw = hero.hd;
    phase = 40;
  }
  // PLAY: orders, one after the other
  std::vector<std::pair<std::string, std::string>> orders;
  size_t order = 0;
  if (getenv("PLAY")) {
    std::string all = getenv("PLAY");
    size_t a = 0;
    while (a <= all.size()) {
      size_t e = all.find(';', a);
      if (e == std::string::npos) e = all.size();
      std::string one = all.substr(a, e - a);
      while (!one.empty() && one[0] == ' ') one.erase(0, 1);
      size_t c = one.find(':');
      if (!one.empty())
        orders.push_back({one.substr(0, c), c == std::string::npos ? std::string() : one.substr(c + 1)});
      a = e + 1;
    }
    phase = 200;
  }
  report(0);

  // the drive: along the street, left up the avenue, right into a street, stop half way along it
  static const float way[][2] = {{93.0f, 153.5f}, {96.5f, 152.6f}, {98.6f, 148.5f}, {98.5f, 143.0f}, {98.5f, 129.5f},
                                 {100.5f, 125.6f}, {107.0f, 125.5f}};
  const int nway = sizeof(way) / sizeof(way[0]);
  // the walk afterwards: to the pavement, then along it
  static const float walk[][2] = {{108.0f, 126.6f}, {118.0f, 126.6f}};
  const int nwalk = sizeof(walk) / sizeof(walk[0]);
  int wp = 0, since = 0, downed = 0, running = 0, left_cars = -1;
  unsigned shots = 0;

  uint32_t seeks = 0, reads = 0, cells = 0, in_sight = 0, none_in_sight = 0;
  int most_sprites = 0;
  bool still = getenv("STILL") != nullptr;
  for (int i = 0; i < frames; i++) {
    // --- autopilot -------------------------------------------------------
    uint8_t b = 0;
    float off, dist;
    since++;
    switch (phase) {
      case 0:                                   // look around for a moment
        if (since > 12) { phase = 1; since = 0; }
        break;
      case 1:                                   // walk to the car waiting at the curb
        b = steer(cars[0].x / 256.0f - 0.3f, cars[0].y / 256.0f + 0.5f, &off, &dist);
        if (fabsf(off) < 0.7f) b |= BTN_UP;
        if (reach != NONE) { b = BTN_DOWN; phase = 2; since = 0; report(i); }
        break;
      case 2:                                   // drive
        if (on_foot || since < 6) break;        // (letting go of the buttons first)
        while (wp < nway - 1 && hypotf(way[wp][0] - hero.x / 256.0f, way[wp][1] - hero.y / 256.0f) < 1.8f) wp++;
        b = steer(way[wp][0], way[wp][1], &off, &dist);
        if (wp == nway - 1 && dist < 2.5f) { phase = 3; since = 0; break; }
        {
          bool corner = wp < nway - 1 && dist < 9.0f && fabsf(off) < 0.3f;
          int limit = (fabsf(off) > 0.25f || corner) ? 1200 : 2200;
          if (hero.speed < limit) b |= BTN_B;
          else if (hero.speed > limit + 300) b |= BTN_A;
        }
        break;
      case 3:                                   // stop, get out
        if (hero.speed > 0) b = BTN_A;
        else if (since & 1) b = BTN_DOWN;
        if (on_foot) { phase = 4; since = 0; wp = 0; report(i); }
        break;
      case 4:                                   // walk on
        if (since < 8) break;
        while (wp < nwalk - 1 && hypotf(walk[wp][0] - hero.x / 256.0f, walk[wp][1] - hero.y / 256.0f) < 0.6f) wp++;
        b = steer(walk[wp][0], walk[wp][1], &off, &dist);
        if (fabsf(off) < 0.7f && dist > 0.3f) b |= BTN_UP;
        if (wp == nwalk - 1 && dist < 4.0f) { phase = (scene && !strcmp(scene, "escape")) ? 61 : 30; since = 0; }
        break;
      case 10:                                  // wait in the lane for a car to come by
        for (int k = 0; k < N_CARS; k++)
          if (car_state(cars[k]) == CAR_TRAFFIC && cars[k].wait && apart(cars[k].x, cars[k].y) < 3 * 256 && since > 0) {
            printf("frame %d: car %d stopped for the player\n", i, k);
            since = -100000;
            report(i);
          }
        if (reach != NONE && car_state(cars[reach]) == CAR_TRAFFIC) {
          printf("frame %d: taking car %d\n", i, reach);
          report(i);
          b = BTN_DOWN;
          phase = 11;
          since = 0;
        }
        break;
      case 11:                                  // drive off in it
        if (on_foot) { printf("frame %d: still on foot?\n", i); break; }
        if (since == 1) report(i);
        if (since > 6) b = BTN_B;
        break;
      case 20:                                  // along the pavement, foot down
        b = steer(77.5f, 120.0f, &off, &dist) | BTN_B;
        break;
      case 30: {                                // turn to whoever is nearest, walk up, fire
        // money on the ground comes first
        int k = nearest_person(&dist, true);
        if (k >= 0) {
          b = steer(peds[k].x / 256.0f, peds[k].y / 256.0f, &off, &dist);
          if (fabsf(off) < 0.5f) b |= BTN_UP;
          break;
        }
        k = nearest_person(&dist);
        if (k < 0) break;
        float far = dist;
        b = steer(peds[k].x / 256.0f, peds[k].y / 256.0f, &off, &dist);
        if (far > 9.0f && fabsf(off) < 0.5f) b |= BTN_UP | BTN_A;
        else if (fabsf(off) < 0.05f && since > 20) { b |= BTN_B; since = 0; }
        break;
      }
      case 50:                                  // one shot, then go and see what they carried
        if (since == 8) b = BTN_B;
        if (since > 16) {
          int k = nearest_person(&dist, true);
          if (k < 0) break;
          b = steer(peds[k].x / 256.0f, peds[k].y / 256.0f, &off, &dist);
          if (fabsf(off) < 0.5f) b |= BTN_UP;
        }
        break;
      case 60:                                  // shoot somebody, then stand and wait for the police
      case 62:                                  // ... or run for it
      case 64: {                                // ... or take the car
        if (wanted) {
          if (phase == 62) b = BTN_UP | BTN_A | ((i / 40) % 6 == 5 ? BTN_RIGHT : 0);
          if (phase == 64) { phase = 1; since = 0; }
          break;
        }
        int k = nearest_person(&dist);
        if (k < 0) break;
        b = steer(peds[k].x / 256.0f, peds[k].y / 256.0f, &off, &dist);
        if (fabsf(off) < 0.05f && since > 20) { b |= BTN_B; since = 0; }
        break;
      }
      case 61:                                  // walk on, whatever happens
        b = BTN_UP;
        break;
      case 63:                                  // stand there; no police comes
        for (int k = 0; k < N_CARS; k++)
          if (car_kind(cars[k]) == CAR_POLICE) cars[k].what = CAR_FREE;
        break;
      case 90: {                                // away from the police
        // not before they are there and have seen the player: getting away
        // from nobody is no test
        static int from = -1, done = 0;
        if (from < 0) {
          if (calm != CALM_SEEN && since < 400) break;
          from = i;
          printf("frame %d: the police is there (%d stars, %d out); off\n", i, wanted, police_near(0, 0) < 9999);
          report(i);
        }
        b = flee();
        if (!wanted && !done) {
          printf("frame %d: got rid of the stars after %d frames (%.0f s), health %d\n", i, i - from,
                 (i - from) * tpf_exact / 156.0, health);
          done = 1;
        }
        if (over && !done) {
          printf("frame %d: caught after %d frames (%.0f s)\n", i, i - from, (i - from) * tpf_exact / 156.0);
          done = 1;
        }
        break;
      }
      case 80:                                  // a walk: on, faster, stop, turn, on
        if (since < 10) break;
        if (since < 90) b = BTN_UP;
        else if (since < 150) b = BTN_UP | BTN_A;
        else if (since < 170) b = 0;
        else if (since < 200) b = BTN_LEFT;
        else if (since < 260) b = BTN_UP | BTN_LEFT;
        else b = BTN_UP;
        {
          static int shown = -1;
          int now = on_foot ? (hero.speed ? 1 + (walked >> 6) : 0) : -1;
          if (now != shown) printf("frame %d: step %d (walked %d, speed %d)\n", i, now, walked, hero.speed);
          shown = now;
        }
        break;
      case 70: {                                // through the pages, a button every now and then
        static const struct { int at; uint8_t b; } keys[] = {
          {30, BTN_A}, {50, BTN_B}, {70, BTN_DOWN}, {90, BTN_B}, {130, BTN_B}, {150, BTN_A},
          {170, BTN_B}, {175, BTN_UP}, {230, BTN_LEFT | BTN_RIGHT}, {260, BTN_DOWN}, {270, BTN_DOWN},
          {290, BTN_UP}, {310, BTN_A}, {330, BTN_B}, {350, BTN_A}, {370, BTN_B}, {375, BTN_UP}};
        for (auto &k : keys)
          if (since >= k.at && since < k.at + (k.b == BTN_UP ? 40 : 3)) b = k.b;
        static int shown = -1, chosen = -1, lit = -1;
        if (page != shown || settings != chosen || host_light != lit) {
          printf("frame %d: %s on the screen; sound %s, police light %s (stored: %d), light now %d\n", i,
                 page == PAGE_GAME ? "the game" : page == PAGE_TITLE ? "the title" : page == PAGE_MAP ? "the map" :
                 "the settings", (settings & SET_SOUND) ? "on" : "off", (settings & SET_LED) ? "on" : "off",
                 host_saved, host_light);
          shown = page;
          chosen = settings;
          lit = host_light;
        }
        break;
      }
      case 100: {                               // the map, the cross to where the drive ends, B
        // NAV_TO: another place, in cells ("200,40")
        static int tx = 107 / 2, ty = 125 / 2, pressed_b = 0;
        if (since == 1 && getenv("NAV_TO")) {
          sscanf(getenv("NAV_TO"), "%d,%d", &tx, &ty);
          tx /= 2;
          ty /= 2;
        }
        if (since < 10) break;
        if (since < 13) { b = BTN_LEFT | BTN_RIGHT; break; }
        if (since < 18) break;
        if (page != PAGE_MAP) {
          if (pressed_b) {
            printf("frame %d: back in the game, on the way to %d, %d\n", i, nav_x, nav_y);
            phase = 0;
            since = 0;
          } else printf("frame %d: the map is not up?\n", i);
          break;
        }
        if (map_x < tx) b |= BTN_RIGHT;
        else if (map_x > tx) b |= BTN_LEFT;
        if (map_y < ty) b |= BTN_DOWN;
        else if (map_y > ty) b |= BTN_UP;
        if (since % 20 == 0) printf("frame %d: the cross is at %d, %d, the map moved down %d steps\n", i, map_x, map_y, page_pick);
        if (!b) {
          printf("frame %d: the cross is at %d, %d: B\n", i, map_x, map_y);
          b = BTN_B;
          pressed_b = 1;
        }
        break;
      }
      case 200: {                               // PLAY: by the list of orders
        if (order >= orders.size()) break;
        const std::string &what = orders[order].first, &how = orders[order].second;
        float px = 0, py = 0;
        int n = 0;
        sscanf(how.c_str(), "%f,%f", &px, &py);
        sscanf(how.c_str(), "%d", &n);
        bool done = false;
        static int stuck = 0, backing = 0;
        if (since == 1) printf("frame %d: order %zu: %s %s\n", i, order, what.c_str(), how.c_str());
        if (what == "walk" || what == "run") {
          b = steer(px, py, &off, &dist);
          if (fabsf(off) < 0.7f) b |= BTN_UP | (what == "run" ? BTN_A : 0);
          done = dist < 0.5f;
        } else if (what == "drive") {
          b = steer(px, py, &off, &dist);
          if (backing) {
            backing--;
            b = (uint8_t)(BTN_A | ((b & BTN_LEFT) ? BTN_RIGHT : (b & BTN_RIGHT) ? BTN_LEFT : 0));
          } else {
            stuck = (since > 20 && hero.speed < 250 && hero.speed > -250) ? stuck + 1 : 0;
            if (stuck > 25) { stuck = 0; backing = 22; }
            // slower the nearer, and round the corners
            int limit = fabsf(off) > 0.5f ? 700 : (fabsf(off) > 0.25f || dist < 6.0f) ? 1300 : 2600;
            if (hero.speed < limit) b |= BTN_B;
            else if (hero.speed > limit + 300) b |= BTN_A;
          }
          done = dist < 1.5f;
        } else if (what == "car") {
          // the nearest car that stands
          int best = -1;
          float bd = 1e9f;
          for (int k = 0; k < N_CARS; k++) {
            if (car_state(cars[k]) != CAR_PARKED && car_state(cars[k]) != CAR_LEFT) continue;
            float d = hypotf((cars[k].x - hero.x) / 256.0f, (cars[k].y - hero.y) / 256.0f);
            if (d < bd) { bd = d; best = k; }
          }
          if (!on_foot) done = since > 6;
          else if (reach != NONE && phone == NONE) b = (since & 1) ? BTN_DOWN : 0;
          else if (best >= 0) {
            b = steer(cars[best].x / 256.0f, cars[best].y / 256.0f, &off, &dist);
            if (fabsf(off) < 0.7f) b |= BTN_UP;
          }
        } else if (what == "stop" || what == "out") {
          if (hero.speed > 200) b = BTN_A;
          else if (hero.speed < -200) b = BTN_B;
          else if (what == "out" && !on_foot) b = (since & 1) ? BTN_DOWN : 0;
          done = what == "out" ? (on_foot && since > 8) : hero.speed == 0;
        } else if (what == "down" || what == "a" || what == "b" || what == "map") {
          if (since >= 4 && since < 7)
            b = what == "down" ? BTN_DOWN : what == "a" ? BTN_A : what == "b" ? BTN_B : (BTN_LEFT | BTN_RIGHT);
          done = since >= 12;
        } else if (what == "wait") {
          done = since >= n;
        } else if (what == "hold") {
          // hold:80,40: the buttons (hex, as the game has them), so many frames
          unsigned held_down = 0;
          int frames_held = 0;
          sscanf(how.c_str(), "%x,%d", &held_down, &frames_held);
          if (since >= 4) b = (uint8_t)held_down;
          done = since >= 4 + frames_held;
        } else if (what == "at") {
          hero.x = (uint16_t)(px * 256);
          hero.y = (uint16_t)(py * 256);
          done = true;
        } else if (what == "kind") {
          hero_kind = (uint8_t)n;
          done = true;
        } else if (what == "health") {
          health = (uint8_t)n;
          done = true;
        } else if (what == "stars") {
          crime = (uint8_t)(((1 << n) - 1) << 3);
          crime_add(0);
          done = true;
        } else if (what == "flee") {
          if (since == 1) flee_dir = -1;
          b = flee();
          done = !wanted;
        } else if (what == "hunt" || what == "spree") {
          static int began_at = -1, began_left = 0, aim_since = 0;
          if (since == 1) { began_at = job_at; began_left = job_left; }
          (void)began_left;
          // money on the ground is left where it is: there is a clock running
          int who = -1;
          float bd = 1e9f;
          for (int k = 0; k < N_PEDS; k++) {
            uint8_t st = ped_state(peds[k]);
            if (st != PED_WALK && st != PED_RUN) continue;
            if (what == "hunt" && job_seen && !(peds[k].what & PED_MARK)) continue;
            float d = hypotf((peds[k].x - hero.x) / 256.0f, (peds[k].y - hero.y) / 256.0f);
            if (d < bd) { bd = d; who = k; }
          }
          float tx = nav_x + 0.5f, ty = nav_y + 0.5f;
          if (who >= 0 && (what == "spree" || job_seen || !nav_x)) { tx = peds[who].x / 256.0f; ty = peds[who].y / 256.0f; }
          else bd = 99.0f;
          b = steer(tx, ty, &off, &dist);
          aim_since++;
          if (getenv("TRACE") && since % 25 == 0)
            printf("frame %d: hunting: player %.2f,%.2f heading %.0f; after %d at %.2f,%.2f, %.1f cells off, %.2f off the line\n", i,
                   hero.x / 256.0, hero.y / 256.0, hero.hd / 65536.0 * 360.0, who, tx, ty, bd, off);
          // (hunt:3: not from further away than 3 cells; 8 if nothing is said)
          if (bd > (n > 0 ? (float)n : 8.0f)) { if (fabsf(off) < 0.5f) b |= BTN_UP | BTN_A; }
          else if (fabsf(off) < 0.05f && aim_since > 20) { b |= BTN_B; aim_since = 0; }
          done = job == NONE || job_at != began_at;
        } else {
          printf("frame %d: no such order: %s\n", i, what.c_str());
          done = true;
        }
        // (every order begins with the buttons let go: what was held down
        // when the game began, or while getting into a car, does not count)
        if (since < 4) b = 0;
        if (!done && since > 4000) {
          printf("frame %d: order %zu (%s %s) is taking too long: given up\n", i, order, what.c_str(), how.c_str());
          done = true;
        }
        if (done) {
          order++;
          since = 0;
          stuck = backing = 0;
          if (order == orders.size()) { printf("frame %d: all orders done\n", i); report(i); }
        }
        break;
      }
      case 40:                                  // fire at whatever drives past
        for (int k = 0; k < N_CARS; k++) {
          int16_t ahead;
          if (car_state(cars[k]) != CAR_TRAFFIC) continue;
          int16_t offl = off_line(cars[k].x, cars[k].y, ahead);
          if (ahead > 40 && ahead < GUN_RANGE && offl < 100 && since > 20) { b = BTN_B; since = 0; }
        }
        break;
      default:
        break;
    }
    host_buttons = still ? 0 : b;

    host_flash_seeks = host_flash_reads = 0;
    ticks_owed += tpf_exact;
    host_ticks += (uint16_t)ticks_owed;
    ticks_owed -= (int)ticks_owed;
    game_loop();
    {
      // what happened in this frame?
      int now = 0, run = 0, left = 0;
      for (int k = 0; k < N_PEDS; k++) {
        if (ped_state(peds[k]) == PED_DOWN) now++;
        if (ped_state(peds[k]) == PED_RUN) run++;
      }
      for (int k = 0; k < N_CARS; k++) if (car_state(cars[k]) == CAR_LEFT) left++;
      static unsigned money = 0;
      if (cash > money) printf("frame %d: picked up $%u, which makes $%u (sound %d)\n", i, cash - money, cash, host_sound);
      if (cash < money) printf("frame %d: $%u of $%u gone\n", i, money - cash, money);
      money = cash;
      static int stars = 0, life = HEALTH, was_over = 0, police_cars = 0, officers = 0;
      if (wanted != stars) { printf("frame %d: %d stars (record %d)\n", i, wanted, crime); stars = wanted; }
      if (health < life) printf("frame %d: hurt, health %d (sound %d)\n", i, health, host_sound);
      life = health;
      if (over && !was_over) {
        printf("frame %d: %s (sound %d)\n", i, over_set == SPR_WASTED ? "WASTED" : "BUSTED", host_sound);
        report(i);
      }
      if (!over && was_over) { printf("frame %d: back at the start\n", i); report(i); }
      was_over = over;
      int pc = 0, po = 0;
      for (int k = 0; k < N_CARS; k++)
        if (car_state(cars[k]) == CAR_TRAFFIC && car_kind(cars[k]) == CAR_POLICE) pc++;
      for (int k = 0; k < N_PEDS; k++)
        if (ped_state(peds[k]) == PED_RUN && ((peds[k].what >> 2) & 3) == PED_COP) po++;
      if (pc > police_cars) { printf("frame %d: a police car is on its way\n", i); report(i); }
      if (po > officers) { printf("frame %d: an officer is out\n", i); report(i); }
      police_cars = pc;
      officers = po;
      static int lost = 0;
      if (wanted && (calm >= CALM_LOST) != lost) {
        lost = calm >= CALM_LOST;
        printf("frame %d: the police has %s the player (%d stars)\n", i, lost ? "lost" : "found", wanted);
      }
      if (!wanted) lost = 0;
      static int lamp = 0;
      if ((host_light != 0) != lamp) {
        lamp = host_light != 0;
        printf("frame %d: the police light %s (%d stars)\n", i, lamp ? "starts" : "is off", wanted);
      }
      if (getenv("TRACE") && i % 10 == 0) {
        // where the police is
        for (int k = 0; k < N_CARS; k++)
          if (car_state(cars[k]) != CAR_FREE && car_kind(cars[k]) == CAR_POLICE)
            printf("frame %d: police car %d %c at %.1f, %.1f going %c, %.1f cells off\n", i, k,
                   "-TPL"[car_state(cars[k])], cars[k].x / 256.0, cars[k].y / 256.0, "NESW"[car_dir(cars[k])],
                   apart(cars[k].x, cars[k].y) / 256.0);
        for (int k = 0; k < N_PEDS; k++)
          if (ped_state(peds[k]) == PED_RUN && ((peds[k].what >> 2) & 3) == PED_COP)
            printf("frame %d: officer %d at %.1f, %.1f facing %c, %.1f cells off, next shot in %d\n", i, k,
                   peds[k].x / 256.0, peds[k].y / 256.0, "NESW"[peds[k].what & 3], apart(peds[k].x, peds[k].y) / 256.0,
                   peds[k].timer);
      }
      {
        // the way to go: what the label shows, and what it should show
        static int going = 0, shown = -1, wrong = 0, far_wrong = 0, looked = 0;
        if (nav_x && !page && label_show) {
          double dx = (nav_x * 4 + 2) - hero.x / 64.0, dy = (nav_y * 4 + 2) - hero.y / 64.0;
          double far = hypot(dx, dy);
          double turn = atan2(dx, -dy) - cam_yaw / 65536.0 * 6.283185307;
          int way = (int)lround(turn / 6.283185307 * 32) & 31;
          // (half way between two directions either will do)
          double between = fabs(turn / 6.283185307 * 32 - lround(turn / 6.283185307 * 32));
          int off = (nav_way - way) & 31;
          if (between > 0.4 && (off == 1 || off == 31)) off = 0;
          int says = (label_text[3] == FONT_K)
                         ? (label_text[0] - FONT_0) * 1000 + (label_text[2] - FONT_0) * 100
                         : (label_text[0] - FONT_0) * 100 + (label_text[1] - FONT_0) * 10 + (label_text[2] - FONT_0);
          bool far_ok = label_text[3] == FONT_K ? fabs(says - far) < 55 : fabs(says - far) < 4;
          looked++;
          if (off != 0) wrong++;
          if (!far_ok) far_wrong++;
          if (!going || nav_way != shown || !far_ok || off != 0) {
            if (!going || i % 5 == 0 || !far_ok)
              printf("frame %d: the arrow is %d (should be %d), the label says %s (it is %.0f m), label %d, display %d\n", i,
                     nav_way, way, label_says(), far, label_show, disp_nav);
            shown = nav_way;
          }
          going = 1;
        } else if (going && !nav_x) {
          printf("frame %d: there (sound %d); the arrow was off %d times and the distance %d times in %d frames\n", i,
                 host_sound, wrong, far_wrong, looked);
          going = 0;
        }
        static int label = 0;
        if ((disp_nav != 0) != label) {
          label = disp_nav != 0;
          printf("frame %d: the display routine %s the label (label %d)\n", i, label ? "shows" : "no longer shows",
                 label_show);
        }
      }
      {
        // missions: what is on, what it asks for, what the screen says about it
        static int was_job = NONE, was_at = -1, was_note = 0, was_phone = NONE, was_page = 0, was_left = -1;
        static int was_seen = -1, was_stores = 0, was_clock = 0;
        auto hint = [&]() {
          std::string t;
          for (int x = 51; x < 51 + 4 * JOB_HINT; x += 4) {
            int found = '?';
            for (int g = 0; FONT_CHARS[g]; g++)
              if (hud[x] == FONT[g * 3] && hud[x + 1] == FONT[g * 3 + 1] && hud[x + 2] == FONT[g * 3 + 2]) { found = FONT_CHARS[g]; break; }
            t += (char)found;
          }
          while (!t.empty() && t.back() == ' ') t.pop_back();
          return t;
        };
        if (phone != was_phone) {
          if (phone != NONE) printf("frame %d: telephone %d is within reach and rings: it offers mission %d\n", i, phone, job_of(phone));
          else if (page == PAGE_GAME) printf("frame %d: no telephone within reach any more\n", i);
        }
        if (page != was_page && (page == PAGE_JOB || was_page == PAGE_JOB))
          printf("frame %d: %s\n", i, page == PAGE_JOB ? "the telephone is answered: the mission is on the screen" : "back in the game");
        if (job != was_job || (job != NONE && job_at != was_at)) {
          if (job == NONE) printf("frame %d: no mission is on any more; missions done %03d, $%u, kept %d times; offers %d %d %d\n", i,
                                  done_says(), cash, host_stores, job_of(0), job_of(1), job_of(2));
          else printf("frame %d: mission %d, step %d: op %02X place %d,%d n %d; clock %d s, stars %d; on the way to %d,%d\n", i, job,
                      job_at, step.op, step.x, step.y, step.n, job_clock / PLANE_HZ, wanted, nav_x, nav_y);
        }
        static std::string was_hint;
        if (job != NONE && page == PAGE_GAME && hint() != was_hint) {
          printf("frame %d: the screen says \"%s\"%s\n", i, hint().c_str(), job_fit ? "" : " (the car is missing)");
          was_hint = hint();
        }
        if (job != NONE && job_left != was_left && (step.op & 3) == STEP_KILL)
          printf("frame %d: %d to go, %d s left; the screen says \"%s\"\n", i, job_left, job_clock / PLANE_HZ, hint().c_str());
        if (job != NONE && job_seen != was_seen && (step.op & STEP_MARK))
          printf("frame %d: whoever it is about %s\n", i, job_seen ? "is there" : "is not there");
        if (job != NONE && was_clock / PLANE_HZ / 30 != job_clock / PLANE_HZ / 30 && job_at == was_at)
          printf("frame %d: %d s left\n", i, job_clock / PLANE_HZ);
        if (note && !was_note)
          printf("frame %d: MISSION %s (sound %d), for %d frames; the screen says \"%s\"\n", i,
                 note_set == SPR_PASSED ? "PASSED" : "FAILED", host_sound, note, hint().c_str());
        if (!note && was_note) printf("frame %d: the lettering is gone\n", i);
        if (host_stores != was_stores) printf("frame %d: kept: settings %d, $%u, missions %03d\n", i, host_saved, host_cash, done_says());
        was_job = job; was_at = job_at; was_note = note; was_phone = phone; was_page = page; was_left = job_left;
        was_seen = job_seen; was_stores = host_stores; was_clock = job_clock;
      }
      if (getenv("TRACE"))
        for (int k = 0; k < N_PEDS; k++)
          if (peds[k].what & PED_MARK)
            printf("frame %d: marked: %d at %.3f,%.3f facing %c, %s, on %02X\n", i, k, peds[k].x / 256.0, peds[k].y / 256.0,
                   "NESW"[peds[k].what & 3], ped_state(peds[k]) == PED_RUN ? "running" : "walking",
                   cell_at((uint8_t)(peds[k].x >> 8), (uint8_t)(peds[k].y >> 8)));
      static int gripped = 0;
      if (grip && !gripped) printf("frame %d: an officer has got hold of the player\n", i);
      if (!grip && gripped && !over) printf("frame %d: got away\n", i);
      gripped = grip;
      static unsigned sirens = 0;
      if (host_sounds != shots && host_sound == SOUND_SIREN && sirens++ < 3) printf("frame %d: siren\n", i);
      if (host_sounds != shots && host_sound == SOUND_SHOT) {
        printf("frame %d: shot fired, struck at %.2f, %.2f\n", i, shot_x / 256.0, shot_y / 256.0);
        if (getenv("LIST")) {
          for (int k = 0; k < draw_count; k++)
            printf("    sprite %d: column %d row %d, %d x %d, depth %.2f cells\n", k, draw_list[k].c0, draw_list[k].r0,
                   draw_list[k].w, draw_list[k].h, draw_list[k].depth / 4.0);
        }
        if (left_cars >= 0 && left > left_cars) printf("frame %d: a driver left their car\n", i);
      }
      if (now > downed) { printf("frame %d: someone went down\n", i); report(i); }
      else if (run > running) { printf("frame %d: %d people running\n", i, run); report(i); }
      static int shoulder = 0;
      if (cam_shoulder != shoulder) {
        printf("frame %d: camera goes over the %s shoulder (at %.2f, %.2f heading %.0f)\n", i,
               cam_shoulder > 0 ? "right" : "left", hero.x / 256.0, hero.y / 256.0, hero.hd / 65536.0 * 360.0);
        shoulder = cam_shoulder;
      }
      downed = now;
      running = run;
      left_cars = left;
      shots = host_sounds;
    }
    {
      // people who can be made out: in front of the camera, within 8 cells
      int n = 0;
      for (int k = 0; k < N_PEDS; k++) {
        uint8_t st = ped_state(peds[k]);
        if (st != PED_WALK && st != PED_RUN) continue;
        int16_t ahead;
        int16_t offl = off_line(peds[k].x, peds[k].y, ahead);
        if (ahead > 100 && ahead < 8 * 256 && offl < ahead) n++;
      }
      in_sight += n;
      if (n == 0) none_in_sight++;
    }
    seeks += host_flash_seeks;
    reads += host_flash_reads;
    cells += stat_cells;
    stat_cells = 0;
    if (draw_count > most_sprites) most_sprites = draw_count;
    write_frame(out);
    if (i < 2 || i == frames - 1)
      printf("frame %d: seeks %u bytes %u far %u walls %u wallpx %u groundpx %u sprites %d props %u sprcols %u\n", i,
             host_flash_seeks, host_flash_reads, stat_far_cells, stat_walls, stat_wall_px,
             stat_ground_px, draw_count, stat_props, stat_spr_cols);
    if (i % 60 == 59) report(i);
    stat_far_cells = stat_walls = stat_wall_px = stat_ground_px = stat_props = stat_spr_cols = 0;
  }
  fclose(out);
  printf("frames %d: per frame -> flash seeks %.0f, flash bytes %.0f, ray cell steps %.0f, most sprites in a frame %d\n",
         frames, (double)seeks / frames, (double)reads / frames, (double)cells / frames, most_sprites);
  printf("people in sight within 8 cells: %.1f on average, none at all in %.0f%% of the frames\n",
         (double)in_sight / frames, 100.0 * none_in_sight / frames);
  report(frames);
  return 0;
}

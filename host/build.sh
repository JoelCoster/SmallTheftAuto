#!/bin/sh
# Build and run the desktop test build. Usage: host/build.sh [frames] [ticks per frame]
set -e
cd "$(dirname "$0")/.."
mkdir -p build/host
clang++ -std=c++17 -O2 -Wall -Wextra -Wno-unused-function -Wno-ignored-attributes -DHOST -o build/host/host_sim host/host_main.cpp
./build/host/host_sim build/game/fxdata.bin build/host/frames.raw "${1:-220}" "${2:-7}"
python3 tools/frames_to_gif.py build/host/frames.raw build/host/run 45

"""Baseline for maps.paint.build_terrain_buffer.

One shaded view: 160 columns by 48 cells, so 160 by 96 sub-pixels, which
is a wide terminal map. The grid is coastal mountains (open water on the
west, rising land to the east, one inland lake). Climate is left to the
function, which samples the vendored family grid itself.
"""

import gc
import math
import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("LINECAST_CACHE_DIR", "/tmp/linecast-intake/cache")
os.environ.setdefault("LINECAST_CONFIG_DIR", "/tmp/linecast-intake/config")
Path(os.environ["LINECAST_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["LINECAST_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)

from linecast.maps.paint import build_terrain_buffer

W, H = 160, 96  # sub-pixels: 160 columns, 48 cells
BBOX = (-71.6, 41.8, -70.4, 42.8)
RUNS = 7
INNER = 8


def _view():
    elev = []
    water = []
    for y in range(H):
        coast = 36 + int(8 * math.sin(y / 4.0))
        row = []
        wet = []
        for x in range(W):
            if x < coast:
                row.append(-15.0 - (coast - x) * 4.0)
                wet.append(0)
            else:
                row.append((x - coast) * 6.0
                           + 40.0 * math.sin(x / 11.0)
                           + 25.0 * math.cos(y / 7.0))
                wet.append(0)
        elev.append(row)
        water.append(wet)
    # A lake sitting on the hillside, the mask the shader tints apart from the sea.
    for y in range(30, 50):
        for x in range(90, 115):
            if (x - 102) ** 2 + (y - 40) ** 2 < 90:
                water[y][x] = 1
    return elev, water


def _call(elev, water):
    buf = build_terrain_buffer(elev, BBOX, W, H, water=water)
    # Touch the corners and a land pixel so the buffer cannot be dropped,
    # and so a change in the grid shape fails the run.
    return (len(buf), len(buf[0]), buf[0][0], buf[40][120], buf[-1][-1])


def samples(elev, water):
    expect = _call(elev, water)
    if expect[0] != H or expect[1] != W:
        raise SystemExit(f"unexpected buffer shape {expect[:2]}")
    # The first call loads the climate grid. Two more, collector off, warm
    # the shade itself before the samples.
    _call(elev, water)
    gc.disable()
    _call(elev, water)
    _call(elev, water)
    gc.enable()
    out = []
    for _ in range(RUNS):
        gc.disable()
        t0 = time.perf_counter()
        got = None
        for _i in range(INNER):
            got = _call(elev, water)
        elapsed = (time.perf_counter() - t0) * 1000.0 / INNER
        gc.enable()
        out.append(elapsed)
        if got != expect:
            raise SystemExit("terrain buffer changed between runs")
    return out


def main():
    elev, water = _view()
    times = samples(elev, water)
    med = statistics.median(times)
    noise = (max(times) - min(times)) / med * 100.0
    print(f"{med:.4f}")
    print(
        f"noise_pct {noise:.4f} n {len(times)} "
        + " ".join(f"{t:.3f}" for t in times),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

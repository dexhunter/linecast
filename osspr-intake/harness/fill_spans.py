"""Baseline for terminal.braille.fill_spans.

A regional radar window still scan-fills any land ring that touches it.
The timed call is the North America ring from the vendored Natural Earth
basemap, projected the way radar.basemap projects it, into a 120 by 36
cell window over eastern Massachusetts.
"""

import gc
import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("LINECAST_CACHE_DIR", "/tmp/linecast-intake/cache")
os.environ.setdefault("LINECAST_CONFIG_DIR", "/tmp/linecast-intake/config")
Path(os.environ["LINECAST_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["LINECAST_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)

from linecast.radar.basemap import _project, load_data
from linecast.terminal.braille import fill_spans

# Eastern Massachusetts, about a degree tall: a radar frame, not a world view.
BBOX = (-71.6, 41.8, -70.4, 42.8)
GRAPH_W, HEIGHT_CELLS = 120, 36
DW, DH = GRAPH_W * 2, HEIGHT_CELLS * 4
# Vertices in that continent ring, and dots the fill paints. Both pin the
# workload so a drift in the vendored basemap fails here instead of silently
# timing a different polygon.
VERTICES = 19825
FILLED_DOTS = 24502
RUNS = 7
INNER = 3


def _north_america():
    best = None
    best_n = -1
    for rings in load_data()["land"]:
        pts = [p for ring in rings for p in ring]
        lons = [p[0] for p in pts]
        lats = [p[1] for p in pts]
        if (max(lons) < BBOX[0] or min(lons) > BBOX[2]
                or max(lats) < BBOX[1] or min(lats) > BBOX[3]):
            continue
        if len(pts) > best_n:
            best, best_n = rings, len(pts)
    if best is None or best_n != VERTICES:
        raise SystemExit(f"expected the {VERTICES}-vertex land ring, found {best_n}")
    return [[_project(lon, lat, BBOX, DW, DH) for lon, lat in ring]
            for ring in best]


def _filled(rings):
    total = 0
    for _y, xa, xb in fill_spans(rings, DW, DH):
        total += xb - xa
    return total


def samples(rings):
    if _filled(rings) != FILLED_DOTS:
        raise SystemExit("fill checksum changed; the workload is not the one measured")
    # Warm the timed path, collector included, so the samples are the
    # fill and not the first trip through it.
    gc.disable()
    _filled(rings)
    _filled(rings)
    gc.enable()
    out = []
    for _ in range(RUNS):
        gc.disable()
        t0 = time.perf_counter()
        got = 0
        for _i in range(INNER):
            got = _filled(rings)
        elapsed = (time.perf_counter() - t0) * 1000.0 / INNER
        gc.enable()
        out.append(elapsed)
        if got != FILLED_DOTS:
            raise SystemExit("fill checksum changed mid-run")
    return out


def main():
    rings = _north_america()
    times = samples(rings)
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

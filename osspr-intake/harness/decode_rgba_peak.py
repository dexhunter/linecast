"""Peak Python heap for _png.decode_rgba on the vendored climate grid.

climate.png is 3600 by 1800 grayscale, filter None, and it is decoded
once at startup to colour the terrain ramps. The figure is tracemalloc's
peak during decode_rgba, after the file bytes are already in hand.
"""

import statistics
import sys
import tracemalloc
from pathlib import Path

from linecast._png import decode_rgba

PNG = Path("src/linecast/data/climate.png")
RUNS = 7
WIDTH, HEIGHT = 3600, 1800


def _peak(data):
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        w, h, rgba = decode_rgba(data)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if (w, h) != (WIDTH, HEIGHT) or len(rgba) != WIDTH * HEIGHT * 4:
        raise SystemExit(f"unexpected decode {(w, h)} len {len(rgba)}")
    return peak


def main():
    data = PNG.read_bytes()
    peaks = [_peak(data) for _ in range(RUNS)]
    med = statistics.median(peaks)
    noise = (max(peaks) - min(peaks)) / med * 100.0
    # Integer bytes. Median of an odd run count is one of the samples.
    print(int(med))
    print(
        f"noise_pct {noise:.6f} n {len(peaks)} " + " ".join(str(p) for p in peaks),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

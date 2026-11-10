"""Baseline for _png._unfilter_paeth.

One 256 by 256 RGB tile, Paeth on every scanline: the shape of a
terrarium elevation tile. The bytes are a smooth height field, which is
what that filter sees on real terrain, and the timer covers only the
unfilter of those rows.
"""

import gc
import math
import statistics
import sys
import time

from linecast._png import _unfilter_paeth

W, H, BPP = 256, 256, 3
RUNS = 7
INNER = 8


def _encoded_rows():
    """Paeth-encoded scanlines of a smooth RGB height field, and the
    reconstructed previous-row seed (zeros, as in a PNG)."""
    prev = bytearray(W * BPP)
    raws = []
    for y in range(H):
        row = bytearray(W * BPP)
        for x in range(W):
            e = (80 + x // 3 + y // 5
                 + int(12 * math.sin(x / 17.0) + 8 * math.cos(y / 11.0))) & 255
            i = x * BPP
            row[i] = e
            row[i + 1] = (40 + e // 2) & 255
            row[i + 2] = (20 + e // 3) & 255
        enc = bytearray(W * BPP)
        for i in range(W * BPP):
            left = row[i - BPP] if i >= BPP else 0
            up = prev[i]
            ul = prev[i - BPP] if i >= BPP else 0
            p = left + up - ul
            pa, pb, pc = abs(p - left), abs(p - up), abs(p - ul)
            if pa <= pb and pa <= pc:
                pred = left
            elif pb <= pc:
                pred = up
            else:
                pred = ul
            enc[i] = (row[i] - pred) & 255
        raws.append(bytes(enc))
        prev = row
    return raws


def _unfilter_all(raws):
    prev = bytes(W * BPP)
    acc = 0
    for raw in raws:
        prev = _unfilter_paeth(raw, prev, BPP)
        acc = (acc + prev[0] + prev[W] + prev[-1]) & 0xFFFFFFFF
    return acc


def samples(raws):
    expect = _unfilter_all(raws)
    gc.disable()
    _unfilter_all(raws)
    _unfilter_all(raws)
    gc.enable()
    out = []
    for _ in range(RUNS):
        gc.disable()
        t0 = time.perf_counter()
        got = None
        for _i in range(INNER):
            got = _unfilter_all(raws)
        elapsed = (time.perf_counter() - t0) * 1000.0 / INNER
        gc.enable()
        out.append(elapsed)
        if got != expect:
            raise SystemExit("Paeth reconstruction changed between runs")
    return out


def main():
    raws = _encoded_rows()
    if len(raws) != H or len(raws[0]) != W * BPP:
        raise SystemExit("tile is not 256x256 RGB")
    times = samples(raws)
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

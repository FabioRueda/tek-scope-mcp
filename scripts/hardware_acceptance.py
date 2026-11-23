"""Hardware acceptance for the control library (build step 2).

Needs the oscilloscope on USB with the CH1 probe on PROBE COMP and the probe
switch at 10X. Saves SET? to local/backup/ first and restores it at the end.

Writes docs/ch1.csv, docs/ch1.png and docs/screen.png, and a JSON result to
local/logs/.
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tek_scope import RestoreError, TekScope


def plot(t, v, pre, path):
    fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
    ax.plot(t * 1e3, v, linewidth=0.8)
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("CH1 (V)")
    ax.set_title("TDS 1012C-EDU, CH1 on PROBE COMP (2500 points)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup_dir = ROOT / "local" / "backup"
    logs_dir = ROOT / "local" / "logs"
    docs = ROOT / "docs"
    backup_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    result = {"stamp": stamp}

    with TekScope() as s:
        s.write("*CLS")
        before = s.state()
        (backup_dir / f"SET-antes-{stamp}.txt").write_text(before, encoding="utf-8")
        try:
            s.channel_probe(1, 10)
            result["probe"] = s.channel_probe(1)
            freq = s.measure("FREQuency", 1)
            pk2pk = s.measure("PK2pk", 1)
            result["frequency_hz"] = freq
            result["pk2pk_v"] = pk2pk
            result["accept_1"] = 950 <= freq <= 1050
            result["accept_2"] = 4.5 <= pk2pk <= 5.5

            t, v, pre = s.waveform(1)
            s.save_csv(docs / "ch1.csv")
            plot(t, v, pre, docs / "ch1.png")
            result["points"] = len(v)
            result["v_min"], result["v_max"] = float(v.min()), float(v.max())
            result["preamble"] = {k: pre[k] for k in ("NR_PT", "XINCR", "XZERO", "PT_OFF", "YMULT", "YZERO", "YOFF")}
            result["accept_3"] = len(v) == 2500

            s.screenshot(docs / "screen.png")
            result["screen_bytes"] = (docs / "screen.png").stat().st_size
            result["accept_4"] = result["screen_bytes"] > 0
            result["errors_during_test"] = s.errors()
        finally:
            try:
                removed = s.restore(before)
            except RestoreError as exc:  # report it (accept_6 will fail); do not hide it
                removed = []
                result["restore_error"] = str(exc)
            after = s.state()
            (backup_dir / f"SET-depois-{stamp}.txt").write_text(after, encoding="utf-8")
            result["restore_removed"] = removed
            result["errors_end"] = s.errors()
            result["accept_5"] = result["errors_end"] == []
            result["accept_6"] = after == before
            if after != before:
                b, a = before.split(";"), after.split(";")
                result["set_diff"] = [(x, y) for x, y in zip(b, a) if x != y]

    (logs_dir / f"aceite-2-{stamp}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if all(result.get(f"accept_{i}") for i in range(1, 7)) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Local MCP server (stdio) for the Tektronix TDS 1012C-EDU, built on tek_scope.py.

Read tools run without confirmation. Tools that change instrument settings need
confirm=true, and disappear when TEK_SCOPE_READONLY=1. The fixed blocklist of
tek_scope.py (see CLAUDE.md) applies to every command, and no tool can lift it.

The VISA connection is opened for each call and closed afterwards, so a timeout
never leaves a stale session behind (the next call opens a fresh one). The
instrument takes about 5 s to answer SET? and *LRN?, so those get 30 s.
"""

from __future__ import annotations

import contextlib
import functools
import math
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from tek_scope import (
    CHANNELS,
    LONG_TIMEOUT_MS,
    ROOT,
    BlockedCommandError,
    TekScope,
    _matches,
    blocked_reason,
    segment_headers,
)

READONLY_ENV = "TEK_SCOPE_READONLY"
MAX_POINTS = 500

# Argument lists come from the programmer manual (part number 077044403).
MEASURE_TYPES = (
    "CRMs", "CURSORRms", "FALL", "FREQuency", "MAXImum", "MEAN", "MINImum",
    "NWIdth", "PDUty", "PERIod", "PHAse", "PK2pk", "PWIdth", "RISe",
)  # fmt: skip
COUPLINGS = ("AC", "DC", "GND")
PROBES = (1, 10, 20, 50, 100, 500, 1000)
TRIGGER_SOURCES = ("CH1", "CH2", "EXT", "EXT5", "LINE")
TRIGGER_SLOPES = ("FALL", "RISe")
TRIGGER_COUPLINGS = ("AC", "DC", "HFRej", "LFRej", "NOISErej")
TRIGGER_MODES = ("AUTO", "NORMal")
ACQUIRE_MODES = ("SAMple", "PEAKdetect", "AVErage")
ACQUIRE_STOP_AFTER = ("RUNSTop", "SEQuence")
AVERAGES = (4, 16, 64, 128)

INSTRUCTIONS = (
    "Tektronix TDS 1012C-EDU oscilloscope over USB. Read tools are safe. Tools that change settings need "
    "confirm=true. Calibration, factory, save/recall, *RST and similar commands are blocked and cannot be sent."
)


class ConfirmationRequired(ValueError):
    """A tool that changes the instrument was called without confirm=true."""


# ---------------------------------------------------------------------------
# Checks done before the instrument is opened
# ---------------------------------------------------------------------------


def error_text(exc: Exception) -> str:
    """A short message for the model. Only the exception text, no stack."""
    msg = str(exc) or type(exc).__name__
    if "TMO" in msg or "imeout" in msg:
        msg += " (no reply from the instrument: unknown query, or it is busy)"
    return msg


def _require_confirm(confirm: bool) -> None:
    if confirm is not True:
        raise ConfirmationRequired("This tool changes the instrument. Call it again with confirm=true.")


def _check_text(cmd: str) -> str:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in cmd):
        raise ValueError("control characters are not allowed in a command")
    cmd = cmd.strip()
    if not cmd:
        raise ValueError("empty command")
    reason = blocked_reason(cmd)
    if reason:
        raise BlockedCommandError(f"{cmd!r}: {reason}")
    return cmd


def check_query(cmd: str) -> str:
    """Validate one query for scope_query and return it cleaned."""
    cmd = _check_text(cmd)
    headers = segment_headers(cmd)
    if len(headers) != 1:
        raise ValueError("send one query per call")
    if not headers[0].endswith("?"):
        raise ValueError("scope_query only sends queries (the header must end with '?'); use scope_write to set")
    first = headers[0].rstrip("?").split(":")[0]
    if _matches(first, "CURV", "CURVE") or _matches(first, "WAVF", "WAVFRM"):
        raise ValueError("waveform data is binary: use scope_waveform")
    if _matches(first, "HARDC", "HARDCOPY"):
        raise ValueError("hard copy is binary: use scope_screenshot")
    return cmd


def check_write(cmd: str) -> str:
    """Validate a program message for scope_write and return it cleaned."""
    cmd = _check_text(cmd)
    if any(h.endswith("?") for h in segment_headers(cmd)):
        raise ValueError("scope_write does not send queries; use scope_query")
    return cmd


def _is_long_query(cmd: str) -> bool:
    header = segment_headers(cmd)[0].rstrip("?")
    return header == "*LRN" or _matches(header, "SET", "SET")


def _choice(value: str, allowed: tuple[str, ...], what: str) -> str:
    """Match value to an allowed spelling, ignoring case. Returns the manual's spelling."""
    for item in allowed:
        if str(value).strip().upper() == item.upper():
            return item
    raise ValueError(f"{what} must be one of {', '.join(allowed)}")


def _channel(canal: int) -> int:
    if canal not in CHANNELS:
        raise ValueError(f"canal must be one of {CHANNELS}")
    return canal


def _number(value: float, what: str, positive: bool = False) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"{what} must be a finite number")
    if positive and value <= 0:
        raise ValueError(f"{what} must be greater than zero")
    return f"{value:.6G}"


def _on_off(value: bool) -> str:
    if not isinstance(value, bool):
        raise TypeError("value must be true or false")
    return "ON" if value else "OFF"


# ---------------------------------------------------------------------------
# Waveform summary
# ---------------------------------------------------------------------------


def summarize_waveform(t, v, max_points: int = MAX_POINTS) -> dict:
    t, v = np.asarray(t, dtype=float), np.asarray(v, dtype=float)
    if len(v) == 0:
        raise ValueError("empty waveform")
    idx = np.unique(np.linspace(0, len(v) - 1, min(len(v), max_points)).round().astype(int))
    return {
        "n_points": len(v),
        "stats": {
            "min": float(v.min()),
            "max": float(v.max()),
            "mean": float(v.mean()),
            "pk2pk": float(v.max() - v.min()),
            "rms": float(np.sqrt(np.mean(v**2))),
        },
        "time_start_s": float(t[0]),
        "time_end_s": float(t[-1]),
        "sample_interval_s": float(t[1] - t[0]) if len(t) > 1 else None,
        "points": [[float(t[i]), float(v[i])] for i in idx],
    }


# ---------------------------------------------------------------------------
# The server
# ---------------------------------------------------------------------------


def create_server(
    scope_factory: Callable[[], TekScope] = TekScope,
    readonly: bool | None = None,
    data_dir: Path | str | None = None,
) -> MCPServer:
    if readonly is None:
        readonly = os.environ.get(READONLY_ENV, "") not in ("", "0")
    out_dir = Path(data_dir) if data_dir is not None else ROOT / "local"
    mcp = MCPServer("tek-scope", instructions=INSTRUCTIONS)

    def tool():
        """Register a tool whose errors reach the model as text (the SDK hides plain exceptions)."""

        def register(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                try:
                    return fn(*args, **kwargs)
                except ToolError:
                    raise
                except Exception as exc:
                    raise ToolError(error_text(exc)) from exc

            mcp.tool()(wrapper)
            return fn

        return register

    @contextlib.contextmanager
    def session(timeout_ms: int | None = None):
        """Open the instrument for one call, close it afterwards (also after an error)."""
        with scope_factory() as scope:
            if timeout_ms is None:
                yield scope
                return
            old = scope.resource.timeout
            scope.resource.timeout = timeout_ms
            try:
                yield scope
            finally:
                scope.resource.timeout = old

    def stamp() -> str:
        return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")

    def events(scope: TekScope) -> list[dict]:
        return [{"code": c, "message": m} for c, m in scope.errors()]

    # -- read tools -----------------------------------------------------------

    @tool()
    def scope_idn() -> str:
        """Return the instrument identity (*IDN?)."""
        with session() as scope:
            return scope.idn()

    @tool()
    def scope_state() -> str:
        """Return all current settings (SET?). The instrument takes about 5 s."""
        with session(LONG_TIMEOUT_MS) as scope:
            return scope.state()

    @tool()
    def scope_errors() -> dict:
        """Read and clear the instrument's error and event queue (*ESR? then ALLEv?)."""
        with session() as scope:
            return {"events": events(scope)}

    @tool()
    def scope_query(cmd: str) -> str:
        """Send one query from the programmer manual (header ends with '?') and return the reply.

        Blocked commands are refused. A query the instrument does not know gets no reply and times out.
        """
        cmd = check_query(cmd)
        with session(LONG_TIMEOUT_MS if _is_long_query(cmd) else None) as scope:
            return scope.query(cmd)

    @tool()
    def scope_measure(tipo: str, canal: int) -> dict:
        """Take one immediate measurement (MEASUrement:IMMed) on CH1 or CH2.

        tipo is one of: CRMs, CURSORRms, FALL, FREQuency, MAXImum, MEAN, MINImum, NWIdth, PDUty, PERIod, PHAse,
        PK2pk, PWIdth, RISe (case does not matter). This sets the immediate-measurement source and type.
        """
        kind = _choice(tipo, MEASURE_TYPES, "tipo")
        ch = _channel(canal)
        with session() as scope:
            value = scope.measure(kind, ch)
            unit = scope.measure_units()
        return {"type": kind, "channel": ch, "value": value, "unit": unit}

    @tool()
    def scope_waveform(canal: int) -> dict:
        """Read 2500 waveform points from CH1 or CH2.

        Returns statistics in volts, the path of a CSV with every point, and at most 500 points
        as [time_s, volts]. The channel must be displayed. This sets the DATa:* source and format.
        """
        ch = _channel(canal)
        with session() as scope:
            t, v, pre = scope.waveform(ch)
            out_dir.joinpath("waveforms").mkdir(parents=True, exist_ok=True)
            path = out_dir / "waveforms" / f"ch{ch}-{stamp()}.csv"
            scope.save_csv(path)
        summary = summarize_waveform(t, v)
        return {"channel": ch, "csv_path": str(path), "y_unit": pre["YUNIT"], "x_unit": pre["XUNIT"], **summary}

    @tool()
    def scope_screenshot() -> Image:
        """Capture the screen as a PNG image. This sets HARDCopy:FORMat BMP and HARDCopy:PORT USB."""
        out_dir.joinpath("screenshots").mkdir(parents=True, exist_ok=True)
        path = out_dir / "screenshots" / f"screen-{stamp()}.png"
        with session() as scope:
            scope.screenshot(path)
        return Image(path=path)

    if readonly:
        return mcp

    # -- tools that change settings (need confirm=true) ------------------------

    def apply(applied: dict, writes: Callable[[TekScope], object]) -> dict:
        with session() as scope:
            writes(scope)
            return {"applied": applied, "errors": events(scope)}

    @tool()
    def scope_set_channel(
        canal: int,
        scale: float | None = None,
        position: float | None = None,
        coupling: str | None = None,
        probe: int | None = None,
        bandwidth: bool | None = None,
        invert: bool | None = None,
        confirm: bool = False,
    ) -> dict:
        """Change CH1 or CH2: scale (V/div), position (div), coupling AC|DC|GND, probe (1, 10, 20, 50, 100, 500,
        1000), bandwidth limit (true = 20 MHz), invert. Needs confirm=true. Give at least one setting."""
        _require_confirm(confirm)
        ch = _channel(canal)
        steps: list[tuple[str, str, str]] = []
        if scale is not None:
            steps.append(("scale", "channel_scale", _number(scale, "scale", positive=True)))
        if position is not None:
            steps.append(("position", "channel_position", _number(position, "position")))
        if coupling is not None:
            steps.append(("coupling", "channel_coupling", _choice(coupling, COUPLINGS, "coupling")))
        if probe is not None:
            if probe not in PROBES:
                raise ValueError(f"probe must be one of {PROBES}")
            steps.append(("probe", "channel_probe", str(probe)))
        if bandwidth is not None:
            steps.append(("bandwidth", "channel_bandwidth", _on_off(bandwidth)))
        if invert is not None:
            steps.append(("invert", "channel_invert", _on_off(invert)))
        if not steps:
            raise ValueError("give at least one setting")
        return apply(
            {"channel": ch, **{name: value for name, _, value in steps}},
            lambda scope: [getattr(scope, method)(ch, value) for _, method, value in steps],
        )

    @tool()
    def scope_set_timebase(scale: float | None = None, position: float | None = None, confirm: bool = False) -> dict:
        """Change the main timebase: scale (s/div) and position (s). Needs confirm=true."""
        _require_confirm(confirm)
        steps = []
        if scale is not None:
            steps.append(("scale", "horizontal_scale", _number(scale, "scale", positive=True)))
        if position is not None:
            steps.append(("position", "horizontal_position", _number(position, "position")))
        if not steps:
            raise ValueError("give at least one setting")
        return apply(
            {name: value for name, _, value in steps},
            lambda scope: [getattr(scope, method)(value) for _, method, value in steps],
        )

    @tool()
    def scope_set_trigger(
        source: str | None = None,
        slope: str | None = None,
        coupling: str | None = None,
        level: float | None = None,
        mode: str | None = None,
        confirm: bool = False,
    ) -> dict:
        """Change the edge trigger: source CH1|CH2|EXT|EXT5|LINE, slope RISe|FALL, coupling
        AC|DC|HFRej|LFRej|NOISErej, level (V) and mode AUTO|NORMal. Needs confirm=true."""
        _require_confirm(confirm)
        steps = []
        if source is not None:
            steps.append(("source", "trigger_source", _choice(source, TRIGGER_SOURCES, "source")))
        if slope is not None:
            steps.append(("slope", "trigger_slope", _choice(slope, TRIGGER_SLOPES, "slope")))
        if coupling is not None:
            steps.append(("coupling", "trigger_coupling", _choice(coupling, TRIGGER_COUPLINGS, "coupling")))
        if level is not None:
            steps.append(("level", "trigger_level", _number(level, "level")))
        if mode is not None:
            steps.append(("mode", "trigger_mode", _choice(mode, TRIGGER_MODES, "mode")))
        if not steps:
            raise ValueError("give at least one setting")
        return apply(
            {name: value for name, _, value in steps},
            lambda scope: [getattr(scope, method)(value) for _, method, value in steps],
        )

    @tool()
    def scope_set_acquisition(
        mode: str | None = None,
        num_avg: int | None = None,
        stop_after: str | None = None,
        confirm: bool = False,
    ) -> dict:
        """Change acquisition: mode SAMple|PEAKdetect|AVErage, number of averages (4, 16, 64, 128) and
        stop_after RUNSTop|SEQuence. Needs confirm=true."""
        _require_confirm(confirm)
        steps = []
        if mode is not None:
            steps.append(("mode", "acquire_mode", _choice(mode, ACQUIRE_MODES, "mode")))
        if num_avg is not None:
            if num_avg not in AVERAGES:
                raise ValueError(f"num_avg must be one of {AVERAGES}")
            steps.append(("num_avg", "acquire_num_avg", str(num_avg)))
        if stop_after is not None:
            steps.append(("stop_after", "acquire_stop_after", _choice(stop_after, ACQUIRE_STOP_AFTER, "stop_after")))
        if not steps:
            raise ValueError("give at least one setting")
        return apply(
            {name: value for name, _, value in steps},
            lambda scope: [getattr(scope, method)(value) for _, method, value in steps],
        )

    @tool()
    def scope_run(confirm: bool = False) -> dict:
        """Start continuous acquisition (RUN). Needs confirm=true."""
        _require_confirm(confirm)
        return apply({"action": "run"}, lambda scope: scope.run())

    @tool()
    def scope_stop(confirm: bool = False) -> dict:
        """Stop acquisition (STOP). Needs confirm=true."""
        _require_confirm(confirm)
        return apply({"action": "stop"}, lambda scope: scope.stop())

    @tool()
    def scope_single(confirm: bool = False) -> dict:
        """Take a single sequence and wait until it is complete. Needs confirm=true."""
        _require_confirm(confirm)
        return apply({"action": "single"}, lambda scope: scope.single())

    @tool()
    def scope_autoset(confirm: bool = False) -> dict:
        """Run autoset. It changes scale, timebase and trigger. Needs confirm=true."""
        _require_confirm(confirm)
        return apply({"action": "autoset"}, lambda scope: scope.autoset())

    @tool()
    def scope_write(cmd: str, confirm: bool = False) -> dict:
        """Send one command from the programmer manual that is not a query. Blocked commands are refused.
        Needs confirm=true. Check the command in the manual first: do not guess syntax."""
        _require_confirm(confirm)
        cmd = check_write(cmd)
        return apply({"cmd": cmd}, lambda scope: scope.write(cmd))

    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()

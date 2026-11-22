"""Control library for the Tektronix TDS 1012C-EDU over USBTMC (PyVISA).

Every command used here was checked against the Tektronix programmer manual,
part number 077044403. Commands in the fixed blocklist (see CLAUDE.md) are
refused by write() and query() unless allow_dangerous=True is passed.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import os
import struct
import sys
from pathlib import Path
from typing import Self

import numpy as np

ROOT = Path(__file__).resolve().parent
DEFAULT_LOG = ROOT / "local" / "logs" / "escritas.log"
DEFAULT_LOCK = ROOT / "local" / "tek_scope.lock"
TEKTRONIX_VID = "0x0699"

DEFAULT_TIMEOUT_MS = 10_000
LONG_TIMEOUT_MS = 30_000
INVALID_MEASUREMENT = 9.9e37
CHANNELS = (1, 2)


class BlockedCommandError(PermissionError):
    """A command from the fixed blocklist was refused."""


class MeasurementError(RuntimeError):
    """The instrument returned 9.9E37 (no valid measurement)."""


class WaveformError(RuntimeError):
    """The waveform could not be read (for example, the channel is off)."""


# ---------------------------------------------------------------------------
# Command parsing and the blocklist
# ---------------------------------------------------------------------------


def _split_segments(cmd: str) -> list[str]:
    """Split a program message on ';', ignoring ';' inside quoted strings."""
    segments, current, quote = [], [], None
    for ch in cmd:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            current.append(ch)
        elif ch == ";":
            segments.append("".join(current))
            current = []
        else:
            current.append(ch)
    segments.append("".join(current))
    return [s.strip() for s in segments if s.strip()]


def _segment_header(segment: str) -> str:
    return segment.split(None, 1)[0]


def _absolute_headers(segments: list[str]) -> list[str]:
    """Resolve each segment's header to a full path (manual: Concatenating Commands)."""
    headers, prefix = [], ""
    for seg in segments:
        head = _segment_header(seg).upper()
        if head.startswith("*"):
            full = head
        elif head.startswith(":"):
            full = head[1:]
        else:
            full = prefix + head if prefix else head
        if not full.startswith("*"):
            parts = full.split(":")
            prefix = ":".join(parts[:-1]) + ":" if len(parts) > 1 else ""
        headers.append(full)
    return headers


def segment_headers(cmd: str) -> list[str]:
    """Return the full header of each command in a program message, upper case."""
    return _absolute_headers(_split_segments(cmd))


def _matches(node: str, short: str, long: str) -> bool:
    """True if a header node is a valid spelling of a mnemonic (short..long form)."""
    node = node.rstrip("?")
    return node.startswith(short) and long.startswith(node)


def _header_blocked(header: str) -> str | None:
    is_query = header.endswith("?")
    bare = header.rstrip("?")
    if bare in ("*CAL", "*TST", "*RST"):
        return f"{bare} is blocked"
    nodes = bare.split(":")
    first = nodes[0]
    if _matches(first, "FAC", "FACTORY") and len(nodes) == 1:
        return "FACtory is blocked"
    if _matches(first, "CAL", "CALIBRATE"):
        if len(nodes) == 2 and _matches(nodes[1], "STATUS", "STATUS") and is_query:
            return None
        return "CALibrate: commands other than CALibrate:STATUS? are blocked"
    if _matches(first, "SAV", "SAVE"):
        return "SAVe: commands are blocked"
    if _matches(first, "RECA", "RECALL"):
        return "RECAll: commands are blocked"
    if _matches(first, "FILES", "FILESYSTEM") and not is_query:
        return "FILESystem: commands that are not queries are blocked"
    if _matches(first, "DIA", "DIAG") and not is_query:
        return "DIAg: commands that are not queries are blocked"
    return None


def blocked_reason(cmd: str) -> str | None:
    """Return why a program message is blocked, or None if it may be sent."""
    for header in segment_headers(cmd):
        reason = _header_blocked(header)
        if reason:
            return reason
    return None


def strip_blocked_segments(text: str) -> tuple[str, list[str]]:
    """Remove blocked commands (and their relative followers) from a SET? response.

    A relative segment (no leading ':') belongs to the absolute segment before it,
    so it is removed together with it.
    """
    segments = _split_segments(text)
    headers = _absolute_headers(segments)
    kept, removed, dropping = [], [], False
    for seg, header in zip(segments, headers):
        absolute = seg.startswith((":", "*")) or seg is segments[0]
        if absolute:
            dropping = _header_blocked(header) is not None
        if dropping or _header_blocked(header):
            removed.append(seg)
        else:
            kept.append(seg)
    return ";".join(kept), removed


# ---------------------------------------------------------------------------
# One connection at a time
# ---------------------------------------------------------------------------


class ScopeLock:
    """Exclusive lock on a file. The OS releases it if the process dies."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._fh = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+")  # noqa: SIM115 - held open while the lock is taken
        try:
            if sys.platform == "win32":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            fh.close()
            raise RuntimeError(f"Oscilloscope in use by another process (lock {self.path.name})") from exc
        fh.seek(0)
        fh.truncate()
        fh.write(str(os.getpid()))
        fh.flush()
        self._fh = fh

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None


# ---------------------------------------------------------------------------
# The instrument
# ---------------------------------------------------------------------------


def find_resource(rm) -> str:
    """Return the VISA resource name: TEK_SCOPE_RESOURCE, or the first Tektronix USB device."""
    name = os.environ.get("TEK_SCOPE_RESOURCE")
    if name:
        return name
    for res in rm.list_resources():
        if res.upper().startswith("USB") and TEKTRONIX_VID in res.lower():
            return res
    raise RuntimeError("No Tektronix USB instrument found; set TEK_SCOPE_RESOURCE")


class TekScope:
    """TDS 1012C-EDU controller. Use as a context manager or call connect()/close()."""

    def __init__(self, resource=None, resource_name=None, log_path=DEFAULT_LOG, lock_path=DEFAULT_LOCK):
        self.resource = resource
        self.resource_name = resource_name
        self.log_path = Path(log_path)
        self._lock = ScopeLock(lock_path)
        self._rm = None
        self._owns_resource = resource is None
        self.last_waveform = None

    # -- connection ---------------------------------------------------------

    def connect(self) -> TekScope:
        self._lock.acquire()
        try:
            if self.resource is None:
                import pyvisa

                self._rm = pyvisa.ResourceManager()
                name = self.resource_name or find_resource(self._rm)
                self.resource = self._rm.open_resource(name)
            self.resource.timeout = DEFAULT_TIMEOUT_MS
            self.resource.read_termination = "\n"
            self.resource.write_termination = "\n"
        except Exception:
            self._lock.release()
            raise
        return self

    def close(self) -> None:
        try:
            if self.resource is not None:
                self.resource.close()
                if self._owns_resource:
                    self.resource = None
            if self._rm is not None:
                self._rm.close()
                self._rm = None
        finally:
            self._lock.release()

    def __enter__(self) -> Self:
        return self.connect()

    def __exit__(self, *exc) -> None:
        self.close()

    # -- raw I/O --------------------------------------------------------------

    def _log(self, line: str) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().isoformat(timespec="seconds")
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp}\t{line}\n")

    def _check(self, cmd: str, allow_dangerous: bool) -> None:
        reason = blocked_reason(cmd)
        if reason and not allow_dangerous:
            self._log(f"REFUSED\t{cmd}\t{reason}")
            raise BlockedCommandError(f"{cmd!r}: {reason}")
        if reason:
            self._log(f"DANGEROUS-ALLOWED\t{cmd}")

    def write(self, cmd: str, allow_dangerous: bool = False) -> None:
        self._check(cmd, allow_dangerous)
        self._log(f"WRITE\t{cmd}")
        self.resource.write(cmd)

    def query(self, cmd: str, allow_dangerous: bool = False) -> str:
        self._check(cmd, allow_dangerous)
        if any(not h.endswith("?") for h in segment_headers(cmd)):
            self._log(f"WRITE\t{cmd}")  # a query line that also sets something
        return self.resource.query(cmd).strip()

    def _query_float(self, cmd: str) -> float:
        return float(self.query(cmd).split()[-1])

    def _wait_opc(self, timeout_ms: int = LONG_TIMEOUT_MS) -> None:
        old = self.resource.timeout
        self.resource.timeout = timeout_ms
        try:
            self.query("*OPC?")
        finally:
            self.resource.timeout = old

    # -- base -----------------------------------------------------------------

    def idn(self) -> str:
        return self.query("*IDN?")

    def state(self) -> str:
        """Full settings (SET?)."""
        return self.query("SET?")

    def errors(self) -> list[tuple[int | None, str]]:
        """Read *ESR? then ALLEv?. Empty list means no errors or events."""
        esr = int(self.query("*ESR?").split()[-1])
        raw = self.query("ALLEv?")
        if raw.upper().startswith(":ALLEV ") or raw.upper().startswith("ALLEV "):
            raw = raw.split(None, 1)[1]
        events = []
        for code, msg in _parse_events(raw):
            if code not in (0, 1):
                events.append((code, msg))
        if not events and esr & 0b0011_1100:  # CME, EXE, DDE, QYE
            events.append((None, f"ESR={esr}"))
        return events

    def restore(self, set_text: str) -> list[str]:
        """Send a SET? response back, without blocked segments. Returns what was removed."""
        clean, removed = strip_blocked_segments(set_text)
        # One message per absolute header and its relative followers: the whole
        # SET? text in one write can stall the USB input past the timeout.
        groups: list[list[str]] = []
        for seg in _split_segments(clean):
            if seg.startswith((":", "*")) or not groups:
                groups.append([seg])
            else:
                groups[-1].append(seg)
        old = self.resource.timeout
        self.resource.timeout = LONG_TIMEOUT_MS
        try:
            for group in groups:
                self.write(";".join(group))
        finally:
            self.resource.timeout = old
        self._wait_opc()
        return removed

    # -- channels ---------------------------------------------------------------

    @staticmethod
    def _ch(ch: int) -> str:
        if ch not in CHANNELS:
            raise ValueError(f"channel must be one of {CHANNELS}")
        return f"CH{ch}"

    def _get_set(self, header: str, value, as_float: bool):
        if value is None:
            return self._query_float(header + "?") if as_float else self.query(header + "?").split()[-1]
        self.write(f"{header} {value}")
        return None

    def channel_scale(self, ch: int, value=None):
        return self._get_set(f"{self._ch(ch)}:SCAle", value, True)

    def channel_position(self, ch: int, value=None):
        return self._get_set(f"{self._ch(ch)}:POSition", value, True)

    def channel_coupling(self, ch: int, value=None):
        return self._get_set(f"{self._ch(ch)}:COUPling", value, False)

    def channel_probe(self, ch: int, value=None):
        return self._get_set(f"{self._ch(ch)}:PRObe", value, True)

    def channel_bandwidth(self, ch: int, value=None):
        return self._get_set(f"{self._ch(ch)}:BANdwidth", value, False)

    def channel_invert(self, ch: int, value=None):
        return self._get_set(f"{self._ch(ch)}:INVert", value, False)

    # -- horizontal ---------------------------------------------------------------

    def horizontal_scale(self, value=None):
        return self._get_set("HORizontal:MAIn:SCAle", value, True)

    def horizontal_position(self, value=None):
        return self._get_set("HORizontal:MAIn:POSition", value, True)

    # -- edge trigger -------------------------------------------------------------

    def trigger_source(self, value=None):
        return self._get_set("TRIGger:MAIn:EDGE:SOUrce", value, False)

    def trigger_slope(self, value=None):
        return self._get_set("TRIGger:MAIn:EDGE:SLOpe", value, False)

    def trigger_coupling(self, value=None):
        return self._get_set("TRIGger:MAIn:EDGE:COUPling", value, False)

    def trigger_level(self, value=None):
        return self._get_set("TRIGger:MAIn:LEVel", value, True)

    def trigger_mode(self, value=None):
        return self._get_set("TRIGger:MAIn:MODe", value, False)

    def trigger_state(self) -> str:
        return self.query("TRIGger:STATE?").split()[-1]

    # -- acquisition ----------------------------------------------------------------

    def acquire_state(self, value=None):
        return self._get_set("ACQuire:STATE", value, False)

    def acquire_stop_after(self, value=None):
        return self._get_set("ACQuire:STOPAfter", value, False)

    def acquire_mode(self, value=None):
        return self._get_set("ACQuire:MODe", value, False)

    def acquire_num_avg(self, value=None):
        return self._get_set("ACQuire:NUMAVg", value, False)

    def run(self) -> None:
        self.write("ACQuire:STOPAfter RUNSTop")
        self.write("ACQuire:STATE RUN")
        self._wait_opc()

    def stop(self) -> None:
        self.write("ACQuire:STATE STOP")
        self._wait_opc()

    def single(self) -> None:
        """Single sequence; *OPC? returns when the acquisition is complete."""
        self.write("ACQuire:STOPAfter SEQuence")
        self.write("ACQuire:STATE RUN")
        self._wait_opc()

    def autoset(self) -> None:
        self.write("AUTOSet EXECute")
        self._wait_opc()

    # -- measurements -----------------------------------------------------------------

    def measure(self, kind: str, ch: int) -> float:
        self.write(f"MEASUrement:IMMed:SOUrce {self._ch(ch)}")
        self.write(f"MEASUrement:IMMed:TYPe {kind}")
        value = self._query_float("MEASUrement:IMMed:VALue?")
        if value >= INVALID_MEASUREMENT:
            raise MeasurementError(f"{kind} on CH{ch}: no valid measurement (9.9E37)")
        return value

    def measure_units(self) -> str:
        return self.query("MEASUrement:IMMed:UNIts?").split()[-1].strip('"')

    # -- waveform -----------------------------------------------------------------------

    def waveform(self, ch: int):
        """Return (time_s, volts, preamble) for 2500 points of a channel."""
        src = self._ch(ch)
        self.write(f"DATa:SOUrce {src}")
        self.write("DATa:ENCdg RIBinary")
        self.write("DATa:WIDth 1")
        self.write("DATa:STARt 1")
        self.write("DATa:STOP 2500")
        pre = parse_preamble(self.query("WFMPre?"))
        old = self.resource.timeout
        self.resource.timeout = LONG_TIMEOUT_MS
        try:
            samples = self.resource.query_binary_values(
                "CURVe?", datatype="b", is_big_endian=True, container=np.array, expect_termination=True
            )
        finally:
            self.resource.timeout = old
        samples = np.asarray(samples, dtype=float)
        n = np.arange(len(samples))
        t = pre["XZERO"] + pre["XINCR"] * (n - pre["PT_OFF"])
        v = pre["YZERO"] + pre["YMULT"] * (samples - pre["YOFF"])
        self.last_waveform = (t, v, pre)
        return t, v, pre

    def save_csv(self, path) -> None:
        if self.last_waveform is None:
            raise WaveformError("no waveform read yet")
        t, v, _ = self.last_waveform
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["time_s", "volts"])
            for ti, vi in zip(t, v):
                w.writerow([f"{ti:.6e}", f"{vi:.6e}"])

    # -- screen -------------------------------------------------------------------------

    def screenshot(self, path) -> None:
        """Save the screen as PNG (HARDCopy over the rear USB Device port, BMP format)."""
        from PIL import Image

        self.write("HARDCopy:FORMat BMP")
        self.write("HARDCopy:PORT USB")
        old_timeout, old_term = self.resource.timeout, self.resource.read_termination
        self.resource.timeout = LONG_TIMEOUT_MS
        self.resource.read_termination = None
        try:
            self.write("HARDCopy STARt")
            data = bytearray(self.resource.read_raw())
            expected = struct.unpack("<I", data[2:6])[0] if len(data) >= 6 and data[:2] == b"BM" else None
            while expected and len(data) < expected:
                chunk = self.resource.read_raw()
                if not chunk:
                    break
                data += chunk
        finally:
            self.resource.timeout = old_timeout
            self.resource.read_termination = old_term
        if expected is None:
            raise RuntimeError("hard copy is not a BMP image")
        if len(data) < expected:
            raise RuntimeError(f"hard copy too short: {len(data)} of {expected} bytes")
        with Image.open(io.BytesIO(bytes(data[:expected]))) as img:
            img.save(path, format="PNG")


def _parse_events(raw: str):
    """Parse '<code>,"<msg>"[,<code>,"<msg>"...]' from ALLEv?."""
    out, i = [], 0
    while i < len(raw):
        comma = raw.find(",", i)
        if comma < 0:
            break
        code = int(raw[i:comma].strip())
        start = raw.find('"', comma)
        end = raw.find('"', start + 1)
        while end + 1 < len(raw) and raw[end + 1] == '"':  # doubled quote inside string
            end = raw.find('"', end + 2)
        out.append((code, raw[start + 1 : end]))
        i = end + 2  # skip closing quote and comma
    return out


_PREAMBLE_KEYS = [
    "BYT_NR", "BIT_NR", "ENCDG", "BN_FMT", "BYT_OR", "NR_PT", "WFID", "PT_FMT",
    "XINCR", "PT_OFF", "XZERO", "XUNIT", "YMULT", "YZERO", "YOFF", "YUNIT",
]  # fmt: skip
_NUMERIC = {"BYT_NR", "BIT_NR", "NR_PT", "PT_OFF", "XINCR", "XZERO", "YMULT", "YZERO", "YOFF"}


def parse_preamble(raw: str) -> dict:
    """Parse WFMPre? (HEADer off): 16 fields in the order of the manual."""
    fields = _split_segments(raw)
    if len(fields) != len(_PREAMBLE_KEYS):
        raise WaveformError(f"preamble has {len(fields)} fields, expected 16 (is the channel displayed?)")
    pre = {}
    for key, val in zip(_PREAMBLE_KEYS, fields):
        val = val.strip()
        if key in _NUMERIC:
            num = float(val)
            pre[key] = int(num) if key in ("BYT_NR", "BIT_NR", "NR_PT", "PT_OFF") else num
        else:
            pre[key] = val.strip('"')
    return pre

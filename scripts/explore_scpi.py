"""Command map for the TDS 1012C-EDU (build step 3): which documented queries it answers.

    python scripts/explore_scpi.py run [--resume local/logs/explore-<stamp>.jsonl]
    python scripts/explore_scpi.py report local/logs/explore-<stamp>.jsonl

Input: docs/manual-commands.json (scripts/extract_manual_commands.py).

`run` sends only the query form ("...?") of each documented header, one at a time, each followed by
*ESR? and ALLEv?, with 100 ms between commands and a 3 s timeout. After a timeout it clears the
USBTMC buffer (device clear) and checks that the status replies parse before it records the row.
It never sends a command without "?", CURVe?, WAVFrm?, HARDCopy?, or anything in the fixed blocklist.
The only writes are HEADer and VERBose, which it sets back in the end.

Before the run it saves SET? and CALibrate:STATUS? to local/backup/; after the run it reads both
again and compares. Rows go to a JSONL file in local/logs/ as they are read, so a stopped run can
resume. `report` writes docs/scpi_map.json and docs/COMMAND-MAP.md.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tek_scope import _parse_events, _split_segments, blocked_reason, segment_headers

MANUAL_JSON = ROOT / "docs" / "manual-commands.json"
BACKUP_DIR = ROOT / "local" / "backup"
LOG_DIR = ROOT / "local" / "logs"
PROBE_TIMEOUT_MS = 3_000
GAP_S = 0.1
# The full settings take about 5 s to arrive on this instrument; 3 s would leave a late reply behind.
SLOW_QUERIES = {"SET?": 30_000, "*LRN?": 30_000}
SLOW_WARNING_S = 2.5

# Excluded by the build prompt even though the library would let them through.
EXCLUDED = {
    "CURVe": "CURVe? is excluded by the build prompt (binary waveform transfer)",
    "WAVFrm": "WAVFrm? returns WFMPre? plus CURVe? (binary waveform transfer); excluded with CURVe?",
    "HARDCopy": "HARDCopy is excluded by the build prompt (HARDCopy? included)",
}

# One representative value for each constructed mnemonic (manual, "Constructed Mnemonics").
EXPANSIONS = [
    ("<wfm>", "CH1"), ("CH<x>", "CH1"), ("CH<y>", "CH1"), ("REF<x>", "REFA"), ("MEAS<x>", "MEAS1"),
    ("POSITION<x>", "POSITION1"), ("HPOS<x>", "HPOS1"), ("BATTERY<x>", "BATTERY1"), ("TP<x>", "TP1"), ("[1]", ""),
]  # fmt: skip


# ---------------------------------------------------------------------------
# Plan: what to send for each manual header
# ---------------------------------------------------------------------------


def query_for(header: str) -> str:
    q = header
    for token, value in EXPANSIONS:
        q = q.replace(token, value)
    if "<" in q or "[" in q:
        raise ValueError(f"unexpanded mnemonic in {header}")
    return q.rstrip("?") + "?"


def build_plan(commands: list[dict]) -> list[dict]:
    plan = []
    for c in commands:
        hdr = c["header"]
        bare = hdr.rstrip("?")
        entry = {"header": hdr, "query": None, "action": "", "reason": ""}
        if not c["query_form"]:
            entry.update(action="no_query_form", reason=c["query_basis"])
        elif bare in EXCLUDED:
            entry.update(action="excluded", reason=EXCLUDED[bare])
        else:
            q = query_for(hdr)
            why = blocked_reason(q)
            if why:
                entry.update(action="excluded", reason=f"blocklist (CLAUDE.md): {why}")
            else:
                entry.update(action="probe", query=q)
        plan.append(entry)
    return plan


# ---------------------------------------------------------------------------
# Matching SET? headers against the manual
# ---------------------------------------------------------------------------


def _node_regex(node: str) -> str:
    if node == "<wfm>":
        return r"(?:CH\d|MATH|REF[A-D])"
    suffix = ""
    if node.endswith(("<x>", "<y>")):
        node = node[:-3]
        suffix = r"[A-D]" if node.upper() == "REF" else r"\d+"
    elif node.endswith("[1]"):
        node, suffix = node[:-3], "1?"
    i = 0
    while i < len(node) and not node[i].islower():
        i += 1
    short, rest = node[:i].upper(), node[i:].upper()
    options = [re.escape(short + rest[:k]) for k in range(len(rest), -1, -1)]
    return "(?:" + "|".join(options) + ")" + suffix


_PATTERNS: dict[str, re.Pattern] = {}


def _pattern(header: str) -> re.Pattern:
    if header not in _PATTERNS:
        nodes = header.rstrip("?").split(":")
        _PATTERNS[header] = re.compile("^" + ":".join(_node_regex(n) for n in nodes) + "$")
    return _PATTERNS[header]


def match_manual(set_header: str, commands: list[dict]) -> str | None:
    """Return the manual header that a full SET? header (e.g. CH2:SCALE) is a spelling of."""
    h = set_header.upper().lstrip(":").rstrip("?")
    for c in commands:
        if _pattern(c["header"]).match(h):
            return c["header"]
    return None


# ---------------------------------------------------------------------------
# Status replies
# ---------------------------------------------------------------------------

_STATUS_PREFIX = re.compile(r"^:?(?:ALLEV|ALLE|\*ESR)\s+", re.IGNORECASE)


def parse_esr(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = _STATUS_PREFIX.sub("", raw.strip())
    return int(raw) if re.fullmatch(r"\d+", raw) else None


def parse_allev(raw: str | None) -> list[tuple[int, str]] | None:
    if raw is None:
        return None
    raw = _STATUS_PREFIX.sub("", raw.strip())
    if not re.match(r'^-?\d+,"', raw):
        return None
    try:
        return _parse_events(raw)
    except ValueError:
        return None


QUERY_ERRORS = {404, 410, 420, 430, 440}


def event_class(code: int) -> int:
    """Four-digit codes such as 2244 are subcodes of a three-digit class (2244 -> 224)."""
    return code // 10 if code >= 1000 else code


def error_codes(codes: list[int]) -> list[int]:
    """Command (1xx), execution (2xx) and device (3xx) errors, power fail and query errors."""
    return [c for c in codes if 100 <= event_class(c) <= 399 or event_class(c) in QUERY_ERRORS]


def is_accepted(response: str | None, codes: list[int]) -> bool:
    return bool(response) and not error_codes(codes)


def should_stop(history: list[list[int]], exempt: set[int] | None = None) -> bool:
    """Stop on a repeated execution or device error (CLAUDE.md, build prompt 3).

    - the same 2xx/3xx code in three probes in a row;
    - a 3xx (device error) in two probes in a row;
    - 404 (power fail) at any time.

    `exempt` lists codes whose repetition was already explained by the manual (for example 2244 when
    DATa:SOUrce names a waveform that is not displayed). They do not count toward a stop.
    """
    exempt = exempt or set()
    history = [[c for c in h if c not in exempt] for h in history]
    if history and 404 in history[-1]:
        return True
    if len(history) >= 2 and all(any(300 <= event_class(c) <= 399 for c in h) for h in history[-2:]):
        return True
    if len(history) >= 3:
        common = set.intersection(*({c for c in h if 200 <= event_class(c) <= 399} for h in history[-3:]))
        if common:
            return True
    return False


def sanitize(text: str | None, serial: str) -> str | None:
    if text is None or not serial:
        return text
    return text.replace(serial, "<SERIAL>")


# ---------------------------------------------------------------------------
# One probe
# ---------------------------------------------------------------------------


def _default_timeout_errors() -> tuple[type[BaseException], ...]:
    try:
        from pyvisa.errors import VisaIOError

        return (VisaIOError,)
    except ImportError:  # pragma: no cover
        return (TimeoutError,)


def _read_status(scope, timeout_errors):
    esr_raw = allev_raw = None
    scope.resource.timeout = PROBE_TIMEOUT_MS
    try:
        time.sleep(GAP_S)
        esr_raw = scope.query("*ESR?")
        time.sleep(GAP_S)
        allev_raw = scope.query("ALLEv?")
    except timeout_errors:
        pass
    return esr_raw, allev_raw


def probe_one(scope, query: str, serial: str, timeout_errors=None, reopen=None) -> dict:
    """Send one query, then *ESR? and ALLEv?. Never raises on a VISA error.

    After a timeout the VISA session is closed and opened again (reopen). On this instrument the USBTMC
    device clear (viClear) and the status-byte read (viReadSTB) fail after a run of unanswered queries;
    a new session reads the status cleanly.
    """
    timeout_errors = timeout_errors or _default_timeout_errors()
    scope.resource.timeout = SLOW_QUERIES.get(query, PROBE_TIMEOUT_MS)
    started = time.monotonic()
    response, timed_out = None, False
    try:
        response = scope.query(query)
    except timeout_errors:
        timed_out = True
    elapsed = round(time.monotonic() - started, 3)
    if timed_out:
        reopen()

    esr_raw, allev_raw = _read_status(scope, timeout_errors)
    esr, events = parse_esr(esr_raw), parse_allev(allev_raw)
    if esr is None or events is None:  # out of step: new session, read the status again
        reopen()
        esr_raw, allev_raw = _read_status(scope, timeout_errors)
        esr, events = parse_esr(esr_raw), parse_allev(allev_raw)

    codes = [c for c, _ in events] if events is not None else []
    if esr is None or events is None:
        status = "status_unreadable"
    elif timed_out or response is None:
        status = "no_response"
    elif not is_accepted(response, codes):
        status = "answered_with_error"
    elif elapsed > PROBE_TIMEOUT_MS / 1000:
        status = "accepted_slow"  # answered, but only with the longer timeout (SLOW_QUERIES)
    else:
        status = "accepted"
    return {
        "query": query,
        "status": status,
        "response": sanitize(response, serial),
        "timed_out": timed_out,
        "seconds": elapsed,
        "esr": esr,
        "event_codes": codes,
        "events": sanitize(allev_raw, serial),
        "esr_raw": esr_raw if esr is None else None,
    }


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def _cell(text: str | None, limit: int = 70) -> str:
    if text is None:
        return ""
    t = " ".join(str(text).split())
    if len(t) > limit:
        t = t[: limit - 1] + "…"
    return t.replace("|", "\\|")


def set_segments(set_text: str) -> list[tuple[str, str]]:
    """(full header, value) for every command in a SET? reply."""
    segments = _split_segments(set_text)
    headers = segment_headers(set_text)
    out = []
    for seg, hdr in zip(segments, headers):
        parts = seg.split(None, 1)
        out.append((hdr, parts[1] if len(parts) > 1 else ""))
    return out


def build_outputs(commands: list[dict], rows: list[dict], set_text: str, meta: dict) -> tuple[dict, str]:
    plan = {p["header"]: p for p in build_plan(commands)}
    by_query = {r["query"]: r for r in rows}
    out_rows = []
    for c in commands:
        p = plan[c["header"]]
        r = by_query.get(p["query"]) if p["query"] else None
        if p["action"] != "probe":
            status = p["action"]
        elif r is None:
            status = "not_run"
        else:
            status = r["status"]
        out_rows.append({
            "header": c["header"],
            "page": c.get("page", ""),
            "group": c.get("group", ""),
            "documented_for_tds1000c_edu": c["applies_to_tds1000c_edu"],
            "query_sent": p["query"],
            "status": status,
            "reason_not_sent": p["reason"] or None,
            "responded": bool(r and r["response"] is not None and not r.get("timed_out", False)),
            "response": r["response"] if r else None,
            "event_code": r["event_codes"] if r else None,
            "esr": r["esr"] if r else None,
            "seconds": r.get("seconds") if r else None,
        })  # fmt: skip

    ok = ("accepted", "accepted_slow")
    table_a = [x for x in out_rows if x["status"] in ok and x["documented_for_tds1000c_edu"]]
    table_b = [x for x in out_rows if x["status"] in ok and not x["documented_for_tds1000c_edu"]]
    not_accepted_here = [
        x for x in out_rows if x["documented_for_tds1000c_edu"] and x["query_sent"] and x["status"] not in ok
    ]
    set_extra, seen = [], set()
    for hdr, value in set_segments(set_text):
        if hdr not in seen and match_manual(hdr, commands) is None:
            set_extra.append({"header": hdr, "value": value})
        seen.add(hdr)

    from collections import Counter

    counts = {
        "manual_headers": len(out_rows),
        "classified": sum(1 for x in out_rows if x["status"] != "not_run"),
        "by_status": dict(Counter(x["status"] for x in out_rows)),
        "table_a": len(table_a),
        "table_b": len(table_b),
        "table_c": len(set_extra),
        "documented_here_not_accepted": len(not_accepted_here),
    }
    data = {"meta": meta, "counts": counts, "commands": out_rows, "set_headers_not_in_manual": set_extra}
    basis = {c["header"]: c["applies_basis"] for c in commands}

    md = [
        "# Command map: Tektronix TDS 1012C-EDU",
        "",
        f"Instrument: TDS 1012C-EDU, firmware {meta.get('firmware', '?')}, USB (USBTMC). Run: {meta.get('date', '?')}.",
        (
            "Manual: *Digital Oscilloscope Series Programmer Manual*, Tektronix 077044403. Raw data: "
            "[scpi_map.json](scpi_map.json); manual headers: [manual-commands.json](manual-commands.json)."
        ),
        "",
        "## How the map was made",
        "",
        (
            f"- {counts['manual_headers']} headers from the manual: every index entry in Command Descriptions, the "
            "`WFMPre:<wfm>:*` headings the index leaves out, and the six headers of Table 2-36."
        ),
        (
            "- For each header with a query form, only the query was sent (`...?`), followed by `*ESR?` and "
            "`ALLEv?`. 100 ms between commands, 3 s timeout, device clear after a timeout. Constructed mnemonics "
            "were sent with one value: `CH1`, `REFA`, `MEAS1`, `POSITION1`, `HPOS1`, `TP1`, `BATTERY1`; `<wfm>` as "
            "`CH1`."
        ),
        f"- Response headers on: `HEADer {meta.get('header_mode', 'ON')}`, `VERBose {meta.get('verbose_mode', 'ON')}`.",
        (
            "- **Accepted** means: a reply within 3 s and no error event (codes 100-399, 404, 410, 420, 430, 440; "
            "four-digit codes such as 2244 count by their class, 224). Warnings (5xx) do not count as errors."
        ),
        (
            "- `SET?` and `*LRN?` take about 5 s to arrive, so they were sent with a 30 s timeout. They are listed "
            "as accepted with the time marked (`accepted_slow`)."
        ),
        (
            "- After a timeout the VISA session was closed and opened again before reading the status. On this "
            "instrument the USBTMC device clear stopped working after a long run of unanswered queries."
        ),
        (
            "- Not sent: commands without a query form, `CURVe?`, `WAVFrm?`, `HARDCopy?`, and everything in the "
            "blocklist (`*CAL?`, `*TST?`, `SAVe:`, `RECAll:`, `*SAV`, `*RCL`, ...)."
        ),
        "- The serial number is replaced with `<SERIAL>` in every recorded reply.",
        "",
        "| Result | Count |",
        "|---|---|",
    ]
    for k, v in sorted(counts["by_status"].items(), key=lambda kv: -kv[1]):
        md.append(f"| {k} | {v} |")
    md += [
        "",
        f"## (a) Documented for this model and accepted ({len(table_a)})",
        "",
        "| Header | Query sent | Reply |",
        "|---|---|---|",
    ]
    def _reply(x: dict) -> str:
        slow = f" *({x['seconds']} s)*" if x["status"] == "accepted_slow" else ""
        return _cell(x["response"]) + slow

    md += [f"| `{x['header']}` | `{x['query_sent']}` | {_reply(x)} |" for x in table_a]
    md += [
        "",
        f"## (b) Documented for other series only, and accepted here ({len(table_b)})",
        "",
        "| Header | Query sent | Reply | The manual says |",
        "|---|---|---|---|",
    ]
    md += [
        f"| `{x['header']}` | `{x['query_sent']}` | {_reply(x)} | {_cell(basis[x['header']], 90)} |"
        for x in table_b
    ]
    md += [
        "",
        f"## (c) In `SET?` but not in the manual ({len(set_extra)})",
        "",
        (
            "Headers in the `SET?` reply (`HEADer ON`, `VERBose ON`) that do not match any manual header, "
            "allowing for short forms and constructed mnemonics."
        ),
        "",
        "| Header in `SET?` | Value |",
        "|---|---|",
    ]
    md += [f"| `{x['header']}` | {_cell(x['value'])} |" for x in set_extra]
    md += [
        "",
        f"## Documented for this model but not accepted ({len(not_accepted_here)})",
        "",
        "| Header | Query sent | Result | Events |",
        "|---|---|---|---|",
    ]
    md += [
        f"| `{x['header']}` | `{x['query_sent']}` | {x['status']} | {', '.join(map(str, x['event_code'] or []))} |"
        for x in not_accepted_here
    ]
    seen_codes = sorted({c for x in out_rows for c in (x["event_code"] or []) if c not in (0, 1)})
    md += ["", "Event codes seen in this run (manual, Tables 3-5 to 3-8):", ""]
    md += [f"- `{c}`: {EVENT_TEXT.get(c, 'see the manual')}" for c in seen_codes]
    for note in meta.get("notes", []):
        md += ["", note]
    return data, "\n".join(md) + "\n"


EVENT_TEXT = {
    100: "Command error (Table 2-36 says the compatibility-only WFMPre headers give 100 and 420)",
    113: "Undefined header (the instrument does not know the command)",
    420: "Query UNTERMINATED (a reply was read for but none was produced)",
    2244: "Waveform requested is not activated",
}


# ---------------------------------------------------------------------------
# Hardware run
# ---------------------------------------------------------------------------


def _stamp() -> str:
    return _dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _value(reply: str) -> str:
    return reply.split()[-1] if reply else reply


class _Session:
    """One VISA resource manager; sessions to the instrument can be closed and opened again."""

    def __init__(self):
        import pyvisa

        from tek_scope import find_resource

        self.rm = pyvisa.ResourceManager()
        self.name = find_resource(self.rm)

    def open(self):
        from tek_scope import DEFAULT_TIMEOUT_MS

        r = self.rm.open_resource(self.name)
        r.timeout = DEFAULT_TIMEOUT_MS
        r.read_termination = "\n"
        r.write_termination = "\n"
        return r

    def reopen(self, scope) -> None:
        try:
            scope.resource.close()
        except Exception as exc:  # noqa: BLE001 - the old session may already be broken
            print("  (old session close failed:", exc, ")")
        time.sleep(0.2)
        scope.resource = self.open()


def _base_stamp(jsonl: Path) -> str | None:
    m = re.fullmatch(r"explore-(\d{8}-\d{6})\.jsonl", jsonl.name)
    return m.group(1) if m else None


def run(resume: Path | None, exempt: set[int] | None = None) -> int:
    from tek_scope import DEFAULT_TIMEOUT_MS, TekScope

    manual = json.loads(MANUAL_JSON.read_text(encoding="utf-8"))
    plan = [p for p in build_plan(manual["commands"]) if p["action"] == "probe"]
    stamp = _stamp()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    jsonl = resume or LOG_DIR / f"explore-{stamp}.jsonl"
    base = _base_stamp(jsonl) or stamp  # the first backup of the run is the reference
    done = set()
    if resume and resume.exists():
        done = {json.loads(line)["query"] for line in resume.read_text(encoding="utf-8").splitlines() if line.strip()}
    todo = [p for p in plan if p["query"] not in done]
    print(f"{len(plan)} queries in the plan, {len(done)} already done, {len(todo)} to send; log {jsonl.name}")

    session = _Session()
    scope = TekScope(resource=session.open())
    scope.connect()
    stopped = None
    try:
        serial = scope.idn().split(",")[2].strip()
        header0 = _value(scope.query("HEADer?"))
        verbose0 = _value(scope.query("VERBose?"))
        scope.resource.timeout = SLOW_QUERIES["SET?"]
        set_now = scope.state()
        scope.resource.timeout = DEFAULT_TIMEOUT_MS
        cal_now = scope.query("CALibrate:STATUS?")
        (BACKUP_DIR / f"SET-antes-mapa-{stamp}.txt").write_text(set_now, encoding="utf-8")
        (BACKUP_DIR / f"CAL-antes-mapa-{stamp}.txt").write_text(cal_now, encoding="utf-8")
        set_ref = (BACKUP_DIR / f"SET-antes-mapa-{base}.txt").read_text(encoding="utf-8")
        cal_ref = (BACKUP_DIR / f"CAL-antes-mapa-{base}.txt").read_text(encoding="utf-8")
        print(f"backup saved: HEADer {header0}, VERBose {verbose0}, CALibrate:STATUS? {cal_now}")
        print(f"reference {base}: SET? same now: {set_now == set_ref}; CALibrate:STATUS? same: {cal_now == cal_ref}")
        # drain old status before the first probe (reading clears them; no *CLS, which is a write)
        print("old status:", scope.query("*ESR?"), scope.query("ALLEv?"))

        history: list[list[int]] = []
        reopens = 0

        def reopen():
            nonlocal reopens
            reopens += 1
            session.reopen(scope)

        try:
            scope.write("HEADer ON")
            time.sleep(GAP_S)
            scope.write("VERBose ON")
            time.sleep(GAP_S)
            scope.resource.timeout = SLOW_QUERIES["SET?"]
            set_verbose = scope.state()
            (BACKUP_DIR / f"SET-verbose-mapa-{stamp}.txt").write_text(set_verbose, encoding="utf-8")
            with open(jsonl, "a", encoding="utf-8") as fh:
                for n, p in enumerate(todo, 1):
                    time.sleep(GAP_S)
                    row = probe_one(scope, p["query"], serial, reopen=reopen)
                    row["header"] = p["header"]
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fh.flush()
                    slow = " SLOW" if row["status"].startswith("accepted") and row["seconds"] > SLOW_WARNING_S else ""
                    print(
                        f"[{n}/{len(todo)}] {p['query']}: {row['status']} {row['event_codes']} {row['seconds']}s{slow}",
                        flush=True,
                    )
                    if row["status"] == "status_unreadable":
                        stopped = f"status replies unreadable after {p['query']}"
                        break
                    history.append(row["event_codes"])
                    if should_stop(history, exempt):
                        stopped = f"repeated execution/device error at {p['query']}: {history[-3:]}"
                        break
        finally:
            print(f"session reopened {reopens} times; restoring in a new session")
            session.reopen(scope)
            scope.write(f"HEADer {header0}")
            time.sleep(GAP_S)
            scope.write(f"VERBose {verbose0}")
            time.sleep(GAP_S)
            scope.resource.timeout = SLOW_QUERIES["SET?"]
            set_after = scope.state()
            scope.resource.timeout = DEFAULT_TIMEOUT_MS
            cal_after = scope.query("CALibrate:STATUS?")
            (BACKUP_DIR / f"SET-depois-mapa-{stamp}.txt").write_text(set_after, encoding="utf-8")
            (BACKUP_DIR / f"CAL-depois-mapa-{stamp}.txt").write_text(cal_after, encoding="utf-8")
            same_set, same_cal = set_after == set_ref, cal_after == cal_ref
            print(f"SET? same as backup {base}: {same_set}; CALibrate:STATUS? same: {same_cal} ({cal_after})")
            summary = {
                "stamp": stamp, "reference": base, "jsonl": jsonl.name, "stopped": stopped, "reopens": reopens,
                "set_same": same_set, "cal_same": same_cal, "cal_before": cal_ref, "cal_after": cal_after,
                "header0": header0, "verbose0": verbose0, "firmware": scope.idn().split(",")[-1].strip(),
            }  # fmt: skip
            (LOG_DIR / f"explore-{stamp}-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    finally:
        scope.close()
        session.rm.close()
    if stopped:
        print("STOPPED:", stopped)
        return 3
    return 0 if same_set and same_cal else 4


def report(jsonl: Path, set_file: Path, meta: dict) -> int:
    manual = json.loads(MANUAL_JSON.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    data, md = build_outputs(manual["commands"], rows, set_file.read_text(encoding="utf-8"), meta)
    (ROOT / "docs" / "scpi_map.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "docs" / "COMMAND-MAP.md").write_text(md, encoding="utf-8")
    print(json.dumps(data["counts"], indent=1))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--resume", type=Path)
    r.add_argument(
        "--exempt",
        type=int,
        action="append",
        default=[],
        help="event code whose repetition the manual explains; it does not trigger the stop rule",
    )
    p = sub.add_parser("report")
    p.add_argument("jsonl", type=Path)
    p.add_argument("set_file", type=Path, help="SET? saved with HEADer ON and VERBose ON")
    p.add_argument("--firmware", default="v25.11")
    p.add_argument("--date", default=_dt.datetime.now().astimezone().date().isoformat())
    p.add_argument("--note", action="append", default=[], help="paragraph added at the end of COMMAND-MAP.md")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run(a.resume, set(a.exempt))
    meta = {"firmware": a.firmware, "date": a.date, "header_mode": "ON", "verbose_mode": "ON", "notes": a.note}
    return report(a.jsonl, a.set_file, meta)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

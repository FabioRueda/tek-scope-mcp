"""Tests for scripts/explore_scpi.py (build step 3). No hardware needed."""

import json
import sys
from pathlib import Path

import pytest

from tek_scope import blocked_reason, segment_headers

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import explore_scpi as ex

MANUAL = json.loads((ROOT / "docs" / "manual-commands.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plans():
    return {p["header"]: p for p in ex.build_plan(MANUAL["commands"])}


def test_every_manual_header_gets_a_plan(plans):
    assert len(plans) == len(MANUAL["commands"]) == MANUAL["counts"]["total"]
    assert {p["action"] for p in plans.values()} <= {"probe", "no_query_form", "excluded"}


def test_every_probe_is_a_plain_query_that_passes_the_blocklist(plans):
    probes = [p for p in plans.values() if p["action"] == "probe"]
    assert len(probes) > 250
    for p in probes:
        q = p["query"]
        assert q.endswith("?"), q
        assert ";" not in q and " " not in q, q
        assert blocked_reason(q) is None, q
        first = segment_headers(q)[0].rstrip("?")
        assert first not in ("CURVE", "CURV", "WAVFRM", "WAVF", "HARDCOPY", "HARDC"), q


@pytest.mark.parametrize(
    "header",
    ["*SAV", "*RCL", "*CAL?", "*TST?", "SAVe:SETUp", "SAVe:IMAge:FILEFormat", "RECAll:SETUp", "CURVe", "WAVFrm?",
     "HARDCopy", "FACtory", "*RST", "CALibrate:INTERNAL"],
)  # fmt: skip
def test_dangerous_or_excluded_headers_are_never_probed(plans, header):
    assert plans[header]["action"] != "probe"
    assert plans[header]["query"] is None


@pytest.mark.parametrize(
    "header, action",
    [("*CAL?", "excluded"), ("*TST?", "excluded"), ("CURVe", "excluded"), ("WAVFrm?", "excluded"),
     ("HARDCopy", "excluded"), ("SAVe:SETUp", "no_query_form"), ("*CLS", "no_query_form"),
     ("AUTOSet", "no_query_form"), ("*RST", "no_query_form")],
)  # fmt: skip
def test_actions(plans, header, action):
    assert plans[header]["action"] == action


@pytest.mark.parametrize(
    "header, query",
    [("CH<x>:SCAle", "CH1:SCAle?"), ("WFMPre:<wfm>:XINcr", "WFMPre:CH1:XINcr?"),
     ("MEASUrement:IMMed:SOUrce[1]", "MEASUrement:IMMed:SOUrce?"), ("SELect:<wfm>", "SELect:CH1?"),
     ("CURSor:VBArs:HPOS<x>?", "CURSor:VBArs:HPOS1?"), ("MEASUrement:MEAS<x>:VALue?", "MEASUrement:MEAS1:VALue?"),
     ("HARDCopy:FORMat", "HARDCopy:FORMat?"), ("CALibrate:STATUS?", "CALibrate:STATUS?"), ("*ESE", "*ESE?"),
     ("TRENDPLOT:TP<x>:AVG?", "TRENDPLOT:TP1:AVG?"), ("POWer:BATTERY<x>:STATUS?", "POWer:BATTERY1:STATUS?")],
)  # fmt: skip
def test_query_strings(plans, header, query):
    assert plans[header]["action"] == "probe"
    assert plans[header]["query"] == query


@pytest.mark.parametrize(
    "set_header, manual",
    [("ACQUIRE:STOPAFTER", "ACQuire:STOPAfter"), ("CH2:SCALE", "CH<x>:SCAle"), ("ACQ:MOD", "ACQuire:MODe"),
     ("MEASUREMENT:MEAS3:TYPE", "MEASUrement:MEAS<x>:TYPe"), ("MEASUREMENT:IMMED:SOURCE1", "MEASUrement:IMMed:SOUrce[1]"),
     ("MEASUREMENT:IMMED:SOURCE", "MEASUrement:IMMed:SOUrce[1]"), ("CURSOR:HBARS:POSITION2", "CURSor:HBArs:POSITION<x>"),
     ("SELECT:REFB", "SELect:<wfm>"), ("HARDCOPY:BUTTON", "HARDCopy:BUTTON"), ("*ESE", "*ESE")],
)  # fmt: skip
def test_match_manual(set_header, manual):
    assert ex.match_manual(set_header, MANUAL["commands"]) == manual


@pytest.mark.parametrize("set_header", ["FOO:BAR", "ACQUIREX:MODE", "CH1:SCALEX", "ACQUIRE:MODE:X", "CH3X:SCALE"])
def test_match_manual_rejects_unknown(set_header):
    assert ex.match_manual(set_header, MANUAL["commands"]) is None


def test_parse_status_with_and_without_header():
    assert ex.parse_allev(':ALLEV 113,"Undefined header; Command not found; FOO?"') == [
        (113, "Undefined header; Command not found; FOO?")
    ]
    assert ex.parse_allev('0,"No events to report - queue empty"') == [(0, "No events to report - queue empty")]
    assert ex.parse_allev("garbage") is None
    assert ex.parse_esr("32") == 32
    assert ex.parse_esr("*ESR 0") == 0
    assert ex.parse_esr("x") is None


@pytest.mark.parametrize(
    "codes, is_error", [([0], False), ([1], False), ([113], True), ([221], True), ([310], True), ([420], True),
                        ([402], False), ([540], False), ([0, 2244], True)]
)  # fmt: skip
def test_error_codes(codes, is_error):
    assert bool(ex.error_codes(codes)) is is_error


def test_accepted_needs_a_reply_and_no_error():
    assert ex.is_accepted("1", [0])
    assert ex.is_accepted("1", [540])  # warning only
    assert not ex.is_accepted(None, [0])
    assert not ex.is_accepted("", [420])
    assert not ex.is_accepted("1", [113])


def test_stop_rule():
    assert not ex.should_stop([[113], [113], [113], [113]])  # command errors are expected
    assert not ex.should_stop([[221], [0], [221]])
    assert ex.should_stop([[221], [221], [221]])
    assert not ex.should_stop([[221], [222], [221]])
    assert ex.should_stop([[0], [310], [350]])  # two device errors in a row
    assert ex.should_stop([[404]])  # power fail


def test_stop_rule_can_exempt_an_explained_code():
    explained = [[2244, 420], [2244, 420], [2244, 420]]
    assert ex.should_stop(explained)
    assert not ex.should_stop(explained, exempt={2244})
    assert ex.should_stop([[2241], [2241], [2241]], exempt={2244})


def test_sanitize_replaces_serial_everywhere():
    assert ex.sanitize("TEKTRONIX,TDS 1012C-EDU,C012345,CF:91.1CT", "C012345") == "TEKTRONIX,TDS 1012C-EDU,<SERIAL>,CF:91.1CT"
    assert ex.sanitize(None, "C012345") is None
    assert ex.sanitize("abc", "") == "abc"


class TimeoutErr(Exception):
    pass


class FakeResource:
    def __init__(self, answers):
        self.answers = answers
        self.timeout = 10000
        self.sent = []
        self.timeouts = []

    def query(self, cmd):
        self.sent.append(cmd)
        self.timeouts.append(self.timeout)
        value = self.answers[cmd]
        if isinstance(value, list):
            value = value.pop(0)
        if value is TimeoutErr:
            raise TimeoutErr("timeout")
        return value

    def clear(self):
        raise AssertionError("device clear must not be used on this instrument")


class FakeScope:
    """A scope whose reopen() swaps in the next fake session, like closing and reopening VISA."""

    def __init__(self, *sessions):
        self.sessions = list(sessions)
        self.resource = self.sessions.pop(0)
        self.reopened = 0

    def query(self, cmd):
        assert blocked_reason(cmd) is None
        return self.resource.query(cmd)

    def reopen(self):
        self.reopened += 1
        self.resource = self.sessions.pop(0)


NO_EVENTS = '0,"No events to report - queue empty"'


def test_probe_one_answered(monkeypatch):
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)
    scope = FakeScope(FakeResource({"CH1:SCAle?": "1.0E0", "*ESR?": "0", "ALLEv?": NO_EVENTS}))
    row = ex.probe_one(scope, "CH1:SCAle?", "SER", timeout_errors=(TimeoutErr,), reopen=scope.reopen)
    assert row["status"] == "accepted"
    assert row["response"] == "1.0E0"
    assert row["event_codes"] == [0]
    assert scope.reopened == 0
    assert scope.resource.timeouts[0] == ex.PROBE_TIMEOUT_MS


def test_probe_one_timeout_reopens_and_reads_status_in_the_new_session(monkeypatch):
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)
    old = FakeResource({"FFT?": TimeoutErr})
    new = FakeResource({"*ESR?": "32", "ALLEv?": ':ALLEV 113,"Undefined header; unrecognized command - FFT?"'})
    scope = FakeScope(old, new)
    row = ex.probe_one(scope, "FFT?", "SER", timeout_errors=(TimeoutErr,), reopen=scope.reopen)
    assert row["status"] == "no_response"
    assert row["response"] is None
    assert row["esr"] == 32
    assert row["event_codes"] == [113]
    assert scope.reopened == 1
    assert old.sent == ["FFT?"]
    assert new.sent == ["*ESR?", "ALLEv?"]


def test_probe_one_reopens_again_after_a_bad_status_reply(monkeypatch):
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)
    first = FakeResource({"X?": TimeoutErr})
    second = FakeResource({"*ESR?": "late answer", "ALLEv?": "stale"})
    third = FakeResource({"*ESR?": "0", "ALLEv?": NO_EVENTS})
    scope = FakeScope(first, second, third)
    row = ex.probe_one(scope, "X?", "SER", timeout_errors=(TimeoutErr,), reopen=scope.reopen)
    assert row["esr"] == 0
    assert row["event_codes"] == [0]
    assert scope.reopened == 2


def test_probe_one_marks_unreadable_status(monkeypatch):
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)
    scope = FakeScope(FakeResource({"X?": "1", "*ESR?": "?", "ALLEv?": "?"}), FakeResource({"*ESR?": "?", "ALLEv?": "?"}))
    row = ex.probe_one(scope, "X?", "SER", timeout_errors=(TimeoutErr,), reopen=scope.reopen)
    assert row["status"] == "status_unreadable"


def test_slow_queries_get_the_long_timeout_and_are_marked(monkeypatch):
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)
    clock = iter([0.0, 4.9])
    monkeypatch.setattr(ex.time, "monotonic", lambda: next(clock))
    scope = FakeScope(FakeResource({"SET?": ":ACQUIRE:MODE SAMPLE", "*ESR?": "0", "ALLEv?": NO_EVENTS}))
    row = ex.probe_one(scope, "SET?", "SER", timeout_errors=(TimeoutErr,), reopen=scope.reopen)
    assert scope.resource.timeouts[0] == ex.SLOW_QUERIES["SET?"]
    assert row["status"] == "accepted_slow"
    assert row["seconds"] == 4.9


def test_build_outputs_tables():
    commands = [
        {"header": "CH<x>:SCAle", "applies_to_tds1000c_edu": True, "applies_basis": "x", "group": "Vertical",
         "query_form": True, "query_basis": "syntax", "page": "2-56", "source": "index"},
        {"header": "ZOOM:STATE", "applies_to_tds1000c_edu": False, "applies_basis": "Conditions: TBS1000B/EDU models only.",
         "group": "Zoom", "query_form": True, "query_basis": "syntax", "page": "2-224", "source": "index"},
        {"header": "FFT?", "applies_to_tds1000c_edu": False, "applies_basis": "y", "group": "FFT",
         "query_form": True, "query_basis": "q", "page": "2-94", "source": "index"},
    ]  # fmt: skip
    rows = [
        {"query": "CH1:SCAle?", "status": "accepted", "response": ":CH1:SCALE 1.0E0", "esr": 0, "event_codes": [0], "events": ""},
        {"query": "ZOOM:STATE?", "status": "accepted", "response": "0", "esr": 0, "event_codes": [0], "events": ""},
        {"query": "FFT?", "status": "no_response", "response": None, "esr": 32, "event_codes": [113], "events": ""},
    ]  # fmt: skip
    set_text = ":CH1:SCALE 1.0E0;:CH2:SCALE 2.0E0;:HARDCOPY:SECRET 1;:ZOOM:STATE 0"
    data, md = ex.build_outputs(commands, rows, set_text, meta={"firmware": "v25.11"})
    assert data["counts"]["table_a"] == 1
    assert data["counts"]["table_b"] == 1
    assert data["counts"]["table_c"] == 1
    assert data["set_headers_not_in_manual"][0]["header"] == "HARDCOPY:SECRET"
    assert "| `ZOOM:STATE?` |" in md
    assert "HARDCOPY:SECRET" in md
    by_header = {c["header"]: c for c in data["commands"]}
    assert by_header["FFT?"]["responded"] is False
    assert by_header["CH<x>:SCAle"]["event_code"] == [0]

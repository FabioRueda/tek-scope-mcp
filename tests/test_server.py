"""Unit tests for the MCP server with a fake VISA resource (no hardware needed)."""

import asyncio
import io
import json

import pytest
from mcp import types
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image as PILImage
from test_tek_scope import FakeResource

import server
from tek_scope import TekScope

READ_TOOLS = {
    "scope_idn",
    "scope_state",
    "scope_errors",
    "scope_query",
    "scope_measure",
    "scope_waveform",
    "scope_screenshot",
}
WRITE_TOOLS = {
    "scope_set_channel",
    "scope_set_timebase",
    "scope_set_trigger",
    "scope_set_acquisition",
    "scope_run",
    "scope_stop",
    "scope_single",
    "scope_autoset",
    "scope_write",
}


class TimedResource(FakeResource):
    """FakeResource that remembers the timeout in force at each query."""

    def __init__(self, answers=None):
        super().__init__(answers)
        self.timeouts = {}
        self.fail_on = set()

    def query(self, cmd):
        self.timeouts[cmd] = self.timeout
        if cmd in self.fail_on:
            raise TimeoutError(f"timeout on {cmd}")
        return super().query(cmd)


class Rig:
    """A factory that builds a TekScope on one fake resource and counts open/close."""

    def __init__(self, tmp_path, answers=None):
        self.tmp = tmp_path
        self.resource = TimedResource(answers)
        self.opened = 0
        self.closed = 0

    def __call__(self):
        scope = TekScope(resource=self.resource, log_path=self.tmp / "w.log", lock_path=self.tmp / "s.lock")
        rig = self
        real_connect, real_close = scope.connect, scope.close

        def connect():
            rig.opened += 1
            return real_connect()

        def close():
            rig.closed += 1
            real_close()

        scope.connect, scope.close = connect, close
        return scope

    @property
    def written(self):
        return self.resource.written


def make(tmp_path, answers=None, readonly=False):
    rig = Rig(tmp_path, answers)
    srv = server.create_server(scope_factory=rig, readonly=readonly, data_dir=tmp_path)
    return srv, rig


class Failed:
    """What the protocol layer turns a ToolError into: an error result carrying the message."""

    is_error = True

    def __init__(self, message):
        self.content = [types.TextContent(type="text", text=message)]


def call(srv, name, **args):
    try:
        return asyncio.run(srv.call_tool(name, args))
    except ToolError as exc:
        return Failed(str(exc))


def text(result):
    return "".join(c.text for c in result.content if hasattr(c, "text"))


def data(result):
    return json.loads(text(result))


# -- tool list --------------------------------------------------------------


def test_all_tools_registered(tmp_path):
    srv, _ = make(tmp_path)
    names = {t.name for t in asyncio.run(srv.list_tools())}
    assert names == READ_TOOLS | WRITE_TOOLS


def test_readonly_removes_every_write_tool(tmp_path):
    srv, _ = make(tmp_path, readonly=True)
    names = {t.name for t in asyncio.run(srv.list_tools())}
    assert names == READ_TOOLS


def test_readonly_env_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("TEK_SCOPE_READONLY", "1")
    srv = server.create_server(scope_factory=Rig(tmp_path), data_dir=tmp_path)
    assert {t.name for t in asyncio.run(srv.list_tools())} == READ_TOOLS


def test_no_allow_dangerous_anywhere(tmp_path):
    srv, _ = make(tmp_path)
    for tool in asyncio.run(srv.list_tools()):
        assert "allow_dangerous" not in json.dumps(tool.input_schema)


def test_write_tools_require_confirm_parameter(tmp_path):
    srv, _ = make(tmp_path)
    for tool in asyncio.run(srv.list_tools()):
        if tool.name in WRITE_TOOLS:
            assert "confirm" in tool.input_schema["properties"], tool.name


# -- read tools --------------------------------------------------------------


def test_idn_opens_and_closes_the_connection(tmp_path):
    srv, rig = make(tmp_path, {"*IDN?": "TEKTRONIX,TDS 1012C-EDU,X,CF:91.1CT FV:v25.11"})
    result = call(srv, "scope_idn")
    assert not result.is_error
    assert "TDS 1012C-EDU" in text(result)
    assert (rig.opened, rig.closed) == (1, 1)


def test_connection_is_closed_after_a_failure(tmp_path):
    srv, rig = make(tmp_path, {"*IDN?": "x"})
    rig.resource.fail_on.add("*IDN?")
    result = call(srv, "scope_idn")
    assert result.is_error
    assert (rig.opened, rig.closed) == (1, 1)


def test_state_uses_30_second_timeout_and_restores_it(tmp_path):
    srv, rig = make(tmp_path, {"SET?": ":HEADER 0;:VERBOSE 1"})
    call(srv, "scope_state")
    assert rig.resource.timeouts["SET?"] == 30_000
    assert rig.resource.timeout == 10_000


def test_errors_lists_events(tmp_path):
    srv, _ = make(tmp_path, {"*ESR?": "32", "ALLEv?": '113,"Undefined header"'})
    out = data(call(srv, "scope_errors"))
    assert out == {"events": [{"code": 113, "message": "Undefined header"}]}


def test_errors_empty(tmp_path):
    srv, _ = make(tmp_path, {"*ESR?": "0", "ALLEv?": '0,"No events to report - queue empty"'})
    assert data(call(srv, "scope_errors")) == {"events": []}


def test_query_returns_the_reply(tmp_path):
    srv, _ = make(tmp_path, {"CH1:SCAle?": "2.0E0"})
    result = call(srv, "scope_query", cmd="CH1:SCAle?")
    assert text(result) == "2.0E0"


@pytest.mark.parametrize("cmd", ["*TST?", "*CAL?", "CALibrate:FACtory?", "*SAV?", "*RCL?", "SAVe:SETUp?"])
def test_query_refuses_the_blocklist_without_connecting(tmp_path, cmd):
    srv, rig = make(tmp_path)
    result = call(srv, "scope_query", cmd=cmd)
    assert result.is_error
    assert "blocked" in text(result).lower()
    assert rig.opened == 0 and rig.written == []


def test_query_refuses_more_than_one_command(tmp_path):
    srv, rig = make(tmp_path)
    result = call(srv, "scope_query", cmd="*IDN?;*ESR?")
    assert result.is_error and rig.opened == 0


def test_query_refuses_a_command_that_is_not_a_query(tmp_path):
    srv, rig = make(tmp_path)
    result = call(srv, "scope_query", cmd="CH1:SCAle 2")
    assert result.is_error and rig.opened == 0 and rig.written == []


@pytest.mark.parametrize("cmd", ["*IDN?\n*RST", "*IDN?\r", "*IDN?\x00"])
def test_query_refuses_control_characters(tmp_path, cmd):
    srv, rig = make(tmp_path)
    assert call(srv, "scope_query", cmd=cmd).is_error and rig.opened == 0


@pytest.mark.parametrize("cmd", ["CURVe?", "curv?", "WAVFrm?", "HARDCopy?"])
def test_query_points_binary_replies_to_the_dedicated_tools(tmp_path, cmd):
    srv, rig = make(tmp_path)
    result = call(srv, "scope_query", cmd=cmd)
    assert result.is_error and rig.opened == 0
    assert "scope_waveform" in text(result) or "scope_screenshot" in text(result)


@pytest.mark.parametrize("cmd", ["SET?", "set?", "*LRN?"])
def test_long_queries_get_30_seconds(tmp_path, cmd):
    srv, rig = make(tmp_path, {cmd: "x"})
    call(srv, "scope_query", cmd=cmd)
    assert rig.resource.timeouts[cmd] == 30_000
    assert rig.resource.timeout == 10_000


def test_ordinary_query_keeps_the_default_timeout(tmp_path):
    srv, rig = make(tmp_path, {"HEADer?": "0"})
    call(srv, "scope_query", cmd="HEADer?")
    assert rig.resource.timeouts["HEADer?"] == 10_000


def test_measure(tmp_path):
    srv, rig = make(
        tmp_path,
        {"MEASUrement:IMMed:VALue?": "1.0E3", "MEASUrement:IMMed:UNIts?": '"Hz"'},
    )
    out = data(call(srv, "scope_measure", tipo="frequency", canal=1))
    assert out["value"] == 1000.0 and out["unit"] == "Hz"
    assert out["type"] == "FREQuency" and out["channel"] == 1
    assert rig.written[:2] == ["MEASUrement:IMMed:SOUrce CH1", "MEASUrement:IMMed:TYPe FREQuency"]


def test_measure_rejects_unknown_type_and_channel(tmp_path):
    srv, rig = make(tmp_path)
    assert call(srv, "scope_measure", tipo="FREQuency;*RST", canal=1).is_error
    assert call(srv, "scope_measure", tipo="FREQuency", canal=3).is_error
    assert rig.opened == 0


def test_measure_invalid_value_is_an_error(tmp_path):
    srv, _ = make(tmp_path, {"MEASUrement:IMMed:VALue?": "9.9E37"})
    result = call(srv, "scope_measure", tipo="PK2pk", canal=1)
    assert result.is_error and "no valid measurement" in text(result)


def _waveform_answers():
    pre = (
        "1;8;ASC;RP;MSB;2500;\"Ch1, DC coupling, 2.0E0 Volts/div, 5.0E-4 s/div, 2500 points, Sample mode\";"
        'Y;4.0E-6;0;-1.0E-3;"s";8.0E-2;0.0E0;0.0E0;"Volts"'
    )
    return {"WFMPre?": pre}


def test_waveform_summary_csv_and_limit_of_500_points(tmp_path):
    srv, rig = make(tmp_path, _waveform_answers())
    rig.resource.binary["CURVe?"] = [(i % 100) - 50 for i in range(2500)]
    out = data(call(srv, "scope_waveform", canal=1))
    assert out["channel"] == 1 and out["n_points"] == 2500
    assert 0 < len(out["points"]) <= 500
    assert set(out["stats"]) >= {"min", "max", "mean", "pk2pk", "rms"}
    assert out["stats"]["max"] > out["stats"]["min"]
    csv_path = out["csv_path"]
    assert csv_path.endswith(".csv")
    with open(csv_path, encoding="utf-8") as fh:
        assert len(fh.readlines()) == 2501
    assert str(tmp_path) in csv_path


def test_waveform_channel_off_is_an_error(tmp_path):
    srv, _ = make(tmp_path, {"WFMPre?": "1;8;ASC"})
    result = call(srv, "scope_waveform", canal=2)
    assert result.is_error and "preamble" in text(result)


def test_screenshot_returns_an_image(tmp_path):
    srv, rig = make(tmp_path)
    buf = io.BytesIO()
    PILImage.new("RGB", (4, 2), "white").save(buf, format="BMP")
    rig.resource.raw = buf.getvalue()
    result = call(srv, "scope_screenshot")
    assert not result.is_error
    images = [c for c in result.content if c.type == "image"]
    assert len(images) == 1 and images[0].mime_type == "image/png"
    assert list((tmp_path / "screenshots").glob("*.png"))


# -- write tools --------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("scope_set_channel", {"canal": 1, "scale": 1.0}),
        ("scope_set_timebase", {"scale": 1e-3}),
        ("scope_set_trigger", {"level": 1.0}),
        ("scope_set_acquisition", {"mode": "SAMple"}),
        ("scope_run", {}),
        ("scope_stop", {}),
        ("scope_single", {}),
        ("scope_autoset", {}),
        ("scope_write", {"cmd": "CH1:SCAle 1"}),
    ],
)
def test_write_tools_refuse_without_confirm(tmp_path, name, args):
    srv, rig = make(tmp_path)
    for extra in ({}, {"confirm": False}):
        result = call(srv, name, **args, **extra)
        assert result.is_error and "confirm" in text(result).lower()
    assert rig.opened == 0 and rig.written == []


def test_set_channel(tmp_path):
    srv, rig = make(tmp_path, {"*ESR?": "0", "ALLEv?": '0,"No events"'})
    out = data(
        call(
            srv,
            "scope_set_channel",
            canal=1,
            scale=2.0,
            position=-1.5,
            coupling="dc",
            probe=10,
            bandwidth=False,
            invert=True,
            confirm=True,
        )
    )
    assert rig.written[:6] == [
        "CH1:SCAle 2",
        "CH1:POSition -1.5",
        "CH1:COUPling DC",
        "CH1:PRObe 10",
        "CH1:BANdwidth OFF",
        "CH1:INVert ON",
    ]
    assert out["errors"] == []


@pytest.mark.parametrize(
    "args",
    [
        {"canal": 3, "scale": 1.0},
        {"canal": 1},
        {"canal": 1, "scale": -1.0},
        {"canal": 1, "scale": float("nan")},
        {"canal": 1, "coupling": "DC;*RST"},
        {"canal": 1, "probe": 7},
    ],
)
def test_set_channel_rejects_bad_values(tmp_path, args):
    srv, rig = make(tmp_path)
    assert call(srv, "scope_set_channel", **args, confirm=True).is_error
    assert rig.opened == 0 and rig.written == []


def test_set_timebase(tmp_path):
    srv, rig = make(tmp_path, {"*ESR?": "0", "ALLEv?": '0,"No events"'})
    call(srv, "scope_set_timebase", scale=1e-3, position=0.0, confirm=True)
    assert rig.written[:2] == ["HORizontal:MAIn:SCAle 0.001", "HORizontal:MAIn:POSition 0"]


def test_set_trigger(tmp_path):
    srv, rig = make(tmp_path, {"*ESR?": "0", "ALLEv?": '0,"No events"'})
    call(
        srv,
        "scope_set_trigger",
        source="ch2",
        slope="rise",
        coupling="DC",
        level=0.5,
        mode="normal",
        confirm=True,
    )
    assert rig.written[:5] == [
        "TRIGger:MAIn:EDGE:SOUrce CH2",
        "TRIGger:MAIn:EDGE:SLOpe RISe",
        "TRIGger:MAIn:EDGE:COUPling DC",
        "TRIGger:MAIn:LEVel 0.5",
        "TRIGger:MAIn:MODe NORMal",
    ]


def test_set_trigger_rejects_bad_source(tmp_path):
    srv, rig = make(tmp_path)
    assert call(srv, "scope_set_trigger", source="CH1;*RST", confirm=True).is_error
    assert rig.opened == 0


def test_set_acquisition(tmp_path):
    srv, rig = make(tmp_path, {"*ESR?": "0", "ALLEv?": '0,"No events"'})
    call(srv, "scope_set_acquisition", mode="average", num_avg=16, stop_after="sequence", confirm=True)
    assert rig.written[:3] == ["ACQuire:MODe AVErage", "ACQuire:NUMAVg 16", "ACQuire:STOPAfter SEQuence"]
    assert call(srv, "scope_set_acquisition", num_avg=10, confirm=True).is_error


def test_run_stop_single_autoset(tmp_path):
    srv, rig = make(tmp_path, {"*OPC?": "1", "*ESR?": "0", "ALLEv?": '0,"No events"'})
    call(srv, "scope_run", confirm=True)
    call(srv, "scope_stop", confirm=True)
    call(srv, "scope_single", confirm=True)
    call(srv, "scope_autoset", confirm=True)
    assert "ACQuire:STATE RUN" in rig.written and "ACQuire:STATE STOP" in rig.written
    assert "ACQuire:STOPAfter SEQuence" in rig.written
    assert "AUTOSet EXECute" in rig.written


def test_write_sends_a_checked_command(tmp_path):
    srv, rig = make(tmp_path, {"*ESR?": "0", "ALLEv?": '0,"No events"'})
    result = call(srv, "scope_write", cmd="CH1:SCAle 1", confirm=True)
    assert not result.is_error
    assert rig.written[0] == "CH1:SCAle 1"


@pytest.mark.parametrize(
    "cmd",
    [
        "*RST",
        "FACtory",
        "CALibrate:INTERNal",
        "SAVe:SETUp 1",
        "RECAll:SETUp 1",
        "*SAV 1",
        "*RCL 1",
        "FILESystem:FORMat",
        "DIAg:EXECute",
        "CH1:SCAle 1;*RST",
        "CH1:SCAle 1;:FACtory",
        "CH1:SCAle?",
        "CH1:SCAle 1\n*RST",
        "",
    ],
)
def test_write_refuses_blocked_queries_and_odd_input(tmp_path, cmd):
    srv, rig = make(tmp_path)
    result = call(srv, "scope_write", cmd=cmd, confirm=True)
    assert result.is_error
    assert rig.opened == 0 and rig.written == []


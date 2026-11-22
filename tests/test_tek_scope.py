"""Unit tests for TekScope with a fake VISA resource (no hardware needed)."""

import struct

import numpy as np
import pytest
from PIL import Image

from tek_scope import BlockedCommandError, MeasurementError, ScopeLock, TekScope, WaveformError


class FakeResource:
    """Minimal stand-in for a pyvisa MessageBasedResource."""

    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.written = []
        self.timeout = 10000
        self.read_termination = "\n"
        self.write_termination = "\n"
        self.binary = {}
        self.raw = b""
        self.closed = False
        self.raw_read_termination = "unset"
        self.raw_timeout = None

    def write(self, cmd):
        self.written.append(cmd)

    def query(self, cmd):
        self.written.append(cmd)
        value = self.answers[cmd]
        return value.pop(0) if isinstance(value, list) else value

    def query_binary_values(self, cmd, datatype, is_big_endian, container, expect_termination=True):
        self.written.append(cmd)
        assert datatype == "b" and is_big_endian
        self.binary_timeout = self.timeout
        return container(self.binary[cmd])

    def read_raw(self):
        self.raw_read_termination = self.read_termination
        self.raw_timeout = self.timeout
        data, self.raw = self.raw, b""
        return data

    def close(self):
        self.closed = True


@pytest.fixture
def scope(tmp_path):
    res = FakeResource()
    s = TekScope(resource=res, log_path=tmp_path / "writes.log", lock_path=tmp_path / "scope.lock")
    s.connect()
    yield s
    s.close()


def test_write_is_logged(scope, tmp_path):
    scope.write("CH1:SCAle 2.0")
    assert scope.resource.written == ["CH1:SCAle 2.0"]
    assert "CH1:SCAle 2.0" in (tmp_path / "writes.log").read_text(encoding="utf-8")


def test_blocked_write_is_refused_and_not_sent(scope, tmp_path):
    with pytest.raises(BlockedCommandError):
        scope.write("*RST")
    assert scope.resource.written == []
    assert "REFUSED" in (tmp_path / "writes.log").read_text(encoding="utf-8")


def test_query_with_set_command_is_logged_as_write(scope, tmp_path):
    scope.resource.answers = {"CH1:SCAle 1;*OPC?": "1"}
    scope.query("CH1:SCAle 1;*OPC?")
    assert "WRITE\tCH1:SCAle 1;*OPC?" in (tmp_path / "writes.log").read_text(encoding="utf-8")


def test_pure_query_is_not_logged(scope, tmp_path):
    scope.resource.answers = {"*IDN?": "x"}
    scope.query("*IDN?")
    log = tmp_path / "writes.log"
    assert not log.exists() or "*IDN?" not in log.read_text(encoding="utf-8")


def test_blocked_query_is_refused(scope):
    with pytest.raises(BlockedCommandError):
        scope.query("*TST?")
    assert scope.resource.written == []


def test_allow_dangerous_lets_blocked_command_through(scope):
    scope.write("*RST", allow_dangerous=True)
    assert scope.resource.written == ["*RST"]


def test_lock_allows_one_connection_at_a_time(tmp_path):
    lock = tmp_path / "scope.lock"
    a = TekScope(resource=FakeResource(), log_path=tmp_path / "w.log", lock_path=lock)
    b = TekScope(resource=FakeResource(), log_path=tmp_path / "w.log", lock_path=lock)
    a.connect()
    with pytest.raises(RuntimeError, match="in use"):
        b.connect()
    a.close()
    b.connect()  # free again after close
    b.close()


def test_scope_lock_releases_on_release(tmp_path):
    lock = ScopeLock(tmp_path / "x.lock")
    lock.acquire()
    lock.release()
    lock.acquire()
    lock.release()


def test_close_closes_resource(tmp_path):
    res = FakeResource()
    s = TekScope(resource=res, log_path=tmp_path / "w.log", lock_path=tmp_path / "l.lock")
    s.connect()
    s.close()
    assert res.closed


def test_errors_empty_when_queue_empty(scope):
    scope.resource.answers = {"*ESR?": "0", "ALLEv?": '0,"No events to report - queue empty"'}
    assert scope.errors() == []
    assert scope.resource.written == ["*ESR?", "ALLEv?"]


def test_errors_returns_events(scope):
    scope.resource.answers = {
        "*ESR?": "16",
        "ALLEv?": '2225,"Measurement error, No waveform to measure; ",420,"Query UNTERMINATED; "',
    }
    events = scope.errors()
    assert [code for code, _ in events] == [2225, 420]
    assert events[0][1].startswith("Measurement error")


def test_errors_reports_esr_error_bits_without_events(scope):
    scope.resource.answers = {"*ESR?": "32", "ALLEv?": '0,"No events to report - queue empty"'}
    assert scope.errors() == [(None, "ESR=32")]


def test_channel_scale_get_and_set(scope):
    scope.resource.answers = {"CH1:SCAle?": "2.0E0"}
    assert scope.channel_scale(1) == 2.0
    scope.channel_scale(2, 0.5)
    assert scope.resource.written[-1] == "CH2:SCAle 0.5"


def test_channel_rejects_bad_number(scope):
    with pytest.raises(ValueError):
        scope.channel_scale(3)


def test_probe_set(scope):
    scope.channel_probe(1, 10)
    assert scope.resource.written[-1] == "CH1:PRObe 10"


def test_trigger_state(scope):
    scope.resource.answers = {"TRIGger:STATE?": "AUTO"}
    assert scope.trigger_state() == "AUTO"


def test_single_waits_for_opc_with_long_timeout(scope):
    scope.resource.answers = {"*OPC?": "1"}
    scope.single()
    assert scope.resource.written == ["ACQuire:STOPAfter SEQuence", "ACQuire:STATE RUN", "*OPC?"]
    assert scope.resource.timeout == 10000  # restored after waiting


def test_run_and_stop(scope):
    scope.resource.answers = {"*OPC?": "1"}
    scope.run()
    scope.stop()
    assert scope.resource.written == [
        "ACQuire:STOPAfter RUNSTop",
        "ACQuire:STATE RUN",
        "*OPC?",
        "ACQuire:STATE STOP",
        "*OPC?",
    ]


def test_measure_sets_source_and_type(scope):
    scope.resource.answers = {"MEASUrement:IMMed:VALue?": "1.0E3"}
    assert scope.measure("FREQuency", 1) == 1000.0
    assert scope.resource.written == [
        "MEASUrement:IMMed:SOUrce CH1",
        "MEASUrement:IMMed:TYPe FREQuency",
        "MEASUrement:IMMed:VALue?",
    ]


def test_measure_invalid_value_raises(scope):
    scope.resource.answers = {"MEASUrement:IMMed:VALue?": "9.9E37"}
    with pytest.raises(MeasurementError):
        scope.measure("PK2pk", 1)


def _preamble_answers():
    wfid = '"Ch1, DC coupling, 2.0E0 V/div, 2.5E-4 s/div, 2500 points, Sample mode"'
    return {
        "WFMPre?": f'1;8;BIN;RI;MSB;2500;{wfid};Y;1.0E-6;0;-1.25E-3;"s";8.0E-2;0.0E0;-2.5E1;"V"',
    }


def test_waveform_converts_samples(scope):
    scope.resource.answers = _preamble_answers()
    samples = np.arange(-125, 125, 0.1).astype(np.int8)[:2500]
    scope.resource.binary = {"CURVe?": samples}
    t, v, pre = scope.waveform(1)
    assert scope.resource.written[:5] == [
        "DATa:SOUrce CH1",
        "DATa:ENCdg RIBinary",
        "DATa:WIDth 1",
        "DATa:STARt 1",
        "DATa:STOP 2500",
    ]
    assert len(t) == len(v) == 2500
    assert t[0] == pytest.approx(-1.25e-3)
    assert t[10] == pytest.approx(-1.25e-3 + 10e-6)
    assert v[0] == pytest.approx(0.08 * (samples[0] - (-25)))
    assert pre["NR_PT"] == 2500
    assert pre["WFID"].startswith("Ch1, DC coupling")
    assert scope.resource.binary_timeout == 30000


def test_waveform_channel_not_displayed_raises(scope):
    scope.resource.answers = {"WFMPre?": "1;8;BIN;RI;MSB"}
    with pytest.raises(WaveformError):
        scope.waveform(2)


def test_save_csv_writes_last_waveform(scope, tmp_path):
    scope.resource.answers = _preamble_answers()
    scope.resource.binary = {"CURVe?": np.zeros(2500, dtype=np.int8)}
    scope.waveform(1)
    out = tmp_path / "ch1.csv"
    scope.save_csv(out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "time_s,volts"
    assert len(lines) == 2501


def _bmp_bytes():
    img = Image.new("RGB", (32, 24), (10, 200, 30))
    import io

    buf = io.BytesIO()
    img.save(buf, format="BMP")
    return buf.getvalue()


def test_screenshot_saves_png_and_reads_raw_without_termination(scope, tmp_path):
    bmp = _bmp_bytes()
    assert struct.unpack("<I", bmp[2:6])[0] == len(bmp)
    scope.resource.raw = bmp
    out = tmp_path / "screen.png"
    scope.screenshot(out)
    assert scope.resource.written == ["HARDCopy:FORMat BMP", "HARDCopy:PORT USB", "HARDCopy STARt"]
    assert scope.resource.raw_read_termination is None
    assert scope.resource.raw_timeout == 30000
    assert scope.resource.read_termination == "\n"  # restored
    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (32, 24)


def test_screenshot_truncated_bmp_raises(scope, tmp_path):
    scope.resource.raw = _bmp_bytes()[:100]
    with pytest.raises(RuntimeError, match="short"):
        scope.screenshot(tmp_path / "s.png")


def test_restore_sends_set_text_without_blocked_segment(scope):
    scope.resource.answers = {"*OPC?": "1"}
    removed = scope.restore(":HEADER 0;:LANGUAGE PORTUGUESE;:SAVE:IMAGE:FILEFORMAT JPEG")
    assert scope.resource.written == [":HEADER 0", ":LANGUAGE PORTUGUESE", "*OPC?"]
    assert removed == [":SAVE:IMAGE:FILEFORMAT JPEG"]


def test_restore_sends_one_message_per_absolute_group_with_long_timeout(scope):
    seen = []
    original_write = scope.resource.write

    def spy(cmd):
        seen.append(scope.resource.timeout)
        original_write(cmd)

    scope.resource.write = spy
    scope.resource.answers = {"*OPC?": "1"}
    scope.restore(":ACQUIRE:MODE SAMPLE;NUMAVG 16;:CH1:PROBE 1.0E1;SCALE 2.0E0")
    assert scope.resource.written == [":ACQUIRE:MODE SAMPLE;NUMAVG 16", ":CH1:PROBE 1.0E1;SCALE 2.0E0", "*OPC?"]
    assert seen == [30000, 30000]
    assert scope.resource.timeout == 10000


def test_autoset(scope):
    scope.resource.answers = {"*OPC?": "1", "BUSY?": "0"}
    scope.autoset()
    assert scope.resource.written[0] == "AUTOSet EXECute"

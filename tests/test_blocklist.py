"""Tests for the fixed command blocklist (see CLAUDE.md, "Blocked commands")."""

import pytest

from tek_scope import blocked_reason, segment_headers, strip_blocked_segments


@pytest.mark.parametrize(
    "cmd",
    [
        "*CAL?",
        "*cal?",
        "*TST?",
        "*RST",
        "FACtory",
        "FAC",
        "factory",
        "CALibrate:INTERNAL",
        "cal:internal",
        "CALIBRATE:CONTINUE",
        "CAL:FACtory",
        "SAVe:SETUp 1",
        "SAV:IMAG:FILEF?",
        ":SAVE:IMAGE:FILEFORMAT JPEG",
        "RECAll:SETUp 1",
        "RECA:SETU?",
        "FILESystem:FORMat",
        "FILES:DELEte \"A.TXT\"",
        "DIAg:LOOP:OPTion ONCE",
        "dia:exec",
        # *SAV overwrites a stored setup; *RCL replaces every setting
        "*SAV 1",
        "*sav 1",
        "*RCL 1",
        "*RCL?",
        "*SAV?",
        "*CLS;*SAV 2",
        # hidden inside a concatenated line
        "HARDCopy:FORMat BMP;:SAVe:SETUp 1",
        "HARDCopy:FORMat BMP;*RST",
        "*CLS; *RST",
        # relative header after ';' inherits CALibrate:
        "CALibrate:STATUS?;INTERNAL",
    ],
)
def test_blocked_commands_are_refused(cmd):
    assert blocked_reason(cmd) is not None


@pytest.mark.parametrize(
    "cmd",
    [
        "*IDN?",
        "*ESR?",
        "*OPC?",
        "*CLS",
        "CALibrate:STATUS?",
        "cal:status?",
        "FILESystem:DIR?",
        "FILES:CWD?",
        "DIAg:RESUlt:FLAg?",
        "SET?",
        "CH1:SCAle 2.0",
        "HARDCopy:FORMat BMP;PORT USB",
        "ACQuire:MODe AVErage;NUMAVg 16",
        ':MATH:DEFINE "CH1 - CH2;*RST"',
        "FACTORYX?",  # not the FACtory mnemonic
    ],
)
def test_allowed_commands_pass(cmd):
    assert blocked_reason(cmd) is None


def test_relative_headers_inherit_previous_path():
    assert segment_headers("ACQuire:MODe AVErage;NUMAVg 16;:CH1:SCAle 1") == [
        "ACQUIRE:MODE",
        "ACQUIRE:NUMAVG",
        "CH1:SCALE",
    ]


def test_semicolon_inside_quotes_does_not_split():
    assert segment_headers(':MATH:DEFINE "A;B";:CH1:PROBE 10') == ["MATH:DEFINE", "CH1:PROBE"]


def test_strip_removes_save_segment_and_its_relatives_from_set_text():
    text = (
        ":HEADER 0;:HARDCOPY:BUTTON SAVESIMAGE;FORMAT JPEG;PORT USB;"
        ":LANGUAGE PORTUGUESE;:SAVE:IMAGE:FILEFORMAT JPEG;:AUTORANGE:SETTINGS BOTH"
    )
    clean, removed = strip_blocked_segments(text)
    assert removed == [":SAVE:IMAGE:FILEFORMAT JPEG"]
    assert clean == (
        ":HEADER 0;:HARDCOPY:BUTTON SAVESIMAGE;FORMAT JPEG;PORT USB;"
        ":LANGUAGE PORTUGUESE;:AUTORANGE:SETTINGS BOTH"
    )
    assert blocked_reason(clean) is None


def test_strip_at_end_of_text():
    clean, removed = strip_blocked_segments(":LANGUAGE ENGLISH;:SAVE:IMAGE:FILEFORMAT JPEG")
    assert clean == ":LANGUAGE ENGLISH"
    assert removed == [":SAVE:IMAGE:FILEFORMAT JPEG"]

# tek-scope-mcp

A Python control library and a local MCP server for the Tektronix TDS 1012C-EDU oscilloscope over USB (USBTMC through PyVISA). The goal is to let an AI assistant such as Claude read the screen, waveforms and measurements, and change channel, timebase and trigger settings, using only the commands in the Tektronix programmer manual.

This is an independent project. It is not affiliated with, sponsored by or endorsed by Tektronix. "Tektronix" is a trademark of its owner.

## Status

| | Status |
|---|---|
| Repository layout, safety rules, build prompts | done |
| USB connection (VISA backend, `*IDN?`) | done, tested on hardware: NI-VISA 2026 Q4 on Windows 11, `*IDN?` answered 3 times in a row, `SET?` read. See [docs/connection.md](docs/connection.md). |
| Control library `tek_scope.py` | done, acceptance passed on hardware with the probe compensation signal on CH1 (1.000 kHz, 5.20 V peak to peak, 2500-point waveform, screen capture, no errors, `SET?` restored). Unit tests with a fake instrument in [tests/](tests/). |
| Command map (which queries the instrument answers) | not started |
| MCP server `server.py` | not started |

Tested on hardware so far: opening the USB resource; `*CLS`, `*IDN?`, `*ESR?`, `*OPC?`, `ALLEv?`, `BUSY?`, `HEADer`, `VERBose`, `SET?` and sending it back; `CH1:PRObe`; `TRIGger:MAIn:LEVel` and `TRIGger:MAIn SETLevel`; `MEASUrement:IMMed:SOUrce`, `:TYPe` (`FREQuency`, `PK2pk`), `:VALue?`; `DATa:SOUrce`, `:ENCdg RIBinary`, `:WIDth 1`, `:STARt`, `:STOP`, `WFMPre?`, `CURVe?`; `HARDCopy:FORMat BMP`, `HARDCopy:PORT USB`, `HARDCopy STARt`.

Implemented but not yet run on hardware: the other channel setters (`SCAle`, `POSition`, `COUPling`, `BANdwidth`, `INVert`), horizontal scale and position, the other edge-trigger setters, `TRIGger:STATE?`, `run()`, `stop()`, `single()`, `autoset()` and `ACQuire:MODe`/`NUMAVg`. Not tested: the pyvisa-py + Zadig path, other Windows versions, other instrument models. This table is updated at the end of each build step, with what was tested and what was not.

Known limits found on hardware:

- A trigger level set from the front panel or by autoset can be finer than what `TRIGger:MAIn:LEVel` accepts. By command, the level moves in steps (0.08 V at 2 V/div), so restoring such a `SET?` gives the nearest step.
- `SET?` contains `:SAVE:IMAGE:FILEFORMAT`, which is in the blocklist. `restore()` leaves it out. On this model `HARDCopy:FORMat` changes the saved-image format too, so the value still comes back.
- Sending the whole `SET?` text in one write can take longer than 10 s. `restore()` sends it in groups, with a 30 s timeout.

## Using the library

```python
from tek_scope import TekScope

with TekScope() as scope:          # finds the first Tektronix USB instrument, or TEK_SCOPE_RESOURCE
    print(scope.idn())
    print(scope.measure("FREQuency", 1))
    t, v, preamble = scope.waveform(1)
    scope.save_csv("ch1.csv")
    scope.screenshot("screen.png")
```

Only one process can hold the instrument at a time (a lock file in `local/`). Every write is logged to `local/logs/escritas.log`. Blocked commands raise `BlockedCommandError` unless `allow_dangerous=True` is passed. `scripts/hardware_acceptance.py` runs the build-step 2 acceptance and restores the settings afterwards.

Example output from the acceptance run: [docs/ch1.png](docs/ch1.png), [docs/ch1.csv](docs/ch1.csv), [docs/screen.png](docs/screen.png).

Test instrument: TDS 1012C-EDU, firmware v25.11, Windows notebook. Other models covered by the same programmer manual (TDS2000C, TDS1000B/2000B, TBS1000) are untested.

## What it is for

1. Read the instrument: identity, full settings (`SET?`), screen image, waveform data, measurements.
2. Change settings: channels, timebase, edge trigger, acquisition, autoset.
3. Publish a command map: which queries from the programmer manual this model answers, including commands the manual lists for other series.

## What it will not do

- No firmware changes, no factory calibration, no unlocking of features.
- No guessing of commands by brute force. Every command comes from the programmer manual.

## Safety

The library and the server refuse these commands by default:

- `*CAL?`, `*TST?` and every `CALibrate:` command except `CALibrate:STATUS?`. Factory calibration is for qualified service only and can leave the instrument out of calibration.
- `FACtory`, `*RST`, `SAVe:`, `RECAll:` and every `FILESystem:` command that is not a query. `FILESystem:FORMat` erases the USB flash drive in the front port.
- `DIAg:` commands that are not queries.

Commands that change settings need an explicit confirmation in the MCP server. Every write is logged locally.

You use this software at your own risk. See [LICENSE](LICENSE).

## Reference manual

*Digital Oscilloscope Series Programmer Manual*, Tektronix part number 077044403. Download it from the Tektronix website. The PDF is not included in this repository.

## How it is being built

The project is built with Claude Code in four steps. The prompts are in [prompts/](prompts/) (in Portuguese), each with the model and effort level used. Rules for AI agents are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE)

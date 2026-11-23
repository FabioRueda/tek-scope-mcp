# tek-scope-mcp

A Python control library and a local MCP server for the Tektronix TDS 1012C-EDU oscilloscope over USB (USBTMC through PyVISA). The goal is to let an AI assistant such as Claude read the screen, waveforms and measurements, and change channel, timebase and trigger settings, using only the commands in the Tektronix programmer manual.

This is an independent project. It is not affiliated with, sponsored by or endorsed by Tektronix. "Tektronix" is a trademark of its owner.

## Status

| | Status |
|---|---|
| Repository layout, safety rules, build prompts | done |
| USB connection (VISA backend, `*IDN?`) | done, tested on hardware: NI-VISA 2026 Q4 on Windows 11, `*IDN?` answered 3 times in a row, `SET?` read. See [docs/connection.md](docs/connection.md). |
| Control library `tek_scope.py` | done, acceptance passed on hardware with the probe compensation signal on CH1 (1.000 kHz, 5.20 V peak to peak, 2500-point waveform, screen capture, no errors, `SET?` restored). Unit tests with a fake instrument in [tests/](tests/). `*SAV` and `*RCL` were added to the blocklist later; that change has unit tests only and was not sent to the hardware. |
| Command map (which queries the instrument answers) | done, run on hardware: all 345 headers of the manual classified, 301 queries sent, 179 accepted (7 of them documented only for other series), `SET?` and `CALibrate:STATUS?` unchanged at the end. See [docs/COMMAND-MAP.md](docs/COMMAND-MAP.md). |
| MCP server `server.py` | done, read tools tested on hardware: `scope_idn`, `scope_state`, `scope_errors`, `scope_query`, `scope_measure`, `scope_waveform` and `scope_screenshot` answered through the library, and `scope_idn` and `scope_screenshot` also through a stdio MCP client against the real server process and through Claude Code itself (registered as `tek-scope`, `claude mcp list` shows it connected). Unit tests with a fake instrument in [tests/test_server.py](tests/test_server.py). The setting tools (`scope_set_*`, `scope_run`, `scope_stop`, `scope_single`, `scope_autoset`, `scope_write`) have unit tests only and were not sent to the hardware. Registration in Claude Code and in the Claude desktop app: see [Using the MCP server](#using-the-mcp-server). |

Tested on hardware so far: opening the USB resource; `*CLS`, `*IDN?`, `*ESR?`, `*OPC?`, `ALLEv?`, `BUSY?`, `HEADer`, `VERBose`, `SET?` and sending it back; `CH1:PRObe`; `TRIGger:MAIn:LEVel` and `TRIGger:MAIn SETLevel`; `MEASUrement:IMMed:SOUrce`, `:TYPe` (`FREQuency`, `PK2pk`), `:VALue?`; `DATa:SOUrce`, `:ENCdg RIBinary`, `:WIDth 1`, `:STARt`, `:STOP`, `WFMPre?`, `CURVe?`; `HARDCopy:FORMat BMP`, `HARDCopy:PORT USB`, `HARDCopy STARt`.

The command map (build step 3) sent the query form of every documented header that has one; the replies are in [docs/scpi_map.json](docs/scpi_map.json). Not sent by design: commands without a query form, `CURVe?`, `WAVFrm?`, `HARDCopy?` and the blocklist. The only writes were `HEADer` and `VERBose`, set back at the end.

The command map also answered, on hardware, the queries behind the other library getters: `CH1:SCAle?`, `POSition?`, `COUPling?`, `BANdwidth?`, `INVert?`, `HORizontal:MAIn:SCAle?`, `POSition?`, the `TRIGger:MAIn:EDGE:*?` queries, `TRIGger:MAIn:MODe?`, `TRIGger:STATE?`, `ACQuire:MODe?` and `NUMAVg?`.

Implemented but not yet run on hardware (build step 3 allowed no writes): the setters for channel (`SCAle`, `POSition`, `COUPling`, `BANdwidth`, `INVert`), horizontal scale and position, the other edge-trigger settings and `ACQuire:MODe`/`NUMAVg`, and `run()`, `stop()`, `single()` and `autoset()`. Not tested: the pyvisa-py + Zadig path, other Windows versions, other instrument models. This table is updated at the end of each build step, with what was tested and what was not.

Known limits found on hardware:

- A trigger level set from the front panel or by autoset can be finer than what `TRIGger:MAIn:LEVel` accepts. By command, the level moves in steps (0.08 V at 2 V/div), so restoring such a `SET?` gives the nearest step.
- `SET?` contains `:SAVE:IMAGE:FILEFORMAT`, which is in the blocklist. `restore()` leaves it out. On this model `HARDCopy:FORMat` changes the saved-image format too, so the value still comes back.
- Sending the whole `SET?` text in one write can take longer than 10 s. `restore()` sends it in groups, with a 30 s timeout.
- Reading `SET?` (and `*LRN?`) takes about 5 s.
- A query the instrument does not know gets no reply, so the read waits for the timeout. With NI-VISA a 3 s timeout waited about 5 s.
- After 37 such timeouts in one VISA session, each followed by a USBTMC device clear, the 38th device clear failed (`VI_ERROR_INV_PARAMETER`) and the next write failed (`VI_ERROR_SYSTEM_ERROR`). Reading the status byte right after an unknown command failed the same way. The instrument itself kept working: a new session answered at once. `scripts/explore_scpi.py` closes and reopens the session after every timeout instead.
- The `WFMPre:<field>?` queries describe the `DATa:SOUrce` waveform. When that waveform is not displayed they give event 2244 and no reply; `WFMPre:CH1:<field>?` still works.
- The instrument answers the `RS232` queries and `MEASUrement:IMMed:SOURCE2?`, which the manual lists only for other series.

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

To rebuild the command map: `python scripts/extract_manual_commands.py <manual.pdf>` (needs `pdftotext`) writes [docs/manual-commands.json](docs/manual-commands.json); `python scripts/explore_scpi.py run` probes the instrument, and `python scripts/explore_scpi.py report <log> <SET? file>` writes the map.

Only one process can hold the instrument at a time (a lock file in `local/`). Every write is logged to `local/logs/escritas.log`. Blocked commands raise `BlockedCommandError` unless `allow_dangerous=True` is passed. `scripts/hardware_acceptance.py` runs the build-step 2 acceptance and restores the settings afterwards.

## Using the MCP server

`server.py` exposes the library as a local MCP server over stdio, built on the official MCP Python SDK (`mcp`, version 2).

Install: `python -m venv .venv`, activate it, `pip install -r requirements.txt`.

Register it in Claude Code (user scope), using the absolute paths of your own virtual environment and checkout:

```
claude mcp add --scope user tek-scope -- <path to .venv python> <path to server.py>
```

For the Claude desktop app, add the same command to `mcpServers` in `claude_desktop_config.json`, then close and reopen the app:

```json
{ "mcpServers": { "tek-scope": { "command": "<path to .venv python>", "args": ["<path to server.py>"] } } }
```

Each call opens the USB connection, does its work and closes it, so only one client can use the instrument at a time (the lock file in `local/`). After a timeout the next call starts a fresh VISA session. `SET?` and `*LRN?` get a 30 s timeout because the instrument needs about 5 s to answer.

Read tools (no confirmation):

| Tool | What it does |
|---|---|
| `scope_idn` | `*IDN?` |
| `scope_state` | all settings (`SET?`) |
| `scope_errors` | reads and clears the event queue |
| `scope_query(cmd)` | one query per call; refuses the blocklist, non-queries and the binary queries (`CURVe?`, `WAVFrm?`, `HARDCopy?`) |
| `scope_measure(tipo, canal)` | one immediate measurement on CH1 or CH2 |
| `scope_waveform(canal)` | statistics, the path of a CSV with all 2500 points, and at most 500 points |
| `scope_screenshot()` | the screen as a PNG image |

Tools that change the instrument need `confirm=true`: `scope_set_channel`, `scope_set_timebase`, `scope_set_trigger`, `scope_set_acquisition`, `scope_run`, `scope_stop`, `scope_single`, `scope_autoset`, `scope_write(cmd)`. Values are checked against the argument lists in the programmer manual before anything is sent. `scope_measure`, `scope_waveform` and `scope_screenshot` also set a few settings (`MEASUrement:IMMed:*`, `DATa:*`, `HARDCopy:*`), as the library does.

The blocklist from [Safety](#safety) applies to every tool, and no tool can lift it: there is no `allow_dangerous` in the server.

To switch the write tools off, set `TEK_SCOPE_READONLY=1` in the environment of the server (for example `claude mcp add --scope user --env TEK_SCOPE_READONLY=1 ...`, or an `env` entry in the desktop config). Those tools are then not listed at all. To remove the server: `claude mcp remove tek-scope`.

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
- `*SAV` and `*RCL`, with or without `?`. `*SAV` overwrites a setup stored in internal memory and `*RCL` replaces every setting at once, the same risks as `SAVe:` and `RECAll:`.
- `DIAg:` commands that are not queries.

Commands that change settings need an explicit confirmation in the MCP server. Every write is logged locally.

You use this software at your own risk. See [LICENSE](LICENSE).

## Reference manual

*Digital Oscilloscope Series Programmer Manual*, Tektronix part number 077044403. Download it from the Tektronix website. The PDF is not included in this repository.

## How it is being built

The project is built with Claude Code in four steps. The prompts are in [prompts/](prompts/) (in Portuguese), each with the model and effort level used. Rules for AI agents are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE)

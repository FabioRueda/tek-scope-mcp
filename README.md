# tek-scope-mcp

A Python control library and a local MCP server for the Tektronix TDS 1012C-EDU oscilloscope over USB (USBTMC through PyVISA). The goal is to let an AI assistant such as Claude read the screen, waveforms and measurements, and change channel, timebase and trigger settings, using only the commands in the Tektronix programmer manual.

This is an independent project. It is not affiliated with, sponsored by or endorsed by Tektronix. "Tektronix" is a trademark of its owner.

## Status

| | Status |
|---|---|
| Repository layout, safety rules, build prompts | done |
| USB connection (VISA backend, `*IDN?`) | not started |
| Control library `tek_scope.py` | not started |
| Command map (which queries the instrument answers) | not started |
| MCP server `server.py` | not started |

**Nothing in this repository has run on hardware yet.** This table is updated at the end of each build step, with what was tested and what was not.

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

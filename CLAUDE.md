# Notes for AI agents

Read [README.md](README.md) first. The build steps are in [prompts/](prompts/), in Portuguese. Run them in order, one per conversation.

## Scope

- Control of the owner's own TDS 1012C-EDU with the commands in the Tektronix programmer manual (part number 077044403).
- Out of scope: firmware, factory calibration, unlocking features, guessing commands by brute force.

## Rules

- **Do not guess command syntax.** Check every command in the programmer manual before using it. If the manual and a prompt disagree, the manual wins; write the difference down in the report.
- **Blocked commands.** Never send these, unless the user asks for that exact command in that turn:
  - `*CAL?`, `*TST?`
  - every `CALibrate:` command except `CALibrate:STATUS?`
  - `FACtory`, `*RST`
  - `SAVe:`, `RECAll:`
  - every `FILESystem:` command that is not a query
  - `DIAg:` commands that are not queries
- **Save and restore.** Before any test that changes instrument settings, save `SET?` to `local/backup/`. Restore it at the end and compare.
- **One VISA connection at a time.** The USB resource accepts one process. Close the connection after use.
- **Do not replace USB drivers** (Zadig or similar) without the user's explicit OK in that turn. Selecting the wrong device breaks another USB device.
- **Do not pin package versions.** `requirements.txt` lists names only.
- **Keys and passwords** go in environment variables, never in files.

## What is public and what is local

- `local/` is ignored by git. It holds everything specific to the owner's machine: `ESTADO.md`, `RELATORIO-*.md`, `backup/`, `logs/`, `manual/` (the PDF).
- Never commit: the instrument serial number, a VISA resource string that contains it, Windows user paths, the manual PDF.
- Public files (`README.md`, `docs/`, code, comments) are in English. `prompts/` and `local/` are in Portuguese.

## Before every commit

1. Run `ruff check .` and `pytest`. Both must pass.
2. Search the tracked files for the serial number written in `local/ESTADO.md` and for `C:\Users\`. Replace any match with `<SERIAL>` or a relative path.
3. Update the Status table in `README.md`: what was tested on hardware, and what was not.
4. Commit with a short prefix (`feat:`, `fix:`, `docs:`, `test:`) and push to `main`.

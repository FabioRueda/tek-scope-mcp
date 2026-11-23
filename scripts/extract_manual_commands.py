"""Extract every command header from the programmer manual (Tektronix 077044403).

Usage: python scripts/extract_manual_commands.py <manual.pdf> [docs/manual-commands.json]

Needs `pdftotext` (poppler) on PATH. The PDF is not part of the repository.

Sources, in order:
1. The manual index: every entry that points into Command Descriptions (pages 2-39 to 2-224).
2. Headings in Command Descriptions that the index leaves out (the WFMPre:<wfm>:* forms).
3. Table 2-36, "WFMPre, Additional Commands for Compatibility".

For each header the script records the group, the syntax lines, whether a query form exists (and why),
and whether the manual says it applies to the TDS1000C-EDU (and why).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "TDS1000C-EDU"
FOOT = re.compile(r"^(TBS1000/B/EDU, TDS2000/B/C.*Programmer|Command Descriptions|2-\d+)$")
LABEL = re.compile(r"^\s*\((Query Only|No Query Form)\)")

# Headings in Command Descriptions that the index does not list.
EXTRA_HEADINGS = [
    "WFMPre:<wfm>:PT_Fmt", "WFMPre:<wfm>:PT_Off", "WFMPre:<wfm>:WFId?", "WFMPre:<wfm>:XINcr",
    "WFMPre:<wfm>:XUNit", "WFMPre:<wfm>:XZEro", "WFMPre:<wfm>:YMUlt", "WFMPre:<wfm>:YOFf", "WFMPre:<wfm>:YUNit",
]  # fmt: skip
# Table 2-36 (page 2-209): set form ignored, query form generates events 100 and 420.
COMPAT_TABLE = ["WFMPre:XMUlt", "WFMPre:XOFf", "WFMPre:ZMUlt", "WFMPre:ZOFf", "WFMPre:ZUNit", "WFMPre:ZZEro"]

# Command groups that the Command Groups section limits to other series.
OTHER_SERIES_GROUPS = {
    "Counter": "Counter Commands (TBS1000B/EDU models only)",
    "Data Logging": "Data Logging Commands (Available Only On TBS1000B, TBS1000 and TDS2000C Series Models)",
    "FFT": "FFT Commands (TBS1000B/EDU models only)",
    "Limit Test": "Limit Test Commands (Available Only On TBS1000B, TBS1000 and TDS2000C Series Models)",
    "Power and Battery-Related": "Power and Battery-Related Commands (TPS2000B and TPS2000 Only)",
    "Power Measurement": "Power Measurement (TPS2000B/TPS2000 with TPS2PWR1 Power Analysis Application Key Installed Only)",
    "RS-232": "RS-232 Commands (TDS2000, TDS1000, TDS200, TPS2000B, and TPS2000 Only)",
    "Trend plot": "Trend Plot Commands (TBS1000B models only)",
    "Zoom": "Zoom Commands (TBS1000B/EDU models only)",
}  # fmt: skip


def pdf_to_lines(pdf: Path) -> list[str]:
    out = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, check=True)
    return out.stdout.decode("utf-8", errors="replace").splitlines()


def parse_index(lines: list[str]) -> tuple[int, dict[str, str]]:
    start = max(i for i, s in enumerate(lines[:-1]) if s.strip() == "Index" and "Symbols" in lines[i + 1])
    text = " ".join(lines[start:])
    index: dict[str, str] = {}
    for m in re.finditer(r"(\*?[A-Z][A-Za-z0-9:<>_\[\]]*\??),\s*(2-\d+)", text):
        hdr, page = m.group(1), m.group(2)
        # "Manual Conventions" and "WFMPre, Additional Commands for Compatibility" are topics, not headers
        if 39 <= int(page.split("-")[1]) <= 224 and hdr not in ("Compatibility", "Conventions"):
            index.setdefault(hdr, page)
    # the text layout separates this entry from its page number
    if "RS232:TRANsmit:TERMinator," in text and "RS232:TRANsmit:TERMinator" not in index:
        index["RS232:TRANsmit:TERMinator"] = "2-166"
    return start, index


def locate_blocks(lines: list[str], index_start: int, headers: list[str]) -> dict[str, dict]:
    start = [i for i, s in enumerate(lines) if s.strip() == "Manual Conventions"][-1]
    end = max(i for i in range(start, index_start) if lines[i].strip() == "Status and Events")
    positions = {}
    for hdr in headers:
        for i in range(start + 1, end):
            s = lines[i].strip()
            if s == hdr or (s.startswith(hdr + " ") and LABEL.match(s[len(hdr) :])):
                positions[hdr] = i
                break
    missing = [h for h in headers if h not in positions]
    if missing:
        raise SystemExit(f"headings not found in Command Descriptions: {missing}")
    ordered = sorted(positions.items(), key=lambda kv: kv[1])
    blocks = {}
    for n, (hdr, i) in enumerate(ordered):
        j = ordered[n + 1][1] if n + 1 < len(ordered) else end
        body = [lines[k].strip() for k in range(i + 1, j)]
        body = [t for t in body if t and not FOOT.match(t)]
        label = LABEL.match(lines[i].strip()[len(hdr) :])
        blocks[hdr] = {"label": label.group(1) if label else "", "text": " ".join(body)}
    return blocks


def field(text: str, name: str, stops: tuple[str, ...]) -> str:
    m = re.search(rf"\b{name}\b\s*(.*)", text)
    if not m:
        return ""
    rest = m.group(1)
    cut = min([rest.find(s) for s in stops if rest.find(s) >= 0] or [len(rest)])
    return rest[:cut].strip()


def query_form(hdr: str, label: str, syntax: str, text: str, known: dict[str, bool]) -> tuple[bool, str]:
    """Decide if a query form exists. The "(No Query Form)" label is not trusted on its own:
    the manual puts it on *ESE, *SRE, *PSC and *DDT, whose syntax lines show the query."""
    bare = hdr.rstrip("?")
    if hdr.endswith("?") or label == "Query Only":
        return True, "query only (heading)"
    if (bare + "?") in syntax.replace(" ?", "?"):
        return True, "query form in the syntax lines"
    if label == "No Query Form":
        return False, "no query form (heading and syntax)"
    first = text[:300]
    same = re.search(r"(?:Same as|identical to(?: the)?)\s+(\*?[A-Z][A-Za-z0-9:<>_\[\]]*)", first)
    if same:
        base = same.group(1).rstrip(".,")
        if known.get(base) or known.get(base + "?"):
            return True, f"same as {base}, which has a query form"
        if re.search(r"\bquery\b", first[same.start() : same.end() + 20]):
            return True, f"description: identical to the {base} query"
    opening = r"^(?:\([A-Za-z ]+\)\s*)?(?:Sets or queries|Sets and queries|Sets or returns|Queries|Returns(?! the oscilloscope to))"
    if re.search(opening, first) or re.search(r"\bThe query form\b", first):
        return True, "description says it queries or returns a value"
    return False, "no query form shown in syntax or description"


def applies_to_model(group: str, conditions: str) -> tuple[bool, str]:
    cond = conditions.replace("TDS1000C_EDU", MODEL)
    if cond:
        if MODEL in cond:
            return True, f"Conditions: {cond}"
        if re.search(r"\bonly\b", cond, re.IGNORECASE) or re.match(r"^(TBS|TDS|TPS)[^.]*models\.?$", cond):
            return False, f"Conditions: {cond}"
        # "NOT applicable to TBS1000B/EDU models" says nothing against this model
        if re.search(r"not applicable", cond, re.IGNORECASE) and group not in OTHER_SERIES_GROUPS:
            return True, f"Conditions: {cond}"
    if group in OTHER_SERIES_GROUPS:
        return False, f"Group: {OTHER_SERIES_GROUPS[group]}"
    return True, "no model restriction in the description or its group"


STOPS = (" Syntax", " Arguments", " Returns", " Examples", " Related Commands", " Conditions", " NOTE.", " Group")
SYNTAX_STOPS = (" Arguments", " Returns", " Examples", " Related Commands", " NOTE.", " Group ", " Status and Events")


def build(lines: list[str]) -> dict:
    index_start, index = parse_index(lines)
    headers = list(index) + EXTRA_HEADINGS
    blocks = locate_blocks(lines, index_start, headers)

    rows = []
    for hdr in headers:
        b = blocks[hdr]
        text = b["text"]
        rows.append({
            "header": hdr,
            "source": "index" if hdr in index else "description heading (not in index)",
            "page": index.get(hdr, ""),
            "label": b["label"],
            "group": field(text, "Group", STOPS)[:60],
            "syntax": field(text, "Syntax", SYNTAX_STOPS),
            "conditions": field(text, "Conditions", (" Group", " Syntax", " Arguments", " Returns", " Examples")),
            "_text": text,
        })  # fmt: skip

    # two passes so "Same as X" can see whether X has a query form
    known: dict[str, bool] = {}
    for _ in range(2):
        for r in rows:
            q, why = query_form(r["header"], r["label"], r["syntax"], r["_text"], known)
            r["query_form"], r["query_basis"] = q, why
            known[r["header"]] = q

    for r in rows:
        if not r["group"] and r["header"].startswith("WFMPre:<wfm>:"):
            r["group"] = "Waveform"  # these "Same as WFMPre:..." entries have no Group line
        ok, why = applies_to_model(r["group"], r["conditions"])
        r["applies_to_tds1000c_edu"], r["applies_basis"] = ok, why
        r["syntax"] = r["syntax"][:300]
        del r["_text"]

    for hdr in COMPAT_TABLE:
        rows.append({
            "header": hdr, "source": "Table 2-36 (not in index)", "page": "2-209", "label": "",
            "group": "Waveform", "syntax": f"{hdr} <arg>", "conditions": "",
            "query_form": True,
            "query_basis": "Table 2-36: the query form generates events 100 (Command Error) and 420 (Query Unterminated)",
            "applies_to_tds1000c_edu": True, "applies_basis": "Table 2-36 lists it for all models (compatibility only)",
        })  # fmt: skip

    return {
        "manual": "Tektronix 077044403, TBS1000/B/EDU, TDS2000/B/C, TDS1000/B/C-EDU, TDS200, TPS2000/B Series",
        "model": MODEL,
        "counts": {
            "index_entries": len(index),
            "description_headings_not_in_index": len(EXTRA_HEADINGS),
            "table_2_36": len(COMPAT_TABLE),
            "total": len(rows),
            "with_query_form": sum(r["query_form"] for r in rows),
            "applies_to_tds1000c_edu": sum(r["applies_to_tds1000c_edu"] for r in rows),
        },
        "commands": rows,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    out = Path(argv[2]) if len(argv) > 2 else ROOT / "docs" / "manual-commands.json"
    data = build(pdf_to_lines(Path(argv[1])))
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(data["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

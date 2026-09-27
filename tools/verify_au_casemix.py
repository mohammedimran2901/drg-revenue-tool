#!/usr/bin/env python3
"""Verify the Australian per-DRG casemix values in the DRG Revenue Focus Tool.

WHAT IS BEING VERIFIED
----------------------
The tool stores one Australian "minor share" per AR-DRG base code:

    BENCH.per_drg["<DRG>"]["Australia (AIHW AR-DRG v9.0 cube, 2019-20)"] = <0..1>

Claimed method: for each DRG base code, take every complexity split the AIHW
publishes (A = Major, B = Intermediate, C = Minor), sum the separations, and

    AU minor share = (all non-Major splits) / (all splits)

i.e. a genuine "% of cases that are Major vs Minor" for that exact DRG - not a
chapter average, not a modelled assumption.

Source: AIHW AR-DRG v9.0 data cube, 2019-20 (sheet "DRG Counts Summary"),
National Hospital Morbidity Database, all public and private Australian
hospitals, acute care.
https://www.aihw.gov.au/reports/hospitals/ar-drg-data-cubes/contents/summary

USAGE
-----
    python3 tools/verify_au_casemix.py                       # spot checks only
    python3 tools/verify_au_casemix.py --cube <file.xlsx>    # FULL check, all DRGs

The AIHW site sits behind a bot check, so the cube cannot be fetched
unattended - download it once and pass --cube to re-derive every stored value.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_HTML = HERE.parent / "drg-revenue-tool-offline.html"

TOLERANCE = 0.0006  # stored values are the exact ratio; allow 4dp rounding only

# DRG -> {split code: separations} exactly as published in the AIHW 2019-20 cube.
# Kept deliberately small; --cube re-derives the full 306 automatically.
SPOT_CHECK = {
    "X64": {"X64A": 2428, "X64B": 3563, "X64C": 7726},   # Major / Interm / Minor
    "X61": {"X61A": 1698, "X61B": 11167},
    "X62": {"X62A": 13413, "X62B": 24425},
    "X60": {"X60A": 19018, "X60B": 57817},
    "Z01": {"Z01A": 1313, "Z01B": 13071},
    "Z64": {"Z64A": 11454, "Z64B": 115364},
    "Y03": {"Y03A": 459, "Y03B": 1505},
    "W61": {"W61A": 1188, "W61B": 1189},
}

# The Major (highest complexity) tier. AR-DRG v9.0 orders a family's splits
# A (most complex) -> B -> C -> D.
MAJOR_LETTER = "A"


def load_tool_values(html_path: Path) -> dict[str, float]:
    """Pull BENCH.per_drg out of the single-file tool."""
    src = html_path.read_text(encoding="utf-8")
    m = re.search(r"const BENCH = (\{.*?\});\n", src, re.S)
    if not m:
        sys.exit(f"could not locate BENCH in {html_path}")
    per_drg = (json.loads(m.group(1)).get("per_drg")) or {}
    return {k: float(next(iter(v.values()))) for k, v in per_drg.items()}


def minor_share(splits: dict[str, int]) -> float:
    """(all non-Major splits) / (all splits)."""
    total = sum(splits.values())
    major = sum(n for code, n in splits.items() if code[-1].upper() == MAJOR_LETTER)
    return (total - major) / total if total else 0.0


def run_spot_checks(tool: dict[str, float]) -> bool:
    print("SPOT CHECKS - recomputed from published AIHW separation counts")
    print("-" * 96)
    print(f"{'DRG':<6}{'AIHW splits':<46}{'expected':>10}{'stored':>10}{'delta':>11}   ok")
    print("-" * 96)
    all_ok = True
    for drg, splits in SPOT_CHECK.items():
        exp = minor_share(splits)
        stored = tool.get(drg)
        ok = stored is not None and abs(stored - exp) <= TOLERANCE
        all_ok &= ok
        label = " + ".join(f"{c} {n:,}" for c, n in splits.items())
        stored_s = "MISSING" if stored is None else f"{stored:.4f}"
        delta = "-" if stored is None else f"{stored - exp:+.4f}"
        print(f"{drg:<6}{label:<46}{exp:>10.4f}{stored_s:>10}{delta:>11}   {'OK' if ok else 'FAIL'}")
    print("-" * 96)
    print("ALL SPOT CHECKS PASS" if all_ok else "SPOT CHECK FAILURES PRESENT")
    return all_ok


def run_full_check(tool: dict[str, float], cube_path: Path) -> bool:
    """Re-derive every stored value from the downloaded AIHW cube."""
    try:
        import openpyxl
    except ImportError:
        sys.exit("full check needs openpyxl:  pip install openpyxl")

    wb = openpyxl.load_workbook(cube_path, read_only=True, data_only=True)
    sheet = next((wb[n] for n in wb.sheetnames if "summary" in n.lower()), None)
    if sheet is None:
        sys.exit(f"no 'DRG Counts Summary' sheet in {cube_path}: {wb.sheetnames}")

    row_re = re.compile(r"^([A-Z0-9]{3})([A-Z])\s")
    splits: dict[str, dict[str, int]] = {}
    for row in sheet.iter_rows(values_only=True):
        cells = [c for c in row if c not in (None, "")]
        if not cells:
            continue
        m = row_re.match(str(cells[0]).strip())
        if not m:
            continue                                  # MDC / partition / n.p. rows
        nums = [c for c in cells[1:] if isinstance(c, (int, float))]
        if not nums:
            continue
        base, letter = m.group(1), m.group(2)
        splits.setdefault(base, {})[base + letter] = int(nums[0])

    checked = mismatched = unevidenced = 0
    bad: list[tuple[str, float, float]] = []
    for base, s in sorted(splits.items()):
        exp = minor_share(s)
        stored = tool.get(base)
        if stored is None:
            unevidenced += 1
            continue
        checked += 1
        if abs(stored - exp) > TOLERANCE:
            mismatched += 1
            bad.append((base, exp, stored))

    print(f"\nFULL CHECK against {cube_path.name}")
    print("-" * 96)
    print(f"DRG families parsed from cube : {len(splits)}")
    print(f"matched to a stored tool value: {checked}")
    print(f"in cube but not stored        : {unevidenced}")
    print(f"mismatches beyond {TOLERANCE} : {mismatched}")
    if bad:
        print("\nMISMATCHES (drg, expected, stored, delta):")
        for base, exp, stored in bad[:40]:
            print(f"  {base}  expected {exp:.4f}  stored {stored:.4f}  delta {stored - exp:+.4f}")
        if len(bad) > 40:
            print(f"  ... and {len(bad) - 40} more")
    print("-" * 96)
    print("FULL CHECK PASS" if mismatched == 0 else "FULL CHECK FAILED")
    return mismatched == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML, help="path to the single-file tool")
    ap.add_argument("--cube", type=Path, help="downloaded AIHW AR-DRG v9.0 2019-20 cube (.xlsx) for a full check")
    args = ap.parse_args()

    if not args.html.exists():
        sys.exit(f"tool not found: {args.html}")
    tool = load_tool_values(args.html)
    print(f"tool            : {args.html}")
    print(f"stored AU values: {len(tool)} per-DRG\n")

    ok = run_spot_checks(tool)
    if args.cube:
        if not args.cube.exists():
            sys.exit(f"cube not found: {args.cube}")
        ok = run_full_check(tool, args.cube) and ok
    else:
        print("\n(full 306-row check skipped - pass --cube <aihw AR-DRG cube.xlsx> to run it)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

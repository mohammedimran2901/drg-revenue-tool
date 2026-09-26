#!/usr/bin/env python3
"""
extract_nhs_apc.py — step 1 of the UK casemix build.

Reads the "APC" (Admitted Patient Care) sheet from the NHS England National
Schedule of NHS Costs workbook and writes a flat HRG-level file that
build_uk_casemix.py consumes.

    python3 extract_nhs_apc.py 2-National-schedule-of-NHS-costs-FY21-22-v4.xlsx /tmp/nhs_hrg.csv
    NHS_HRG_CSV=/tmp/nhs_hrg.csv python3 build_uk_casemix.py

Output columns: hrg, fce, total_cost, unit_cost, desc
  hrg       HRG4+ currency code (5 chars), e.g. HN12A
  fce       Finished Consultant Episodes (national activity)
  unit_cost total_cost / fce
  desc      NHS currency description, which carries the complexity wording
"""
import csv, sys, os

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/nhs_hrg.csv"
    try:
        import openpyxl
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    ws = wb["APC"]
    agg = {}
    for r in ws.iter_rows(min_row=6, values_only=True):
        code = r[2]
        if not code or not isinstance(code, str) or len(code) < 5:
            continue
        desc = (r[3] or "")
        try:
            fce = int(float(str(r[4]).replace(",", "")))
        except (TypeError, ValueError):
            fce = 0                      # "*" = NHS suppression, treated as 0
        try:
            uc = float(r[5])
        except (TypeError, ValueError):
            uc = 0.0
        try:
            tc = float(r[6])
        except (TypeError, ValueError):
            tc = 0.0
        a = agg.setdefault(code, {"fce": 0, "cost": 0.0, "desc": desc.strip()})
        a["fce"] += fce
        a["cost"] += tc if tc else uc * fce      # one row per admission type
        if desc.strip():
            a["desc"] = desc.strip()
    with open(out, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["hrg", "fce", "total_cost", "unit_cost", "desc"])
        for c, a in sorted(agg.items()):
            wr.writerow([c, a["fce"], round(a["cost"], 2),
                         round(a["cost"] / a["fce"], 2) if a["fce"] else 0, a["desc"]])
    print("wrote %s | %d HRG4+ codes | %s FCE" %
          (out, len(agg), format(sum(a["fce"] for a in agg.values()), ",")))
    print("NOTE: rows with suppressed activity ('*') are treated as zero, so totals "
          "slightly under-state NHS activity — the published national totals do the same.")

if __name__ == "__main__":
    main()
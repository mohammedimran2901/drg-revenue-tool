#!/usr/bin/env python3
"""
build_uk_casemix.py — real UK (NHS) casemix extract for the DRG Revenue Focus Tool.

SOURCE
  NHS England, National Schedule of NHS Costs FY2021/22 (v4), sheet "APC"
  (Admitted Patient Care):
      2-National-schedule-of-NHS-costs-FY21-22-v4.xlsx
  Columns used: Currency Code (= HRG4+ code), Currency Description,
                Number of FCEs, National Average Unit Cost, Total Costs.
  Sanity check: ~16.9m FCEs across 2,568 HRG4+ codes — the right order of
  magnitude for NHS admitted patient care in one financial year.

WHAT IT PRODUCES
  For every HRG4+ chapter and every AR-DRG MDC chapter: real UK activity (FCE),
  a Low/Medium/High complexity split, and the real UK "lower-complexity share"
  (the NHS analogue of the tool's `minor share`) so the tool's assumed UK
  chapter anchors can be audited against actual NHS data.

COMPLEXITY RULE (three tiers, priority order; documented, no invention)
  1. EXPLICIT — the HRG4+ description states the complexity, e.g.
                "Very Major Hip Procedures" ... "Minimal Hip Procedures".
                Very Major / Major -> High; Intermediate -> Medium;
                Minor / Minimal -> Low.   (NHS's own wording.)
  2. CC SCORE — medical HRGs split on a complication/comorbidity score, e.g.
                "with CC Score 10+" down to "CC Score 0-1". Within one HRG stem
                the lowest max-CC split is Low and the highest is High; middles
                are Medium.
  3. COST     — remaining codes banded by FCE-weighted unit-cost tertiles
                within their chapter.
  Each row records its `basis`; each chapter records the activity share resolved
  by each rule, so the consumer can judge NHS wording vs derived proxy.

BOUNDARY (stated, not hidden)
  HRG4+ is a different grouper to AR-DRG v9.0 and there is no official crosswalk,
  so CHAPTER_TO_MDC is body-system (MDC) level only. It is NOT per-DRG: several
  AR-DRGs share one chapter figure.
"""

import csv, json, re, collections, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("NHS_HRG_CSV", "/tmp/nhs_hrg.csv")   # hrg,fce,total_cost,unit_cost,desc
OUT = os.path.join(HERE, "uk-casemix.json")

# ---- HRG4+ chapter -> AR-DRG MDC (chapter/body-system level only) -------------
# NOTE: MDC letters follow THIS TOOL'S price-table convention (T=Infectious,
# U=Mental health, X=Injuries, Y=Burns, Z=Other health contacts), not the
# textbook AR-DRG letters, so the panel lines up with the DRGs actually loaded.
CHAPTER_TO_MDC = {
    "AA": "B",   # Nervous system procedures / disorders
    "AB": "B",   # Epidural & image-guided pain management
    "HC": "B",   # Spinal conditions and procedures
    "PR": "B",   # Paediatric febrile convulsions / epilepsy
    "BZ": "C",   # Ophthalmology
    "PP": "C",   # Paediatric ophthalmology
    "CA": "D",   # Mouth, head and neck procedures
    "CB": "D",   # Non-malignant ENT / neck
    "CD": "D",   # Dental extraction & oral surgery
    "PC": "D",   # Paediatric head, neck and ear
    "DZ": "E",   # Respiratory disorders
    "PD": "E",   # Paediatric respiratory
    "PF": "E",   # Paediatric respiratory infection
    "YD": "E",   # Percutaneous lung / mediastinal procedures
    "EB": "F",   # Cardiac disorders
    "ED": "F",   # Cardiac surgery (CABG)
    "EC": "F",   # Congenital cardiac procedures
    "EY": "F",   # Cardiac catheterisation / pacemaker / angioplasty
    "YA": "F",   # Percutaneous transluminal vascular procedures
    "PE": "F",   # Paediatric cardiac conditions
    "YQ": "F",   # Peripheral vascular disorders
    "FD": "G",   # Gastrointestinal tract disorders
    "FE": "G",   # Diagnostic & therapeutic endoscopy (upper GI / colonoscopy)
    "FF": "G",   # General abdominal / anal procedures
    "GA": "H",   # Hepatobiliary & pancreatic procedures
    "GB": "H",   # Endoscopic retrograde & hepatobiliary endoscopy
    "GC": "H",   # Hepatobiliary & pancreatic disorders
    "YG": "H",   # Percutaneous liver / biliary procedures
    "PG": "H",   # Paediatric hepatobiliary & pancreatic
    "HD": "I",   # Inflammatory spine, joint & connective tissue disorders
    "HN": "I",   # Hip, knee & other joint procedures
    "HT": "I",   # Trauma orthopaedic procedures
    "YH": "I",   # Percutaneous joint / bone procedures
    "PH": "I",   # Paediatric musculoskeletal
    "JA": "J",   # Breast procedures
    "JB": "Y",   # Burns
    "JC": "J",   # Skin procedures
    "JD": "J",   # Skin disorders
    "YJ": "J",   # Breast biopsy / excision
    "PJ": "J",   # Paediatric skin
    "KA": "K",   # Thyroid & other endocrine procedures
    "KB": "K",   # Diabetes & hyperglycaemic disorders
    "KC": "K",   # Metabolic & electrolyte disorders
    "PK": "K",   # Paediatric endocrine
    "LA": "L",   # Kidney & urinary tract infections / disorders
    "LB": "L",   # Bladder & urinary procedures
    "YL": "L",   # Percutaneous renal / ureteric procedures
    "PL": "L",   # Paediatric renal
    "MA": "N",   # Female reproductive tract procedures
    "MB": "N",   # Miscarriage / threatened miscarriage
    "MC": "N",   # Assisted reproduction
    "NZ": "O",   # Ante-natal, delivery and post-partum
    "PB": "P",   # Neonatal diagnoses
    "SA": "Q",   # Blood disorders & transfusions
    "SB": "Q",   # Same-day chemotherapy (haematology)
    "SC": "Q",   # Same-day radiotherapy (haematology)
    "PN": "Q",   # Paediatric blood cell disorders
    "PQ": "Q",   # Paediatric disorders of immunity
    "PM": "R",   # Paediatric neoplasm
    "DX": "T",   # COVID-19 infection
    "WJ": "T",   # Infectious diseases / sepsis
    "PW": "T",   # Paediatric infections
    "WD": "U",   # Specialist mental health
    "PT": "U",   # Paediatric behavioural disorders
    "VA": "W",   # Multiple significant trauma
    "HE": "X",   # Hip fracture (injury)
    "PV": "X",   # Paediatric minor injury
    "WH": "Z",   # Procedure not carried out / other health contacts
    "PX": "Z",   # Paediatric examination / follow-up / special screening
    "RD": "Z",   # Diagnostic imaging admissions
    "RN": "Z",   # Nuclear medicine admissions
}

# HRG4+ chapters deliberately NOT mapped (no defensible AR-DRG MDC equivalent)
UNMAPPED = {
    "UZ": "Data invalid for grouping",
    "YR": "Central venous catheter care (cross-cutting, no MDC)",
    "YF": "Percutaneous abdominal cavity drainage (cross-cutting, no MDC)",
    "YC": "Image-guided neck biopsy (cross-cutting, no MDC)",
}

TIER_WORD = [
    ("High",   re.compile(r"very\s+major", re.I)),
    ("High",   re.compile(r"\bmajor\b",    re.I)),
    ("Medium", re.compile(r"intermediate", re.I)),
    ("Low",    re.compile(r"\bminimal\b",  re.I)),
    ("Low",    re.compile(r"\bminor\b",    re.I)),
]
CC_RE = re.compile(r"cc\s*score\s*(\d+)\s*(?:\+|-\s*(\d+))?", re.I)

def explicit_tier(desc):
    for name, rx in TIER_WORD:
        if rx.search(desc):
            return name
    return None

def max_cc(desc):
    m = CC_RE.search(desc)
    if not m:
        return None
    return int(m.group(2)) if m.group(2) else int(m.group(1))

def load(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            code = (r.get("hrg") or "").strip().upper()
            if len(code) < 5:
                continue
            rows.append({
                "hrg": code, "stem": code[:4], "chap": code[:2],
                "fce": int(float(r.get("fce") or 0)),
                "uc": float(r.get("unit_cost") or 0),
                "desc": (r.get("desc") or "").strip(),
                "cc": max_cc(r.get("desc") or ""),
            })
    return rows

def assign_tiers(rows):
    # 1. explicit NHS wording
    for r in rows:
        t = explicit_tier(r["desc"])
        r["tier"] = t
        r["basis"] = "explicit" if t else None
    # 2. CC-score ladder within each HRG stem
    stems = collections.defaultdict(list)
    for r in rows:
        stems[r["stem"]].append(r)
    for grp in stems.values():
        todo = [r for r in grp if r["tier"] is None and r["cc"] is not None]
        if not todo:
            continue
        if len(todo) == 1:
            todo[0]["tier"] = "Medium"; todo[0]["basis"] = "cc"; continue
        srt = sorted(todo, key=lambda r: r["cc"])
        srt[0]["tier"]  = "Low";  srt[0]["basis"]  = "cc"
        srt[-1]["tier"] = "High"; srt[-1]["basis"] = "cc"
        for r in srt[1:-1]:
            r["tier"] = "Medium"; r["basis"] = "cc"
    # 3. unit-cost tertiles within chapter
    bychap = collections.defaultdict(list)
    for r in rows:
        bychap[r["chap"]].append(r)
    for grp in bychap.values():
        todo = [r for r in grp if r["tier"] is None]
        if not todo:
            continue
        todo.sort(key=lambda r: r["uc"])
        n = len(todo)
        for i, r in enumerate(todo):
            p = (i + 0.5) / n
            r["tier"] = "Low" if p <= 1/3 else ("High" if p > 2/3 else "Medium")
            r["basis"] = "cost"
    return rows

def main():
    if not os.path.exists(SRC):
        sys.exit("missing %s — extract it from the NHS APC sheet first" % SRC)
    rows = assign_tiers(load(SRC))
    tot = sum(r["fce"] for r in rows)

    bychap = collections.defaultdict(list)
    for r in rows:
        bychap[r["chap"]].append(r)
    chapters = {}
    for chap, grp in bychap.items():
        f = sum(r["fce"] for r in grp)
        tiers = collections.Counter()
        basis = collections.Counter()
        for r in grp:
            tiers[r["tier"]] += r["fce"]
            basis[r["basis"]] += r["fce"]
        top = max(grp, key=lambda r: r["fce"])
        chapters[chap] = {
            "fce": f,
            "codes": len(grp),
            "mdc": CHAPTER_TO_MDC.get(chap),
            "exemplar": top["desc"][:70],
            "low": tiers["Low"], "medium": tiers["Medium"], "high": tiers["High"],
            "lowShare": round(tiers["Low"] / f, 4) if f else None,
            "basis": {k: round(v / f, 4) for k, v in basis.items() if f},
        }

    mdcs = {}
    for ch, e in chapters.items():
        if not e["mdc"]:
            continue
        m = mdcs.setdefault(e["mdc"], {"fce": 0, "low": 0, "medium": 0, "high": 0, "chapters": []})
        m["fce"] += e["fce"]; m["low"] += e["low"]
        m["medium"] += e["medium"]; m["high"] += e["high"]
        m["chapters"].append(ch)
    for e in mdcs.values():
        f = e["fce"]
        e["lowShare"] = round(e["low"] / f, 4) if f else None
        e["highShare"] = round(e["high"] / f, 4) if f else None
        e["chapters"].sort()

    mapped = sum(e["fce"] for e in mdcs.values())
    payload = {
        "source": {
            "dataset": "NHS England National Schedule of NHS Costs, FY2021/22 (v4), sheet APC",
            "file": "2-National-schedule-of-NHS-costs-FY21-22-v4.xlsx",
            "grouping": "HRG4+ chapters mapped to AR-DRG MDC at chapter (body-system) level only",
            "note": ("HRG4+ is a different grouper to AR-DRG v9.0 and there is no official "
                     "HRG4+->AR-DRG crosswalk. Mapping is MDC-level; several AR-DRGs share "
                     "one chapter figure. This is NOT a per-DRG equivalence."),
        },
        "totals": {
            "fce": tot, "codes": len(rows),
            "mappedFce": mapped, "mappedPct": round(mapped / tot, 4),
            "tierBasis": {k: round(sum(r["fce"] for r in rows if r["basis"] == k) / tot, 4)
                          for k in ("explicit", "cc", "cost")},
            "unmapped": UNMAPPED,
        },
        "mdc": mdcs,
        "chapter": chapters,
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
    print("wrote", OUT)
    print("FCE total %s | mapped %.1f%% | tier basis %s" % (
        format(tot, ","), 100 * payload["totals"]["mappedPct"],
        payload["totals"]["tierBasis"]))
    print("\n%-4s %10s %6s %6s %6s  %s" % ("MDC", "FCE", "low%", "med%", "high%", "chapters"))
    for m, e in sorted(mdcs.items(), key=lambda kv: -kv[1]["fce"]):
        f = e["fce"]
        print("%-4s %10s %5.0f %6.0f %6.0f  %s" % (
            m, format(f, ","), 100*e["low"]/f, 100*e["medium"]/f, 100*e["high"]/f,
            ",".join(e["chapters"])))

if __name__ == "__main__":
    main()
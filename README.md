# DRG Revenue Focus Tool — Saudi Arabia

A single-file, **100% offline** tool for estimating **missed insured revenue** from
minor/major DRG complexity miscategorisation in Saudi inpatient care, benchmarked
against leading casemix systems.

Open `drg-revenue-tool-offline.html` by double-clicking it — no server, no build,
no internet required (SheetJS is embedded for `.xlsx` uploads).

---

## What it does

1. Loads the **CHI AR-DRG v9.0 price table** (309 DRG groups: minor SAR, major SAR,
   uplift, DARS activity, insured claims activity).
2. Lets you upload a patient-level extract (CSV / tab-delimited / XLSX) with a
   facility column, a DRG column and (optionally) a Minor/Major complexity column.
   The extract should be **one row per insured patient** — filter out uninsured
   cases before upload, because every figure in the tool is an insured-only figure.
3. Aggregates the upload to **per-DRG observed minor shares** (the "current state").
4. Compares those against **five benchmarks** and reports the **missed revenue** —
   the additional insured income if IP encounters were categorised as in the
   benchmark and billed at the CHI AR-DRG tariff.

---

## The core calculation

```
observed minor share  = uploaded file aggregated to DRG level (peer)
                        else KSA CHI baseline (fallback when no file is loaded)

gap                   = max(0, observed minor share − benchmark minor share)
missed revenue (SAR)  = gap × insured cases × DRG tariff uplift (major − minor)

money at stake (SAR)  = uplift × insured cases   [ceiling: every minor → major]
```

A positive `gap` means the DRG is **under-reporting majors** (too many minors vs the
benchmark) → missed insured income. Everything is computed on **insured cases only**
(claims activity), because only insured cases generate claimable revenue.

---

## Benchmarks

| Benchmark | Granularity | Source | Role |
|---|---|---|---|
| **UK** | per-DRG (**calibrated**, not observed) | UK chapter anchors × AIHW within-chapter pattern; genuine NHS activity shown separately (NCC FY2021/22, HRG4+) | **Headline / primary** |
| **Australia AIHW** | per-DRG (306/309) | AIHW AR-DRG v9.0 data cube 2019–20 | Structural anchor (like-for-like grouper) |
| **UAE DoH Abu Dhabi** | chapter level | DoH IR-DRG 3.01 / Shafafiya | Regional peer |
| **KSA CHI baseline** | chapter level | CHI DRG baseline assumptions | Current-state fallback |
| **Peer median** | per-DRG | Aggregated from your uploaded file | Self-benchmark |

Every value carries a **granularity badge** and **evidence badge** so a
chapter-level figure is never mistaken for a like-for-like per-DRG figure.

### UK per-DRG method (calibration)

NHS England publishes the UK anchor at **chapter** level because HRG4+ is a different
grouping to AR-DRG, so there is no direct per-DRG NHS value. The tool gives every DRG
a UK figure by:

1. anchoring to the **UK chapter mean** (NHS NCC 2023/24, HRG4+), then
2. applying the **evidenced within-chapter relative pattern** from the AIHW AR-DRG
   v9.0 cube (the like-for-like grouper), activity-weighted.

Chapter totals are preserved (approximately to exactly), and the result is labelled
**"UK-calibrated"** everywhere it appears. A future upgrade can replace this with a
true HRG4+ → AR-DRG crosswalk derived from the National Cost Collection.

> **Important:** the UK per-DRG column is **arithmetic on Australian data**, not NHS
> per-DRG data. Anything quoted from it externally should say so.

### Real UK casemix

Separately from the calibration, the tool carries **real NHS activity**, so the UK
anchor can be audited rather than assumed:

- **16,927,227 FCEs** across **2,568 HRG4+ codes** — NHS England National Schedule of
  NHS Costs FY2021/22 (v4), sheet "APC" — mapped to **22 body-system chapters**
  (98.3% of activity; HRG4+ chapters with no AR-DRG equivalent are left unmapped).
- A real **Low / Medium / High** complexity split, banded in priority order by:
  1. NHS's own wording in the HRG description ("Very Major"…"Minimal") — 15% of activity;
  2. the **CC-score** complication/comorbidity ladder — 61%;
  3. unit-cost tertile within the chapter — 24%.
- Displayed in **DRG Chapters & Benchmarks → "Real UK casemix"**, next to the chapter
  anchor the tool assumes, with the difference flagged where it is large.

Reproduce it:

```bash
cd tools
python3 extract_nhs_apc.py 2-National-schedule-of-NHS-costs-FY21-22-v4.xlsx /tmp/nhs_hrg.csv
NHS_HRG_CSV=/tmp/nhs_hrg.csv python3 build_uk_casemix.py      # writes uk-casemix.json
```

> **What this surfaced.** The UK chapter anchors the tool assumes diverge from the real
> NHS-derived low-complexity share by up to **43 percentage points** — Newborns assumed
> 52% low vs **24%** actual, Infectious 42% vs **20%**, Respiratory 38% vs **19%**,
> Pregnancy 52% vs **38%**. The direction is mostly **conservative** (the tool over-states
> the low tier, so missed revenue is more likely understated than overstated), but the
> anchors are **not traceable to NHS data** and should be re-derived before any figure is
> quoted externally. Note also that the tool's two-way Minor/Major split and the NHS
> three-way Low/Medium/High split are **not identical constructs**, so the comparison is
> indicative rather than a like-for-like recalibration.

---

## Why Australia is the best DRG comparison for Saudi Arabia

- Saudi Arabia adopted **ICD-10-AM 10th Edition + AR-DRG v9.0** (Saudi Health Council);
  CHI mandated AR-DRG for Article 11 provision from 2021, and it is the sole
  admitted-care patient classification system.
- CHI's own correlation analysis scored the KSA price list at **0.96** against
  **Australian AR-DRG v9.0 2019/20** (and 0.92 vs UAE IR-DRG 3.01).
- Same grouper + same MINC/MAJC complexity logic ⇒ complexity splits are genuinely
  like-for-like.

**UK** is kept as the headline because it is a mature, transparent, single-payer
activity-based system — the best "what good looks like" reference — but it is a
*different grouping*, so its granularity is always labelled.

---

## Tabs

- **📤 Outputs — DRG opportunities** (default): missed-revenue headline, KPIs,
  per-DRG table (benchmark target, gap pp, direction, missed revenue, per-1% shift),
  compare-all-benchmarks view, and CSV / Excel exports.
- **🎯 Biggest Bank for Buck** — top-10 DRGs by money at stake.
- **🏥 Facility Targeting** — upload, column mapping, facility league table.
- **Full Ranking** — sortable DRG league table.
- **DRG Chapters & Benchmarks** — per-chapter breakdown with all benchmark columns,
  a **Real UK casemix** panel (actual NHS episodes + Low/Medium/High split per chapter,
  vs the anchor the tool assumes) and the source audit trail.
- **Simulator** — shift-X%-of-minors-to-majors revenue simulation.

## Exports

`CSV (all benchmarks)`, `Excel (all benchmarks)`, `UK benchmark only (CSV)` — each
with a metadata header (version, formula, benchmark versions, method, caveat) and a
per-DRG `Direction` column.

---

## Hosting / deployment

The tool is a plain static file, so any static host works. This repo ships:

- `drg-revenue-tool-offline.html` — the tool itself
- `index.html` — redirects `/` to the tool (fallback for any host)
- `vercel.json` — clean-URL rewrite for `/` and `noindex` headers

### Option A — Vercel (one-click, auto-deploys on every push)

1. Go to <https://vercel.com/new> (signed in as the **same GitHub account**).
2. **Import Git Repository** → `mohammedimran2901/drg-revenue-tool`.
3. Framework preset: **Other**. Build command / output directory: leave **blank**.
4. **Deploy**. Vercel serves it at `https://drg-revenue-tool.vercel.app`.

Every `git push` to `main` then redeploys automatically.

### Option B — CLI

```bash
npx vercel --prod          # first run asks you to log in
```

### Option C — offline distribution

Just share `drg-revenue-tool-offline.html`; it runs by double-clicking, with no
server and no internet.

> **Access note:** a `*.vercel.app` URL is publicly reachable unless you enable
> deployment protection. The file embeds the CHI AR-DRG price table and aggregate
> DARS/claims activity, so use Vercel Authentication / password protection (Pro) if
> the link must be restricted to the team.

---

## Version

**v2.5** (2026-09-26) · Price table: AR-DRG v9.0 (CHI).

> For internal revenue-strategy use. UK per-DRG values are a **calibration over
> Australian data**, not NHS per-DRG data; real NHS activity and complexity are shown
> separately in the "Real UK casemix" panel. UAE/KSA values are chapter-anchored
> assumptions; Australia AIHW is the only true per-DRG evidenced source. Observed shares
> default to the KSA CHI baseline until a patient file is uploaded.
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
| **UK** | **per-DRG (UK-calibrated)** | NHS England National Cost Collection 2023/24 (HRG4+) + HES APC | **Headline / primary** |
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
- **DRG Chapters & Benchmarks** — per-chapter breakdown with all benchmark columns
  and the source audit trail.
- **Simulator** — shift-X%-of-minors-to-majors revenue simulation.

## Exports

`CSV (all benchmarks)`, `Excel (all benchmarks)`, `UK benchmark only (CSV)` — each
with a metadata header (version, formula, benchmark versions, method, caveat) and a
per-DRG `Direction` column.

---

## Version

**v2.4** (2026-09-26) · Price table: AR-DRG v9.0 (CHI).

> For internal revenue-strategy use. UK/UAE/KSA values are chapter-anchored
> (UK is per-DRG calibrated); Australia AIHW is per-DRG evidenced. Observed shares
> default to the KSA CHI baseline until a patient file is uploaded.
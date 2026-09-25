# Bartik Reconciliation Summary
### For the original panel-data-study / paper-writing project

**Purpose of this document:** this is the single bridge between the
Python panel-building project (retail/claimants/population/PAYE/SSSC
assembly, Bartik validation) and this project's do-file/paper work.
It exists so questions like "does this look right compared to the
Python side" can be answered directly here, without switching chats.

**Companion file:** `bartik_check.py` — the actual validation script.
Everything below is a plain-language summary of what it checks and
what it found. If a question needs more detail than this document
has, the build project's `README.md` and `README.SCOT` have full
history; ask there rather than guessing here.

---

## 1. What bartik_check.py does

Replicates the do-file's Bartik IV construction and main analysis in
Python, as a pipeline validation step before/alongside Stata. Same
instrument logic: 2016 baseline discount-chain share (Aldi/Lidl vs.
incumbents) × leave-one-out national growth. Sections:

1. Bartik instrument construction
2. First-stage diagnostics
3. Main IV outcomes — **LA level** (148 English LAs)
4. Regional-level check (9 English regions) — see caveats below
5. Summary comparison vs. paper benchmarks

## 2. Confirmed matches to the do-file (Section 3, LA level)

| Outcome | Python | Do-file benchmark | Match? |
|---|---|---|---|
| First-stage F | 30.84 | ~43 | Same direction, both strong (>16.38 Stock-Yogo) |
| Vacant posts | β=13.27, p=0.442 | β=1.85, p=0.885 | Both null ✓ |
| Vacancy rate | β=0.131, p=0.257 | β=0.164, p=0.254 | Both null ✓ |
| Employees | β=1.58, p=0.963 | β=-4.77, p=0.850 | Both null ✓ |
| Benefit rate (Dec) | β=-1.057, p=0.001 | β=-0.495, p=0.040 | Same direction, both significant ✓ (magnitude ~2x — see open note below) |

Minor known differences: pop_65plus vs paper's pop_60; 148 vs 150
upper-tier LAs; retail counts ~20% higher (same national total, fewer
larger upper-tier units — see build project's RETAIL_METHODOLOGY_NOTE.md).
None of these affect direction or significance.

**Open item, not yet resolved:** the December benefit-rate coefficient
is directionally and statistically consistent with the do-file, but
roughly double the magnitude (-1.057 vs -0.495). Possible contributors
flagged but not confirmed: the retail-count inflation noted above could
be scaling up the effective "dose" of retail exposure. Worth checking
whether it narrows if restricted to the ~145 LAs that name-match
cleanly against the do-file's own panel (excludes the 3 combined-split
LAs: Cumbria, Dorset, Northamptonshire).

## 3. December vs. annual benefit claims — genuinely new finding, fold into the paper

The Python pipeline built **two** claimant measures where the do-file
(and the original paper) uses only one:

- **claimants_december** — December snapshot, matches the do-file exactly
- **claimants_annual** — annual mean, not in the original paper

Results:
- **December: β=-1.057, p=0.001** (negative, significant — matches do-file direction)
- **Annual: β=+0.632, p<0.001** (positive, significant — opposite sign)

**Interpretation, worth stating explicitly in the paper:** the
December effect is a **seasonal** effect — retail's Christmas hiring
peak temporarily reduces claimants. The annual mean shows the opposite:
no lasting reduction, if anything a small increase. Consistent with
overseas workers filling *permanent* retail roles while UK claimants
benefit only during the seasonal peak. This is a genuinely more
complete story than a single point-in-time snapshot can tell, and
directly explains why the do-file's December-only result, while
correct, is narrower than it might first appear.

## 4. Scotland comparison (new since the do-file — no do-file equivalent exists)

Built as an extension, not a replication — the do-file has no Scotland
component. Validated Scotland-specific Bartik instrument (29 councils,
3 remote islands excluded on structural grounds — parallel to the
do-file's own City of London/Scilly exclusion; F=26.63, well above
Stock-Yogo).

| Outcome | Scotland | England (this project's benchmark) |
|---|---|---|
| Vacancy rate | β=0.085, p=0.422 | β=0.131, p=0.257 (both null — **replicates**) |
| Benefit rate (Dec) | β=-0.052, p=0.846 | β=-1.057, p=0.001 (**does NOT replicate**) |
| Benefit rate (annual) | β=0.086, p=0.648 | β=+0.632, p<0.001 (**does NOT replicate**) |

**Key finding for the paper:** the vacancy null holds across both
nations — genuine cross-national agreement that retail expansion
doesn't create care-sector shortages anywhere in the UK. The benefit-
claims effect, however, is England-specific — Scotland's coefficients
aren't just noisier versions of England's, they're close to zero
outright (an order of magnitude smaller), on a solid first stage
(F=26.63, not a weak-instrument artefact). Tentative explanation:
Scotland's retail incumbent landscape is Co-op-dominated (~31.8% of
major retail footprint vs ~22% in England) rather than driven by a
few national chains — a structurally different competitive
environment that may not displace workers into new roles the same way.

**Important scope caveat:** Scotland's vacancy measure (SSSC) covers
ALL social services (children, young people, adults, older people) —
not adult-only like England's Skills for Care data. No LA-level
age-group breakdown exists in the Scottish source, so this can't be
narrowed. State this explicitly wherever the two nations are compared.

## 5. Regional-level analysis (Section 4) — caveats, not a headline result

9 English regions, single first-stage Bartik + region FE + PAYE
overseas share (contemporaneous) in the second stage. All outcomes
null, F=12.53. **Do not present this as a finding on its own** — 9
clusters with more stage-2 parameters than clusters is a scoping
exercise, not reliable inference. Relevant mainly for the discussion-
section point below.

## 6. Discussion-section material worth using directly

**A. Sub-sector mechanism (descriptive, from SSSC "reasons" tables,
not a regression result):** "Competition from other types of work" —
the category capturing loss of candidates to alternative employment —
is reported at roughly double the sector average by care-at-home and
housing-support roles (the lowest-paid, most retail-comparable roles),
and near/below average by nursing and other skilled roles. Consistent
with a substitution mechanism concentrated in specific low-wage roles,
sitting underneath the aggregate null vacancy result. National-level
only, no LA cross-tab exists in the source.

**B. Identification vs. data granularity (methodological point):** a
valid, strong instrument (F=30.84) establishes the main LA-level
effect is credible. It does not mean every follow-up question is
answerable with the same data — testing whether overseas recruitment
moderates the effect needs region-level PAYE data that only exists at
9 English regions, and no specification tried there (several were)
produces a reliable estimate. Worth framing as a structural data
limitation, not an analysis flaw — arguably illustrates why policy
debates about mechanism often can't be resolved by the data commonly
cited in them. A follow-on PhD project (RAPID data) is planned to
pursue the granular version of this question.

---

**For anything not covered here** — build process details, exact
column names, file locations, why a specific design choice was made —
check the build project's `README.md` and `README.SCOT` rather than
guessing. Those documents have the full history.

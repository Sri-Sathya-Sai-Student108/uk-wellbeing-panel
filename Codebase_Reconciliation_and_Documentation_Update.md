# Reconciliation: New Python Codebase → Existing Writing Files

**Purpose:** `bartik_check.py` + `BARTIK_RECONCILIATION_SUMMARY.md` are new since
the writing files below were drafted. This document is the single map from what
changed to what needs editing where, so no rewrite happens blind. Nothing here
touches the Stata do-file numbers already in the paper — those remain the
canonical England results. What's added is (a) confirmation they replicate,
(b) two genuinely new pieces of analysis, (c) one open item to resolve before
the Scotland numbers go in as final.

---

## 0. What's actually new (three things, not a full rewrite)

1. **Validation only, no number changes needed:** Python replicates the
   do-file's F-stat, vacancy null, employment null, and benefit-rate direction.
   Nothing in the existing papers needs correcting on this basis.
2. **A new mechanism finding:** splitting the benefit-claimant measure into a
   December snapshot (matches do-file) vs. an annual mean (new) shows opposite
   signs — a seasonal story, not previously in any document.
3. **Scotland now has actual coefficients**, not just a data-assembly plan.
   Every document currently describes Scotland as future/planned work. That
   framing is now out of date in the places listed below.

Plus one open item that should be resolved *before* the Scotland/benefit
material is finalised in prose (Section 5).

---

## 1. File-by-file edit map

### 1.1 `Revised_Paper_-_Retail_Competition_and_Care_Workforce.md`
*(target journal submission — England only, no existing Scotland content)*

- **§5.4 (Effects on Rates and Intensive Margins):** currently reports only
  the December benefit-rate coefficient (β=-0.495, p=0.040) as the headline.
  Add a new subsection **5.4a** presenting the annual-mean result alongside it
  and stating the seasonal interpretation (draft text in §2.1 below). This
  strengthens rather than complicates the story — it explains *why* the
  December effect exists rather than just reporting it.
- **§6.3 (Benefit Claimant Dynamics):** this discussion section is the natural
  home for the seasonal framing — currently discusses only the December
  result in isolation. Extend with the Christmas-hiring-peak mechanism.
- **§6.4 (Contribution Relative to IFS Study) / §7 (Conclusion):** no changes
  needed — this paper is England-only by design; Scotland doesn't belong here
  unless you want a "companion paper" footnote pointing to the Scotland work.
- **§6.7 (Limitations):** no changes required from this update.

### 1.2 `Complete_Two-Chapter_Report__Bartik_IV_Analysis.md`
*(the fullest document — has room for both new pieces)*

- **§2.4.3 (Main Results):** add the annual/December split here as it's the
  natural results-table home; cross-reference to §2.5.5 for interpretation.
- **§2.5.5 (Why Benefit Claims Fall: The Successful Transition Story):** this
  section already tells the "workers transition, don't go unemployed" story —
  it needs the seasonal caveat folded in directly, since "December claims
  fall" and "annual claims rise slightly" both need to be true statements
  in the same paragraph without contradicting each other.
- **New subsection needed after §2.5.6 (Understanding the Regional Analysis
  Results):** a **§2.5.6a "Cross-National Comparison: Does This Replicate in
  Scotland?"** — this is where the Scotland vacancy-null replication and
  benefit-effect non-replication belong, since this section already handles
  "how do we interpret results that don't look like other results."
- **§2.5.8 (Limitations):** add the SSSC all-ages-of-care scope caveat here
  (Scotland vacancy measure isn't adult-only) — this is a limitations-style
  caveat, not a findings one.
- **§2.5.9 (Future Research Directions):** currently likely frames Scotland as
  future work — **this needs updating**, since Scotland now has results, not
  just a plan. Reframe as "the Scotland extension, reported in §2.5.6a, opens
  a further question about retail-market structure (Co-op-dominated vs.
  chain-dominated) that a future paper could test directly" — future work is
  now the *explanation* for Scotland's null, not Scotland itself.
- **Appendix B.3 (Regional Variation in Overseas Workers):** add a note that a
  Scotland-equivalent breakdown isn't possible at LA level due to the SSSC
  scope caveat (all social services, not adult-only).

### 1.3 `Bartik_IV_Analysis__Summary_for_Writing_Up.md`
*(this is the master "what can we claim" reference — most heavily affected)*

- **"What to Claim vs. What to Suggest" section:** add two lines:
  - CAN CLAIM CAUSALLY: *"The vacancy null replicates in Scotland (separate
    instrument, F=26.63) — this is now a cross-national finding, not an
    England-specific one."*
  - CANNOT CLAIM: *"That the benefit-claims mechanism is universal — it's
    England-specific; Scotland's coefficients are close to zero on a strong
    first stage, not just noisier."*
- **"Critical Finding" section:** needs the December/annual split added as a
  caveat to the existing single-number claim, since as written it presents
  the December result as if it were the only benefit-claims finding.
- **New section recommended:** *"Cross-National Robustness: England vs.
  Scotland"* — this document is written as short, punchy, claim-oriented
  blocks, so the Scotland comparison table fits its existing style well
  (draft in §2.2 below).

### 1.4 `Transition_Sections__Linking_LA_and_Regional_Analyses.md`
*(bridging prose between LA-level and regional-level analysis)*

- No structural changes needed to the existing four transitions — those
  bridge LA↔regional within England and aren't affected.
- **Consider a new "Transition 5"** if the Complete Two-Chapter Report gains
  the Scotland subsection (§1.2 above): a short bridge paragraph moving from
  "regional mechanism analysis" to "does the LA-level result even hold
  outside England" — same bridging function, one level up (national rather
  than regional).

### 1.5 `Non-Expert_Summary__Retail_Competition_and_Care_Worker_Shortages.md`
*(plain-language, three-analysis narrative structure)*

- **"Summary: The Causal Story" and "The Complete Story" sections:** add one
  plain-language line: *"We checked whether this holds in Scotland too — the
  'no shortage' part does, but the 'workers move to retail and it shows up in
  benefit claims' part is specific to England."* This is a natural fit for a
  non-expert audience since it's a clean replicates/doesn't-replicate story.
- **"EVIDENCE STRENGTH SUMMARY" section:** add a row for the Scotland check —
  frame it as strengthening confidence in the main null finding while
  narrowing the benefit-claims mechanism to England.
- The December/annual seasonal split is more technical than this document's
  register — recommend leaving it out of the non-expert version, or reducing
  it to one sentence: *"the benefit-claims effect is concentrated around
  Christmas hiring, not a year-round pattern."*

### 1.6 `Health_Economics_Journal_Submission_Guide_for_Bartik_IV_Analysis...md`
*(a guide for how to write the paper, not the paper itself)*

- **§6 (Results) guidance:** add a note that a robustness/mechanism check
  (December vs. annual claimant timing) is available and referee-resistant —
  reviewers of a Bartik IV paper are likely to probe exactly this kind of
  measurement-timing question, so pre-empting it is good submission strategy.
- **§7.4 (Limitations) guidance:** add the Scotland cross-national check as an
  example of the kind of external-validity evidence referees like to see,
  if you decide to include Scotland as an appendix/robustness section in the
  England paper rather than reserving it for a separate paper.
- **Decision needed (see §3 below):** whether Scotland becomes (a) a separate
  paper, as memory suggests was the plan, or (b) a robustness appendix in the
  England paper. This guide's structure doesn't currently accommodate a
  second country — worth deciding before restructuring it.

---

## 2. Draft text blocks (ready to paste, adjust to house style)

### 2.1 Seasonal benefit-claims paragraph (for Revised Paper §6.3 / Two-Chapter §2.5.5)

> The December benefit-claims effect (β=-0.495, p=0.040) reflects retail's
> seasonal hiring peak: claimant counts fall as Christmas recruitment draws
> people off benefits. This effect does not persist across the year — an
> annual-mean version of the same measure shows no equivalent reduction. This
> is consistent with retail absorbing workers into temporary or seasonal
> roles rather than permanent employment displacing care workers, and it
> narrows the benefit-claims finding to a seasonal-activation story rather
> than evidence of a lasting labour-market reallocation.

*(Note: this phrasing is deliberately conservative — it treats the annual
result as narrowing the claim, not overturning it, since the December
result's sign and significance are the do-file benchmark and shouldn't be
undercut without your sign-off on this framing.)*

### 2.2 Scotland cross-national comparison table (for Two-Chapter Report / Summary doc)

> **Does the England result hold in Scotland?**
>
> | Outcome | England | Scotland | Replicates? |
> |---|---|---|---|
> | Vacancy rate | β=0.131, p=0.257 (null) | β=0.085, p=0.422 (null) | **Yes** |
> | Benefit rate (Dec) | β=-1.057, p=0.001 | β=-0.052, p=0.846 | **No** |
>
> The central finding — retail expansion does not create care-sector
> vacancies — holds in both nations, on independently constructed
> instruments (Scotland F=26.63, comparable strength to England). The
> benefit-claims mechanism does not extend to Scotland; this isn't weaker
> evidence of the same effect, it's a precisely estimated null on a strong
> first stage. One candidate explanation: Scotland's retail incumbent
> landscape is Co-op-dominated (~32% of major retail footprint) rather than
> spread across several national chains as in England (~22% for the largest
> single chain) — a structurally different competitive environment that may
> not displace workers into new roles in the same way.
>
> *Scope note: Scotland's SSSC vacancy measure covers all social services
> (children's, adults', older people's), not adult-only like England's
> Skills for Care data — stated here because it applies wherever the two
> nations' vacancy figures are placed side by side.*

---

## 3. Open items needing your decision before finalising

1. **The 2x benefit-rate magnitude gap** (Python -1.057 vs. do-file -0.495).
   Same direction and significance, so it doesn't threaten any existing
   claim, but it should be resolved before Scotland's *English benchmark*
   column locks in one number or the other. Suggested next step: rerun
   restricted to the ~145 name-matching LAs (excluding Cumbria, Dorset,
   Northamptonshire) and see if it narrows — flagged in the reconciliation
   summary as the most likely single cause (retail-count inflation).
2. **Scotland's destination:** separate paper (as memory suggests was the
   original plan) vs. a robustness/appendix section folded into the England
   paper. This changes which of the file-by-file edits above you'd actually
   want — a separate paper barely touches the existing England documents; an
   appendix touches all six.
3. **Whether the seasonal claimant split goes in the main text or an
   appendix.** It's genuinely new and referee-relevant, but it also
   complicates a currently-clean single-number headline result. Your call on
   how much nuance the main narrative should carry vs. defer to appendix.

---

## 4. Suggested order of operations

Once the three decisions above are made, the mechanical edits are quick:
1. Resolve the magnitude discrepancy (data check, not writing).
2. Lock in Scotland's destination (separate paper vs. appendix).
3. Paste the two draft blocks above into the six files per §1, adjusting
   tone per document (technical for the Complete Report and Summary,
   plain-language for the Non-Expert Summary, submission-strategy framing
   for the Journal Guide).

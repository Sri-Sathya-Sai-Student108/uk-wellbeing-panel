********************************************************************************
* BARTIK IV ANALYSIS: SCOTLAND (RETAIL EXPANSION AND SOCIAL CARE VACANCIES)
* Mirrors the England do-file's structure, ported from check_scotland_bartik.py
* and check_scotland_iv.py -- both reuse bartik_check.py's construct_bartik(),
* first_stage(), and run_iv() UNCHANGED, feeding them a Scotland-only panel.
* This do-file follows the same principle: same construction, same
* regression logic as England, different input data.
*
* Key differences from England, per README.SCOT (read that file for full
* rationale -- this is a Stata port of validated decisions already made,
* not a new specification):
*   - Sample: 29 councils (32 minus Orkney/Shetland/Na h-Eileanan Siar,
*     excluded on structural/geographic grounds -- decided BEFORE seeing
*     results, same logic as England's City of London/Scilly exclusion)
*   - Leave-one-out pool is SCOTLAND-ONLY (Option A) -- not pooled with
*     England. Deliberately keeps England's validated result untouched.
*   - vacancy_rate source is a DECIMAL (e.g. 0.083) -- multiplied by 100
*     here to match England's percentage-point scale.
*   - No vacant_posts count, no employees, no fte_posts equivalent exists
*     for Scotland (SSSC publishes vacancy_rate only, no LA-level WTE
*     count). Outcomes are limited to vacancy_rate, benefit_rate (Dec),
*     and benefit_rate_annual -- this is a genuine data limitation per
*     README.SCOT Section 1, not something to work around here.
*   - vacancy_rate SCOPE CAVEAT: covers ALL social services (children,
*     adults, older people), not adult-only like England's Skills for
*     Care data. State this wherever Scotland is compared to England.
*
* Assumed panel variable names (from check_scotland_iv.py's usage):
*   scotland_panel.csv: la_code, year, tot, tot_new, tot_old, pop_total,
*                        pop_65plus, vacancy_rate (decimal), claimants_december,
*                        claimants_annual
********************************************************************************

clear all
set more off

cd "D:\Repo"

********************************************************************************
* SECTION 0: LOAD DATA
********************************************************************************

import delimited "data\scotland_panel.csv", clear varnames(1) case(preserve)

* Same NULL-text safety net as the England do-file -- harmless if not
* needed, but cheap insurance against the same issue we hit there.
foreach v of varlist _all {
    capture confirm string variable `v'
    if !_rc {
        capture replace `v' = "" if trim(`v') == "NULL"
        capture destring `v', replace
    }
}

save "outputs\scotland_panel.dta", replace

********************************************************************************
* SECTION 0b: SETUP -- ISLAND EXCLUSION AND VARIABLE PREPARATION
********************************************************************************

* Keep a copy of the full 32-council sample before excluding islands, so
* we can reproduce check_scotland_bartik.py's weak-vs-strong comparison
* (F=7.52 all 32 vs F=26.63 with islands excluded) rather than only ever
* seeing the final 29-council number.
save "outputs\scotland_panel_all32.dta", replace

* Island authorities -- excluded on STRUCTURAL grounds (remote archipelago
* geography, populations in the low 20-thousands), decided independently
* of how they perform on the growth measure. NOT selected because they
* show weak growth -- see README.SCOT Section 3 for the full rationale.
drop if la_code == "S12000023"   /* Orkney Islands */
drop if la_code == "S12000027"   /* Shetland Islands */
drop if la_code == "S12000013"   /* Na h-Eileanan Siar (Western Isles) */

encode la_code, gen(LA_ID)

* --- vacancy_rate: convert decimal (0.083) to percentage points (8.3) ---
* Matches England's constructed vacancy_rate units. Drop first in case the
* source column collides with a rebuild attempt, same defensive pattern
* as the England do-file.
capture confirm variable vacancy_rate
if !_rc {
    gen vacancy_rate_pct = vacancy_rate * 100
    drop vacancy_rate
    rename vacancy_rate_pct vacancy_rate
}
else {
    display as error "vacancy_rate not found -- check scotland_panel.csv column names"
}

* --- Benefit rates, same construction as England ---
gen benefit_rate        = (claimants_december / pop_total) * 1000
gen benefit_rate_annual = (claimants_annual   / pop_total) * 1000

label variable vacancy_rate        "Vacancy rate, % (ALL social services -- not adult-only)"
label variable benefit_rate        "Benefit claim rate per 1,000 pop (December snapshot)"
label variable benefit_rate_annual "Benefit claim rate per 1,000 pop (annual mean)"

********************************************************************************
* SECTION 1: CONSTRUCT BARTIK INSTRUMENT (2016 BASELINE, SCOTLAND-ONLY POOL)
********************************************************************************

* Identical construction to England's Section 1 -- construct_bartik() in
* the Python pipeline is fully generic, so this is the same code, just
* run on the Scotland-only 29-council sample. That is deliberate: the
* leave-one-out national pool here is Scotland's own total, NOT England's
* -- this is Option A from README.SCOT Section 3, not an error.

gen new_2016   = tot_new if year == 2016
gen old_2016   = tot_old if year == 2016
gen total_2016 = tot     if year == 2016

bysort LA_ID: egen baseline_new_2016   = max(new_2016)
bysort LA_ID: egen baseline_old_2016   = max(old_2016)
bysort LA_ID: egen baseline_total_2016 = max(total_2016)

count if baseline_total_2016 == 0
if r(N) > 0 {
    display as error "WARNING: some councils have zero stores in 2016 -- Bartik set to missing"
}

gen share_new_2016 = baseline_new_2016 / baseline_total_2016
gen share_old_2016 = baseline_old_2016 / baseline_total_2016

* Expect: mean ~0.128, median ~0.136, max ~0.207 (narrower than England's
* 0.161/0.168/0.370 -- a real structural difference, see README.SCOT Sec 3).
summarize share_new_2016

bysort year: egen national_new = total(tot_new)
bysort year: egen national_old = total(tot_old)

gen national_new_excl = national_new - tot_new
gen national_old_excl = national_old - tot_old

gen national_new_2016_excl = national_new_excl if year == 2016
gen national_old_2016_excl = national_old_excl if year == 2016

bysort LA_ID: egen baseline_national_new_2016 = max(national_new_2016_excl)
bysort LA_ID: egen baseline_national_old_2016 = max(national_old_2016_excl)

gen growth_new_from2016 = (national_new_excl - baseline_national_new_2016) / baseline_national_new_2016
gen growth_old_from2016 = (national_old_excl - baseline_national_old_2016) / baseline_national_old_2016

gen bartik = share_new_2016 * growth_new_from2016 + share_old_2016 * growth_old_from2016

label variable bartik "Bartik IV (2016 baseline, Scotland-only leave-one-out pool)"

drop new_2016 old_2016 total_2016 baseline_new_2016 baseline_old_2016
drop baseline_total_2016 national_new national_old national_new_excl
drop national_old_excl national_new_2016_excl national_old_2016_excl
drop baseline_national_new_2016 baseline_national_old_2016
drop growth_new_from2016 growth_old_from2016

save "outputs\scotland_panel_with_bartik.dta", replace

********************************************************************************
* SECTION 2: FIRST-STAGE DIAGNOSTICS (2020-2023)
********************************************************************************

display as result _n "{hline 80}"
display as result "SECTION 2: FIRST-STAGE DIAGNOSTICS -- 29 COUNCILS, ISLANDS EXCLUDED"
display as result "{hline 80}"

* Benchmark (check_scotland_bartik.py): F = 26.63, strong (>16.38 Stock-Yogo).
* If your F differs noticeably from 26.63, check the island exclusion and
* the 2016-baseline construction against README.SCOT Section 3 before
* trusting downstream results.

reghdfe tot bartik pop_total pop_65plus if year >= 2020, ///
    absorb(LA_ID year) cluster(LA_ID)

test bartik

********************************************************************************
* SECTION 3: MAIN IV ANALYSIS (2020-2023) -- 29 COUNCILS
********************************************************************************

display as result _n "{hline 80}"
display as result "SECTION 3: MAIN IV ANALYSIS -- SCOTLAND, 29 COUNCILS, 2020-2023"
display as result "{hline 80}"

* NOTE: use ivreghdfe (true FE absorption), not ivreg2 with i.LA_ID dummies
* -- the England session found these can diverge for some outcomes even
* though they're supposed to be numerically equivalent. ivreghdfe matches
* the Python demeaning approach exactly.

* --- Vacancy rate ---
* Benchmark: beta=0.085, p=0.422 (null). SCOPE CAVEAT: this covers ALL
* social services, not adult-only like England -- see header notes.
ivreghdfe vacancy_rate pop_total pop_65plus i.year (tot = bartik) if year >= 2020, ///
    absorb(LA_ID) cluster(LA_ID) first
estimates store scot_vac_rate

* --- Benefit rate, December ---
* Benchmark: beta=-0.052, p=0.846 (null). England benchmark for contrast:
* beta=-1.057, p=0.001 -- Scotland's point estimate is ~20x smaller, not
* just noisier. This is the headline "does not replicate" finding.
ivreghdfe benefit_rate pop_total pop_65plus i.year (tot = bartik) if year >= 2020, ///
    absorb(LA_ID) cluster(LA_ID) first
estimates store scot_ben_dec

* --- Benefit rate, annual ---
* Benchmark: beta=0.086, p=0.648 (null). England benchmark for contrast:
* beta=+0.632, p<0.001.
ivreghdfe benefit_rate_annual pop_total pop_65plus i.year (tot = bartik) if year >= 2020, ///
    absorb(LA_ID) cluster(LA_ID) first
estimates store scot_ben_annual

esttab scot_vac_rate scot_ben_dec scot_ben_annual, ///
    keep(tot) b(3) se(3) star(* 0.10 ** 0.05 *** 0.01) ///
    mtitles("Vacancy Rate" "Benefit Rate (Dec)" "Benefit Rate (Annual)") ///
    title("Scotland IV Results, 29 Councils, 2020-2023 -- cf. England benchmarks in comments above")

********************************************************************************
* NOTES ON INTERPRETATION (per README.SCOT Section 6)
********************************************************************************

* - Vacancies REPLICATE across both nations: retail expansion doesn't
*   appear to hurt care-sector staffing capacity in either country --
*   genuine cross-national agreement, not two separate underpowered nulls
*   (both first stages are strong: England F=30.84, Scotland F=26.63).
* - Benefits do NOT replicate: England's effect is large and significant
*   in both December and annual specifications; Scotland's point estimates
*   are close to zero on a solid first stage -- a genuine divergence, not
*   a weak-instrument artefact.
* - Tentative explanation (discussion section, not a proven mechanism):
*   Scotland's retail incumbent base is Co-op-dominated (~31.8% of major
*   retail footprint vs ~22% in England) rather than spread across
*   several large national chains -- a structurally different competitive
*   landscape that may not displace workers into new roles the same way.

display as result _n "{hline 80}"
display as result "DO-FILE COMPLETE"
display as result "{hline 80}"

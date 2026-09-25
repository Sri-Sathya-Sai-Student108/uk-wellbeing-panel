********************************************************************************
* BARTIK IV ANALYSIS: RETAIL EXPANSION AND CARE WORKER SHORTAGES
* v2 -- recreated to run on the new Python pipeline's panel output, replacing
* outputs\all_251016.dta as the data source.
*
* Carries over three design changes already validated in bartik_check.py
* relative to the original do-file:
*   1. benefit_rate is now split into December (matches the original do-file
*      exactly) and annual mean (new -- reveals the seasonal pattern).
*   2. The OLD Section 4 (LA-level "visa control") and Section 5 (LA-level
*      heterogeneity by high/low visa region) are REMOVED. Both broadcast a
*      regional PAYE variable down to LA level, giving zero within-region
*      LA-to-LA variation -- invalid alongside LA-clustered SEs. Replaced
*      with a single region-level mechanism section (Section 4 below),
*      matching the Python design exactly: ONE shared first stage, with
*      region FE and PAYE both living in the second stage only.
*   3. Two new OPTIONAL sections at the end (5 and 6) are starting
*      specifications for two open items, not yet-confirmed results:
*        - Section 5: whether the December benefit effect is concentrated
*          in discount-chain exposure (a complier-style check)
*        - Section 6: whether the ~2x benefit-rate magnitude gap vs. the
*          original do-file narrows under a name-matched sample restriction
*
* Assumed panel variable names (confirm against your actual CSV headers --
* these match bartik_check.py's usage, not verified against a live file):
*   england_panel_sfc.csv:   la_code, la_name, year, region, tot, tot_new,
*                             tot_old, pop_total, pop_65plus, vacant_posts,
*                             filled_posts, employees, fte_posts,
*                             claimants_december, claimants_annual
*   paye_overseas_regional.csv: region, region_code, year, overseas_share
********************************************************************************

clear all
set more off

* Set your working directory
cd "D:\Repo"

********************************************************************************
* SECTION 0: LOAD DATA (from new Python pipeline output)
********************************************************************************

* The Python pipeline outputs CSVs rather than a single .dta. Import both and
* save as .dta; adjust paths to match your local build output structure.

import delimited "data\intermediate\england_panel_sfc.csv", clear varnames(1) case(preserve)

* --- Clean up literal "NULL" text before it causes problems ---
* If your CSV writes missing values as the literal string NULL (common from
* pandas/SQL exports) rather than a true blank cell, import delimited reads
* those columns in as string instead of numeric, and every later calculation
* on them silently fails or prints as missing. This loop finds any string
* variable, blanks out "NULL", and destrings it back to numeric.
foreach v of varlist _all {
    capture confirm string variable `v'
    if !_rc {
        capture replace `v' = "" if trim(`v') == "NULL"
        capture destring `v', replace
    }
}

save "outputs\england_panel_sfc.dta", replace

import delimited "data\intermediate\paye_overseas_regional.csv", clear varnames(1) case(preserve)

foreach v of varlist _all {
    capture confirm string variable `v'
    if !_rc {
        capture replace `v' = "" if trim(`v') == "NULL"
        capture destring `v', replace
    }
}

save "outputs\paye_overseas_regional.dta", replace

use "outputs\england_panel_sfc.dta", clear

********************************************************************************
* SECTION 0b: SETUP - VARIABLE PREPARATION
********************************************************************************

* Deduplicate: the Python-side panel is long on measure type; keep one row
* per la_code-year, matching bartik_check.py's drop_duplicates() step.
duplicates drop la_code year, force

* Exclude City of London and Isles of Scilly (matches Python EXCL set)
drop if la_code == "E09000001"
drop if la_code == "E06000053"

* Encode LA code and region to numeric for fixed effects / clustering
encode la_code, gen(LA_ID)
encode region, gen(Region_ID_num)

* Total retailers (discount + traditional), if not already summed
capture confirm variable tot
if _rc {
    gen tot = tot_new + tot_old
}

* Derived outcome variables (matches Python load_data())
replace filled_posts = 0 if missing(filled_posts)
replace vacant_posts = 0 if missing(vacant_posts)
gen posts = filled_posts + vacant_posts
gen vacancy_rate = (vacant_posts / posts) * 100 if posts > 0

* Benefit rate: December (matches original do-file exactly) and annual (new)
gen benefit_rate        = (claimants_december / pop_total) * 1000
gen benefit_rate_annual = (claimants_annual   / pop_total) * 1000

gen fte_per_emp = fte_posts / employees if employees > 0

label variable benefit_rate        "Benefit claim rate per 1,000 pop (December snapshot)"
label variable benefit_rate_annual "Benefit claim rate per 1,000 pop (annual mean)"

********************************************************************************
* SECTION 1: CONSTRUCT BARTIK INSTRUMENT (2016 BASELINE)
********************************************************************************

* --- Step 1: 2016 shares ---
gen new_2016   = tot_new if year == 2016
gen old_2016   = tot_old if year == 2016
gen total_2016 = tot     if year == 2016

bysort LA_ID: egen baseline_new_2016   = max(new_2016)
bysort LA_ID: egen baseline_old_2016   = max(old_2016)
bysort LA_ID: egen baseline_total_2016 = max(total_2016)

count if baseline_total_2016 == 0
if r(N) > 0 {
    display as error "WARNING: some LAs have zero stores in 2016 -- Bartik set to missing"
}

gen share_new_2016 = baseline_new_2016 / baseline_total_2016
gen share_old_2016 = baseline_old_2016 / baseline_total_2016

* --- Step 2: National growth rates (leave-out), 2016 baseline ---
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

* --- Step 3: Construct instrument ---
* Kept as separate components (bartik_discount / bartik_trad) as well as the
* combined bartik, so Section 5's complier check doesn't need to
* reconstruct them later.
gen bartik_discount = share_new_2016 * growth_new_from2016
gen bartik_trad     = share_old_2016 * growth_old_from2016
gen bartik = bartik_discount + bartik_trad

label variable bartik "Bartik IV (2016 baseline, discount vs traditional chains)"
label variable bartik_discount "Bartik IV -- discount-chain component only"
label variable bartik_trad     "Bartik IV -- traditional-chain component only"
label variable share_new_2016 "Discount chain share, 2016"
label variable share_old_2016 "Traditional chain share, 2016"

* Clean up intermediate variables
drop new_2016 old_2016 total_2016 baseline_new_2016 baseline_old_2016
drop baseline_total_2016 national_new national_old national_new_excl
drop national_old_excl national_new_2016_excl national_old_2016_excl
drop baseline_national_new_2016 baseline_national_old_2016
drop growth_new_from2016 growth_old_from2016

save "outputs\england_panel_with_bartik.dta", replace

********************************************************************************
* SECTION 2: FIRST-STAGE DIAGNOSTICS (2020-2023)
********************************************************************************

display as result _n "{hline 80}"
display as result "SECTION 2: FIRST-STAGE DIAGNOSTICS (2020-2023)"
display as result "{hline 80}"

* NOTE: controls are pop_total and pop_65plus, not pop_all/pop_60 -- the
* Python pipeline doesn't carry a pop_60 field. pop_65plus is what
* bartik_check.py flags as a known, minor difference from the original
* do-file benchmark (doesn't affect direction/significance).

reghdfe tot bartik pop_total pop_65plus if year >= 2020, absorb(LA_ID year) cluster(LA_ID)

test bartik

* Python validation on this panel: F ~ 30.84 (original do-file benchmark: ~43)

********************************************************************************
* SECTION 3: MAIN IV ANALYSIS - LA LEVEL (2020-2023)
********************************************************************************

display as result _n "{hline 80}"
display as result "SECTION 3: MAIN IV ANALYSIS - LA LEVEL, 2020-2023"
display as result "{hline 80}"

* --- Vacant posts ---
ivreg2 vacant_posts pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_vacancies
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- Total employees ---
ivreg2 employees pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_employment
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- FTE posts ---
ivreg2 fte_posts pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_fte
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- Total posts ---
ivreg2 posts pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_posts
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- Vacancy rate ---
ivreg2 vacancy_rate pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_vac_rate
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- FTE per employee (intensive margin) ---
ivreg2 fte_per_emp pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_intensity
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- Benefit rate, December (matches original do-file measure) ---
ivreg2 benefit_rate pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_ben_rate_dec
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- Benefit rate, annual mean (NEW -- not in the original do-file) ---
ivreg2 benefit_rate_annual pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
estimates store iv_ben_rate_annual
estadd scalar clusters = e(N_clust)
estadd scalar fstat = e(widstat)

* --- Summary table: main outcomes ---
esttab iv_vacancies iv_employment iv_fte iv_posts, keep(tot) b(3) se(3) star(* 0.10 ** 0.05 *** 0.01) stats(clusters N fstat, labels("Clusters" "Observations" "First-stage F") fmt(%9.0g %9.0g %9.2f)) mtitles("Vacancies" "Employees" "FTE Posts" "Total Posts") title("Effect of Retail Expansion on Care Sector Outcomes, 2020-2023")

* --- Summary table: rates, December/annual benefit split side by side ---
esttab iv_vac_rate iv_intensity iv_ben_rate_dec iv_ben_rate_annual, keep(tot) b(3) se(3) star(* 0.10 ** 0.05 *** 0.01) stats(clusters N fstat, labels("Clusters" "Observations" "First-stage F") fmt(%9.0g %9.0g %9.2f)) mtitles("Vacancy Rate" "FTE/Employee" "Benefit Rate (Dec)" "Benefit Rate (Annual)") title("Effect on Rates and Intensive Margin, Including Seasonal Benefit Split")

* If December is negative & significant and Annual is null/positive, this is
* consistent with a Christmas-hiring seasonal effect rather than a
* year-round labour market reallocation. Report both together -- don't
* report the December figure alone.

********************************************************************************
* SECTION 4: REGIONAL MECHANISM ANALYSIS (SINGLE SHARED FIRST STAGE)
********************************************************************************

* Replaces the OLD Section 4 (LA-level "visa control") and Section 5
* (LA-level heterogeneity by high/low visa region). Both broadcast a
* regional PAYE variable down to LA level, giving zero within-region
* LA-to-LA variation -- invalid alongside LA-clustered SEs. This section
* replicates the Python design exactly instead:
*   Stage 1 (single, shared across all regions): tot ~ bartik_region
*   Stage 2: outcome ~ tot_hat + year FE + overseas_share_contemp
*            + region FE, clustered by region.
* Confined to 9 English regions, N=36 region-years -- a scoping/mechanism
* exercise, NOT a headline causal result (more stage-2 parameters than
* clusters).

display as result _n "{hline 80}"
display as result "SECTION 4: REGIONAL MECHANISM (SINGLE FIRST STAGE, N=9 REGIONS)"
display as result "{hline 80}"

preserve

keep if year >= 2020 & year <= 2023
collapse (mean) bartik tot (sum) pop_total vacant_posts filled_posts claimants_december claimants_annual, by(region year)

gen posts_r = filled_posts + vacant_posts
gen vacancy_rate_r        = (vacant_posts / posts_r) * 100 if posts_r > 0
gen benefit_rate_r        = (claimants_december / pop_total) * 1000
gen benefit_rate_annual_r = (claimants_annual   / pop_total) * 1000

rename bartik bartik_region

* Merge in contemporaneous PAYE overseas share (English regions only --
* confirm your paye_overseas_regional.dta is pre-filtered to region_code
* starting "E12", or filter here before merging)
merge 1:1 region year using "outputs\paye_overseas_regional.dta", keepusing(overseas_share) keep(match) nogen
rename overseas_share overseas_share_contemp

encode region, gen(Region_ID_num2)

* --- Vacant posts ---
ivreg2 vacant_posts overseas_share_contemp i.year i.Region_ID_num2 (tot = bartik_region), cluster(Region_ID_num2) first ffirst
estimates store mech_vacancies

* --- Vacancy rate ---
ivreg2 vacancy_rate_r overseas_share_contemp i.year i.Region_ID_num2 (tot = bartik_region), cluster(Region_ID_num2) first ffirst
estimates store mech_vac_rate

* --- Benefit rate (December) ---
ivreg2 benefit_rate_r overseas_share_contemp i.year i.Region_ID_num2 (tot = bartik_region), cluster(Region_ID_num2) first ffirst
estimates store mech_ben_dec

* --- Benefit rate (annual) ---
ivreg2 benefit_rate_annual_r overseas_share_contemp i.year i.Region_ID_num2 (tot = bartik_region), cluster(Region_ID_num2) first ffirst
estimates store mech_ben_annual

esttab mech_vacancies mech_vac_rate mech_ben_dec mech_ben_annual, keep(tot) b(3) se(3) star(* 0.10 ** 0.05 *** 0.01) mtitles("Vacant Posts" "Vacancy Rate" "Benefit Rate (Dec)" "Benefit Rate (Annual)") title("Regional Mechanism, N=9 English Regions -- SCOPING, NOT CAUSAL")

restore

********************************************************************************
* SECTION 5 (NEW, OPTIONAL): COMPLIER CHECK -- IS THE DECEMBER EFFECT
* CONCENTRATED IN DISCOUNT-CHAIN EXPOSURE?
********************************************************************************

* Open item, not yet run: 2SLS with a continuous Bartik instrument doesn't
* identify a classic binary-complier LATE -- it identifies a weighted
* average of local effects across the instrument's variation. Since the
* instrument has two components (discount vs. traditional chain exposure),
* and discount chains (Aldi/Lidl) do noticeably heavier Christmas seasonal
* hiring, the December benefit-rate effect should -- if it really is a
* seasonal-hiring story -- be concentrated among LAs whose exposure comes
* mainly through the discount-chain component, not spread evenly across
* both. bartik_discount and bartik_trad are already available from Section 1.

display as result _n "{hline 80}"
display as result "SECTION 5 (OPTIONAL): DISCOUNT VS TRADITIONAL COMPLIER CHECK"
display as result "{hline 80}"

* Uncomment to run. Compare the two coefficients: if the discount-only
* instrument reproduces the December effect and the traditional-only one
* doesn't, that supports the seasonal-hiring / complier story.

* ivreg2 benefit_rate pop_total pop_65plus i.year i.LA_ID (tot = bartik_discount) if year >= 2020, cluster(LA_ID) first ffirst
* estimates store complier_discount
*
* ivreg2 benefit_rate pop_total pop_65plus i.year i.LA_ID (tot = bartik_trad) if year >= 2020, cluster(LA_ID) first ffirst
* estimates store complier_trad
*
* esttab complier_discount complier_trad, keep(tot) b(3) se(3) star(* 0.10 ** 0.05 *** 0.01) mtitles("Discount-chain instrument only" "Traditional-chain instrument only") title("Complier check: December benefit effect by instrument component")

********************************************************************************
* SECTION 6 (NEW, OPTIONAL): NAME-MATCHED SAMPLE RESTRICTION
********************************************************************************

* Open item: the December benefit-rate coefficient on this panel runs
* roughly double the original do-file's magnitude (-1.057 vs -0.495).
* Candidate explanation: retail-count inflation from LAs that don't
* name-match cleanly against the original panel (Cumbria, Dorset,
* Northamptonshire -- reorganised into unitary splits since the original
* do-file's panel vintage). CONFIRM exact la_name / la_code values in
* THIS panel before running -- do not assume these string matches are
* correct without checking.

display as result _n "{hline 80}"
display as result "SECTION 6 (OPTIONAL): NAME-MATCHED SAMPLE RESTRICTION"
display as result "{hline 80}"

* preserve
* drop if strpos(lower(la_name), "cumbria") > 0
* drop if strpos(lower(la_name), "dorset") > 0
* drop if strpos(lower(la_name), "northamptonshire") > 0
*
* ivreg2 benefit_rate pop_total pop_65plus i.year i.LA_ID (tot = bartik) if year >= 2020, cluster(LA_ID) first ffirst
* -- compare this coefficient to -1.057 (full sample, above) and -0.495
*    (original do-file). If it narrows substantially toward -0.495,
*    retail-count inflation is confirmed as the driver of the gap.
* restore

display as result _n "{hline 80}"
display as result "DO-FILE COMPLETE"
display as result "{hline 80}"
# Aggregate data dictionary

All numerical result CSVs are in `data/aggregates/`. They are long-format estimates or aggregate summaries, not participant rows.

| Column/family | Meaning |
|---|---|
| `capacity` | Complete programmes requested per 1,000 original 2018 candidates |
| `mode` | `known_equal`: equal places, support already known; `paid_equal`: equal places with enquiry paid; `fixed_resource`: joint staff/budget ceiling |
| `scenario` | Population and resource scenario, e.g. `2018_paid500`, `2020_eligible50`, `2018_rural_fixed500` |
| `policy` | S0-R or S1-R; `paired_difference` means S1-R minus S0-R unless an explicit frozen/updated-list comparison is specified |
| `design` | `community_WR` or `county_WR`, the paired with-replacement cluster approximation |
| `estimate`, `lower`, `upper` | Frozen point estimate and pointwise paired percentile 95% interval |
| `replicates`, `attempted`, `valid`, `failed` | Draw counts; failed or undefined target outcomes must not be silently dropped |
| `packages` | Modelled complete-programme opportunity mass, not an integer count of observed patients treated |
| `eligible_mass` | Current eligible opportunity mass on the original weighted-1,000 denominator |
| `gap_population`, `gap_reached`, `gap_unserved` | Assistance-gap opportunity mass in the population, allocated and unallocated |
| `gap_coverage_percent` | Allocated gap opportunity mass divided by the corresponding gap population, times 100 |
| `B_total`, `I_total` | Allocation-weighted totals of ordinal basic-ADL/IADL indices; not clinical outcome changes |
| `B_change`, `I_change`, `family_gain`, `rural_gain` | Difference relative to the specified S0-R allocation |
| `family_reached`, `rural_reached` | Allocations to participants with confirmed family help / rural residence |
| `entrants`, `displaced` | Weighted increases/decreases in individual allocation probabilities; not necessarily full integer treatment switches |
| `RN_h`, `OT_h`, `inquiry_h` | Hours per original 1,000 candidates, with enquiry charged as RN work |
| `provider_USD` | Planning programme expenditure in 2024 US$ per original 1,000 candidates |
| `patient_contact_h`, `patient_total_h` | Programme contact and contact plus synchronous enquiry hours |
| `recorded_family_month_hours` | Descriptive recorded assistance hours among recipients with observations; not preventable hours |
| `N_retained` | Covered B+I need relative to S0-R; an ordinal-index ratio, not a safety/health threshold |
| `suppressed`, `suppression_applied`, `suppressed_fields`, `status`, `disclosure` | Disclosure or availability flags; row-level flags may coexist with released resource totals |

## File groups

- `CAPACITY_100_900_RESULTS`, `PAIRED_NINE_CAPACITY_RESULTS`, `JOINT_TRADEOFF_BY_CAPACITY`, `CONDITIONAL_ACCEPTABILITY_GRID`: nine-capacity policies, paired uncertainty and transparent two-objective sampling stability.
- `MAIN_500_POLICY_COMPARISON`, `ENTRANTS_DISPLACED_500`, `PATIENT_FAMILY_TASK_*`, `TASK_NEEDS_BY_CAPACITY`: reference allocation, opportunity exchange and functional/family composition.
- `ALL_SENSITIVITY_POINTS`, `ALL_PAIRED_UNCERTAINTY`, `FEASIBILITY_ALL_DRAWS`: full follow-up, age-compatibility, inquiry and rural scenario outputs.
- `FOLLOWUP2020_*`: observed same-person follow-up, current eligibility, natural needs and reassessment; not programme follow-up effects.
- `RURAL500_*`, `RURAL_NEXT_PACKAGE_BINDING_DIAGNOSTICS`: travel costs, occupational constraints and no-displacement expansion.
- `QUERY_IMPLEMENTATION_*`: targeted, universal and conservative-union enquiries under the same priority rule.
- `NO_DISPLACEMENT_EXPANSION`, `INDIVIDUAL_PROTECTION_RESOURCES`: additional complete programmes/resources for retaining original allocations.
- `PARTICIPATION_ACCOUNTING`, `FAMILY_PARTICIPATION_CURRENT`, `OCCUPATION_SPECIFIC_PRICE_COEFFICIENTS`: participation and separately priced RN/OT resource coefficients.
- `SOURCE_FLOW_FINAL`, `SOURCE_POPULATION_SUMMARY`, `BASELINE_*`, `AGE_GROUP*`, `UPDATED_BASELINE_DENOMINATORS`: aggregate source flow, nested-population characteristics, native variable mappings and valid denominators.
- `EVIDENCE_LEDGER`: source evidence and limits of interpretation; no third-party full texts are redistributed.

Source-catalogue aliases retained in mappings mean: F08889, 2018 health/function module; F08896, 2018 individual weights; F08915, Harmonized CHARLS demographics; F08908, 2020 health/function module; F08905, 2020 demographics. They are catalogue labels, not official CHARLS variable names. The actual item names appear alongside them.

## Figure/table source data

`data/display/Table*.csv` gives final display cells. `tables.json` includes titles, headers, notes and cells; `figures.json` contains numerical plotting inputs. Figure-specific CSVs make these inputs inspectable without plotting. `metadata/SOURCE_VALUE_LEDGER.csv` maps each display cell to its source file, exact selector, field and multiplier. `DERIVED_DISPLAY_IDENTITIES.csv` records deterministic display identities. These transformations do not generate new estimates or intervals.

The baseline table reports unweighted n and survey-weighted percentages within each column, weighted means/SDs and weighted empirical quartiles. The assistance-gap column is a nested subset, not a comparison group; no between-column test is provided.

## Missingness and privacy

An empty numeric cell with a suppression flag must remain withheld. An empty cell without such a flag may be unavailable or undefined; inspect its status and denominator. Neither is numeric zero. Fine-grained exchange counts and complementary counts are suppressed together where required. Do not infer the hidden values from other public tables.

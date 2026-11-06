# Restricted analytical inputs

This document describes the actual analytical interface, not a substitute for CHARLS permission or a claim that harmonisation is automatic. The code was checked against the frozen study files. Reconstructing those files from a separately obtained CHARLS release requires the documented sample, original item routing and verified person-wave linkage. Do not substitute a convenience complete-case cohort or infer unobserved answers.

## Configuration

Create a JSON file **outside** the public repository:

```json
{
  "baseline_2018": "/approved/private/analytic_family_2018.parquet",
  "followup_2020": "/approved/private/analytic_family_2020.parquet",
  "sampling_frame_2018": "/approved/private/charls2018.parquet",
  "output_directory": "/approved/private/reanalysis"
}
```

Paths above are placeholders, not distributed data. The output directory must not be within the repository. The code does not upload any data.

## Baseline schema

Exactly 2,433 unique participants aged at least 60, with 564 explicit gap reports; original row order retained for paired validation.

| Field | Meaning |
|---|---|
| `ID` | Private linkage key; never public |
| `weight` | Positive 2018 individual weight, `INDV_weight_ad2`; no arbitrary trimming |
| `psu` | Original community label, retained as a string; first six characters identify the county in the frozen source |
| `age` | Verified wave-4 age, harmonized `r4agey` |
| `adl0`–`adl4` | Dressing, bathing, eating, transferring, toileting; native ordinal values 1–4 |
| `iadl0`–`iadl4` | Housework, meal preparation, shopping, finances, medication; native values 1–4 |
| `gap_known` | At least one activity coded 3/4 with an explicit report of no assistance for that same activity |
| `unknown_need_n` | Number of needed-help activities whose assistance is unresolved; unknown is not no assistance |
| `family_confirmed` | Confirmed family-helper report from the functional-module roster; not-confirmed does not establish no family assistance |
| `family_recorded_month_hours` | Recorded family assistance hours with missingness preserved; descriptive, not assumed reducible by the programme |
| `rural` | Frozen rural residence indicator; current community, not hukou |

The 2018 original activity fields are `db010`–`db014` and `db016`–`db020`, with corresponding `_w2` assistance fields. Original responses distinguish: 1 no difficulty; 2 difficulty but can complete independently; 3 needs help; 4 cannot complete. A verified negative screening route can establish normal function; ordinary blanks cannot. Help not asked because there is no explicit need is distinct from unknown help where need exists.

## Follow-up schema

The 2020 file has the same 2,433 keys in the same order, with `eligible_current` indicating the 1,386 observed, currently community-resident records satisfying the frozen operational functional and support requirements. All original participants remain in the denominator; the current eligible subset is not rescaled to 1,000.

The eligible records require the ten ordinal activity fields, `gap_known`, `unknown_need_n`, `family_confirmed`, `family_recorded_month_hours` and `rural` as above. Original ability/assistance pairs are `db001/002`, `db003/004`, `db005/006`, `db007/008`, `db009/010`, `db012/013`, `db014/015`, `db016/017`, `db022/023`, and `db020/021`, in the task order above. Follow-up `rural` is the inherited baseline residence measure; it is not newly measured 2020 rural status.

Death, unresolved life/function status, observed non-eligibility and unresolved current qualification must be classified before assigning `eligible_current`; unknown is never recoded healthy or independent. See `FOLLOWUP2020_FLOW_AND_ELIGIBILITY.csv` for the released partition and `FOLLOWUP2020_UNKNOWN_BOUNDS.csv` for compatible bounds. Natural follow-up is not an intervention response.

## Resampling frame

The third file is the full 2018 source frame, with `weight`, `raw_interview` and `psu`. Positive-weight interviewed records define 449 observed communities and 150 counties in the frozen implementation. Do not resample only the communities represented among selected recipients. Each draw multiplies original survey weights by cluster multiplicities and renormalises the **baseline** candidate weights to 1,000. Both policies, all capacities and all follow-up subsets use the same draw. This is a with-replacement approximation, not a reconstruction of unavailable official sampling strata.

## Reproduction boundaries

The public route reproduces frozen aggregate arithmetic and displays. The restricted route recomputes allocation, resource outcomes, nine-capacity paired intervals and follow-up/rural sensitivities using the specified analytical files. Their preparation is documented through native field mappings and routing rules, but an automated raw-download-to-final-cohort pipeline is not included. Complete original preparation records remain in the authors' authorised environment.

For participant-level baseline descriptive recomputation, additionally supply `harmonized_charls`, the authorised Harmonized CHARLS Stata or parquet file containing `ID`, `r4agey`, `ragender`, `raeduc_c`, `h4rural`, `r4mstath` and `h4hhres`. The baseline analytical file must also retain `sex`, `education`, `chronic_n` and `roster_known`. With `CUCOM_CONFIG` set, run `python analysis/baseline_descriptives.py`. It computes the overall and nested gap-group summaries directly; it does not infer the subgroup from overall statistics.

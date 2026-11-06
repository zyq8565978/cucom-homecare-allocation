# CuCoM home-based care allocation

Analysis code and aggregate data for:

**Balancing functional limitations and gaps in assistance in home-based care allocation for older adults with multimorbidity: A population-based simulation guided by the Cumulative Complexity Model**

This cost–consequence analysis compares functional-need priority (S0-R, displayed as S0) with assistance-gap-informed priority (S1-R, displayed as S1). Both preserve the same basic-ADL tier and score priority. The study population comprises 2,433 community-dwelling CHARLS participants aged 60 years or older with multimorbidity and functional difficulties; 564 reported an explicit same-activity assistance gap.

The reference is 500 complete five-month programmes per 1,000 original candidates, with capacities of 100–900 examined. Registered-nurse visits, occupational therapy and home adaptation remain a complete programme. Equal programme numbers, fixed professional resources, and expansion without displacement are distinct comparisons.

## What is available

| Directory | Contents |
|---|---|
| `analysis/` | Two-policy allocation, sequential information acquisition, nine capacities, paired cluster resampling, 2020 reassessment, rural travel, resource expansion and independent checks |
| `data/aggregates/` | Frozen, disclosure-controlled estimates, paired intervals, follow-up flow and cost–consequence results |
| `data/display/` | Numerical source data for the final two main tables, three main figures and supplementary exhibits |
| `scripts/` | Public arithmetic/provenance checks and reproduction of tables and figures |
| `metadata/` | Model parameters, source-cell ledger, variable mappings and file checksums |
| `docs/` | Definitions, access conditions, reproduction scope and availability statements |
| `tests/` | Synthetic tests of priority, conservation, unknown responses and information boundaries |

**No participant records, identifiers, individual survey weights, linked histories or unrestricted resampling arrays are distributed.** Empty or withheld cells are not zero. Do not reconstruct protected cells from complements.

## Public reproduction

The original analyses used Python 3.12.14, NumPy 2.3.5, pandas 2.3.3, SciPy 1.16.3 and Matplotlib 3.10.7. PyArrow 25.0.1 is required for authorised parquet inputs.

```bash
python -m venv .venv
# Activate the environment using the command appropriate to your operating system.
python -m pip install -r requirements.txt
python scripts/verify_release.py
python scripts/reproduce_public.py
python -m unittest discover -s tests
```

Reproduced tables and figures are written to `results/`. This public route verifies and renders the frozen aggregate estimates; it does **not** re-estimate allocation or confidence intervals from participants. `--no-plots` skips figure rendering. Arial was used for the original figures; install that font or expect a font substitution on other systems.

## Authorised participant-level re-analysis

Obtain data through [CHARLS](https://charls.pku.edu.cn/en/) and use only an approved local environment. See [restricted input documentation](docs/RESTRICTED_INPUTS.md) for the frozen analytical schema and routing requirements. The analytical participant files are not included. The repository does not claim to automate every raw-release-to-analytical-file preparation step.

```bash
python analysis/run_analysis.py --config /path/to/private/config.json
```

For the independent full-run check, set `CUCOM_CONFIG` to that private configuration, then run `python analysis/independent_check.py`. Both analysis components must have completed first. All private inputs and generated arrays must remain outside this repository.

## Interpretation

- Coverage means a modelled service opportunity, not observed health improvement.
- IADL indices describe ordinal functional need, not health utility or clinical deterioration.
- Family assistance can coexist with an unmet same-activity need; reported family help is not proof of adequate or sustainable support.
- Programme costs, brief enquiry time and extra rural travel are planning inputs, not measured nationwide service prices.
- Intervals use 5,000 paired with-replacement community draws, with county resampling as sensitivity analysis. This is a stated public-data design approximation, not fully reconstructed official stratified-PPS variance.
- The 500-programme reference and revised priority rules were developed after earlier results had been examined. They are not presented as prospectively registered or objectively optimal.
- No CAPABLE treatment effect, QALY gain or caregiver time saving is identified in CHARLS by these allocation comparisons.

See [analysis definitions](docs/ANALYSIS_DEFINITIONS.md), [data access](docs/DATA_ACCESS.md), and [code availability](docs/CODE_AVAILABILITY.md). The MIT licence applies to original code only.

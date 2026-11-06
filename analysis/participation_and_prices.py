"""Accounting only: reuse allocation draws; no new policy or price selection."""
from engine import *


def main():
    points=np.load(R/'private/points.npz')
    # Scenario ordering is fixed and shared by all saved paired arrays.
    names=json.loads((R/'logs/SCENARIOS.json').read_text())
    if isinstance(names,dict):names=names['names']
    v=points['values'];rows=[]
    for design in ['community_WR','county_WR']:
        z=np.load(R/'private'/f'{design}.npz')['values']
        for i,name in enumerate(names):
            labels=['frozen2018_function','updated2020_function'] if '_update_' in name else ['S0-R','S1-R']
            for programme_h in [0,5,10]:
                for inquiry_fraction in [0,.5,1]:
                    est=programme_h*v[i,:,0]+inquiry_fraction*v[i,:,10]
                    draws=programme_h*z[:,i,:,0]+inquiry_fraction*z[:,i,:,10]
                    for a,policy in enumerate(labels+['paired_difference']):
                        xx=draws[:,1]-draws[:,0] if a==2 else draws[:,a]
                        val=est[1]-est[0] if a==2 else est[a]
                        lo,hi=np.quantile(xx,[.025,.975])
                        rows.append(dict(scenario=name,policy=policy,design=design,
                          programme_family_h_per_package=programme_h,inquiry_family_fraction=inquiry_fraction,
                          total_family_participation_h=val,lower=lo,upper=hi,
                          unit='hours / original2018 weighted1000',status='PLANNING_PARTICIPATION_NOT_CARE_SAVINGS'))
    save('supplement/FAMILY_PARTICIPATION_CURRENT.csv',rows)
    # Distinct occupational coefficients. The shared historical value is only
    # a reproducibility reference, not an estimate of both occupations' wages.
    pts=pd.read_csv(R/'ALL_SENSITIVITY_POINTS.csv')
    ledger=[]
    for name in ['2018_rural_paid500','2020_rural_paid500']:
        for policy in ['S0-R','S1-R']:
            q=pts[(pts.scenario==name)&(pts.policy==policy)].set_index('metric').estimate
            rn=q.travel_RN_h+q.inquiry_h;ot=q.travel_OT_h
            ledger.append(dict(scenario=name,policy=policy,
              fixed_complete_package_cost_USD=q.packages*COST,
              additional_RN_h_coefficient=rn,additional_OT_h_coefficient=ot,
              reference_RN_rate_USD=RATE,reference_OT_rate_USD=RATE,
              reference_total_USD=q.provider_USD,
              formula='complete_package_cost + RN_h_coefficient * r_RN + OT_h_coefficient * r_OT',
              rate_units='2024 US$/hour; two independently replaceable occupation-specific rates',
              evidence='Historical common planning labour valuation only; distinct observed marginal RN/OT wages NOT_IDENTIFIED'))
            assert abs(q.provider_USD-(q.packages*COST+rn*RATE+ot*RATE))<1e-7
    save('supplement/OCCUPATION_SPECIFIC_PRICE_COEFFICIENTS.csv',ledger)
    print('Inherited family scenarios and separate occupational price coefficients computed; no policy refit.')


if __name__=='__main__':main()

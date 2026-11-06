"""Portable aggregate checks. Python standard library only; no patient data."""
from pathlib import Path
import csv, hashlib, json, math

ROOT=Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT/'data/aggregates'/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def main():
    count=0;worst=0.0
    def close(a,b,tol=1e-6):
        nonlocal count,worst
        err=abs(float(a)-float(b));count+=1;worst=max(worst,err)
        assert math.isfinite(err) and err<=tol,(err,a,b)
    rate=15.706068249154;cost=1078.5558464797732
    points=read('ALL_SENSITIVITY_POINTS.csv')
    lookup={(r['scenario'],r['policy'],r['metric']):r for r in points}
    def val(sc,pol,met):
        r=lookup[sc,pol,met]
        return float(r['estimate']) if r['estimate'] else None
    for r in points:
        if r['policy']!='paired_difference' or not r['estimate']:continue
        sc=r['scenario'];met=r['metric']
        a,b=('frozen2018_function','updated2020_function') if '_update_' in sc else ('S0-R','S1-R')
        x,y=val(sc,a,met),val(sc,b,met)
        if x is not None and y is not None:close(r['estimate'],y-x)
    for sc in sorted({r['scenario'] for r in points}):
        policies=('frozen2018_function','updated2020_function') if '_update_' in sc else ('S0-R','S1-R')
        for pol in policies:
            get=lambda k:val(sc,pol,k)
            n,h=get('packages'),get('inquiry_h')
            close(get('patient_contact_h'),10*n)
            close(get('patient_total_h'),10*n+h)
            for met,base,travel in [('RN_h',8*n+h,'travel_RN_h'),('OT_h',11.5*n,'travel_OT_h')]:
                if get(met) is not None and get(travel) is not None:close(get(met),base+get(travel))
            if get('provider_USD') is not None:
                close(get('provider_USD'),cost*n+rate*(h+get('travel_RN_h')+get('travel_OT_h')))
            if get('gap_reached') is not None:close(get('gap_unserved'),get('gap_population')-get('gap_reached'))
            close(get('eligible_unserved'),get('eligible_mass')-n)
    close(val('2018_equal500','paired_difference','gap_reached'),17.403831131,1e-8)
    close(val('2018_fixed500','S1-R','packages'),499)
    close(val('2020_historical299','paired_difference','gap_reached'),7.1282433038,1e-8)
    close(val('2020_equal500','paired_difference','gap_reached'),0)
    close(val('2020_fixed500','S1-R','packages'),500)
    for r in read('FEASIBILITY_ALL_DRAWS.csv'):
        assert int(r['attempted'])==5000 and int(r['computation_failures'])==0
        assert int(r['requested_target_mass_feasible'])+int(r['target_mass_shortfall'])==5000
    flow=[r for r in read('FOLLOWUP2020_FLOW_AND_ELIGIBILITY.csv') if r['section']=='current_eligibility_partition']
    close(sum(int(r['n']) for r in flow),2433)
    close(sum(float(r['weighted_per_original1000']) for r in flow),1000)
    for r in read('OCCUPATION_SPECIFIC_PRICE_COEFFICIENTS.csv'):
        close(r['reference_total_USD'],float(r['fixed_complete_package_cost_USD'])+
          float(r['additional_RN_h_coefficient'])*float(r['reference_RN_rate_USD'])+
          float(r['additional_OT_h_coefficient'])*float(r['reference_OT_rate_USD']))
    for r in read('FAMILY_PARTICIPATION_CURRENT.csv'):
        if r['design']!='community_WR':continue
        n=val(r['scenario'],r['policy'],'packages');h=val(r['scenario'],r['policy'],'inquiry_h')
        close(r['total_family_participation_h'],float(r['programme_family_h_per_package'])*n+float(r['inquiry_family_fraction'])*h)
    hashes=0
    if (ROOT/'PACKAGE_MANIFEST.csv').exists():
        for r in read('PACKAGE_MANIFEST.csv'):
            f=ROOT/r['path']
            assert f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256'],r['path']
            hashes+=1
    print(json.dumps(dict(passed=True,arithmetic_checks=count,maximum_error=worst,
      package_hashes_checked=hashes,scope='Aggregate arithmetic and file integrity; not patient-level rerun'),indent=2))


if __name__=='__main__':main()

from engine import *
from extensions import evaluate as expand, EM

UNITS={'packages':'complete packages / original2018 1000','eligible_mass':'weighted candidates / original2018 1000',
 'gap_reached':'opportunities / original2018 1000','I_total':'ordinal IADL index units / original2018 1000',
 'B_total':'ordinal basic ADL index units / original2018 1000','provider_USD':'2024 US$ / original2018 1000'}

def interval(x):
    if not np.isfinite(x).all():return np.nan,np.nan
    return np.quantile(x,[.025,.975])

def main():
    d,b,d0,d20,e=load();w=1000*d.weight.to_numpy()/d.weight.sum()
    v,pr,dg,sets=scenarios(d,b,d0,d20,e,w,True)
    sources={design:dict(np.load(R/'private'/f'{design}.npz')) for design in ['community_WR','county_WR']}
    point=[];ci=[];feas=[];profiles=[];profile_ci=[];hide_all={}
    # Cross-implementation contrasts can have smaller margins than either
    # implementation versus S0. Protect the newly published comparator too,
    # otherwise subtracting its arm from the inherited target arm defeats masking.
    byname={x[0]:x for x in sets};cross_guard={}
    for mode in ['paid','fixed']:
        target=byname['query_target_5_'+mode]
        for comparator in ['universal','union']:
            name='query_'+comparator+'_5_'+mode;other=byname[name]
            cross_guard[name]=masks(target[1],target[2],target[3][1].a,other[3][1].a)
    profile_names=['opportunities','gap_opportunities','B_total','I_total','family_opportunities','rural_opportunities',
                   *['tier'+str(j) for j in range(4)],'family_time_observed_mass','recorded_family_hours',*['needs_'+x for x in TASKS]]
    for i,(name,dm,ww,objs,t,k) in enumerate(sets):
        hidden=masks(dm,ww,objs[1].a,objs[0].a)
        hidden.update(cross_guard.get(name,set()))
        # Travel cost is an invertible function of rural allocation. Suppress both
        # arms' rural-dependent ledgers where a protected exchange complement exists.
        if t and 'rural_reached' in hidden:hidden.update(['RN_h','OT_h','provider_USD','travel_RN_h','travel_OT_h'])
        hide_all[name]=sorted(hidden)
        labels=['frozen2018_function','updated2020_function'] if '_update_' in name else ['S0-R','S1-R']
        for j,metric in enumerate(MET):
            protected=metric in hidden
            for a,label in [(0,labels[0]),(1,labels[1]),(2,'paired_difference')]:
                estimate=v[i,1,j]-v[i,0,j] if a==2 else v[i,a,j]
                row=dict(scenario=name,policy=label,metric=metric,estimate=np.nan if protected else estimate,
                    requested_capacity=k,denominator='original2018 weighted1000',status='SUPPRESSED_COMPLEMENT' if protected else 'CURRENT_SENSITIVITY',
                    unit=UNITS.get(metric,'hours / original2018 1000' if metric.endswith('_h') else 'weighted opportunity or index total / original2018 1000'))
                point.append(row)
                for design,z in sources.items():
                    x=z['values'][:,i,1,j]-z['values'][:,i,0,j] if a==2 else z['values'][:,i,a,j]
                    lo,hi=interval(x)
                    ci.append(dict(row,design=design,lower=np.nan if protected else lo,upper=np.nan if protected else hi,
                                   attempted=5000,valid=int(np.isfinite(x).sum()),estimand='all-draw realised feasible allocation; no target-failure deletion'))
        for design,z in sources.items():
            dd=z['diagnostics'][:,i]
            feas.append(dict(scenario=name,design=design,attempted=5000,
                 source_mass_point=dg[i,0],source_mass_lower=np.quantile(dd[:,0],.025),source_mass_upper=np.quantile(dd[:,0],.975),
                 requested_target_mass_feasible=int(dd[:,1].sum()),target_mass_shortfall=int((dd[:,1]==0).sum()),
                 S0_original_resource_feasible=int(dd[:,2].sum()),S1_original_resource_feasible=int(dd[:,3].sum()),
                 computation_failures=0,S1_max_queried_targets=int(dd[:,5].max()),
                 all_draws_retained=True))
        fr=[np.maximum(objs[1].a-objs[0].a,0),np.maximum(objs[0].a-objs[1].a,0),np.minimum(objs[1].a,objs[0].a),1-np.maximum(objs[1].a,objs[0].a)]
        exchange_small=any(small(((ww*z)>1e-8).sum()) for z in fr[:2])
        for ig,(group,frac,pvals) in enumerate(zip(['entrant','displaced','retained','unserved_both'],fr,pr[i])):
            sel=ww*frac>1e-8;raw_n=int(sel.sum())
            for j,metric in enumerate(profile_names):
                h=exchange_small or small(raw_n)
                if metric in ['family_opportunities','family_time_observed_mass','recorded_family_hours']:
                    h |= 'family_reached' in hidden or 'family_hours_known_mass' in hidden
                if metric=='rural_opportunities':h |= 'rural_reached' in hidden
                if metric.startswith('tier'):
                    cat=dm.f['tier']==int(metric[-1]);h|=small((sel&cat).sum()) or small((sel&~cat).sum())
                if metric.startswith('needs_'):
                    cat=dm.f['x'][:,TASKS.index(metric[6:])]>=3
                    h |= small((sel&cat).sum()) or small((sel&~cat).sum())
                profiles.append(dict(scenario=name,group=group,metric=metric,estimate=np.nan if h else pvals[j],
                                     source_n=np.nan if h else raw_n,status='SUPPRESSED_COMPLEMENT' if h else ('EMPTY_EXCHANGE' if raw_n==0 else 'OBSERVED_COMPOSITION_MODEL_OPPORTUNITIES')))
                for design,z in sources.items():
                    xx=z['profiles'][:,i,ig,j];lo,hi=interval(xx)
                    profile_ci.append(dict(profiles[-1],design=design,lower=np.nan if h else lo,
                                           upper=np.nan if h else hi,attempted=5000,valid=int(np.isfinite(xx).sum())))
    save('ALL_SENSITIVITY_POINTS.csv',point);save('ALL_PAIRED_UNCERTAINTY.csv',ci)
    save('FEASIBILITY_ALL_DRAWS.csv',feas);save('PATIENT_FAMILY_TASK_EXCHANGES.csv',profiles)
    save('PATIENT_FAMILY_TASK_PAIRED_INTERVALS.csv',profile_ci)
    (R/'logs/DISCLOSURE_MASKS.json').write_text(json.dumps(hide_all,indent=2))
    pts=pd.DataFrame(point);cis=pd.DataFrame(ci);pro=pd.DataFrame(profiles)
    files={
      'FOLLOWUP2020_MAIN500_EQUAL.csv':['2020_equal500','2020_paid500'],
      'FOLLOWUP2020_MAIN500_FIXED_RESOURCE.csv':['2020_fixed500'],
      'FOLLOWUP2020_ELIGIBLE50pct.csv':['2020_eligible50'],
      'FOLLOWUP2020_PRIORITY_UPDATE.csv':['2020_update_500','2020_update_eligible50'],
      'RURAL500_RESOURCE_COMPARISON.csv':['2018_equal500','2018_paid500','2018_fixed500','2018_rural_equal500','2018_rural_paid500','2018_rural_fixed500'],
      'FOLLOWUP2020_RURAL500_BOUNDED.csv':['2020_rural_equal500','2020_rural_paid500','2020_rural_fixed500']}
    for file,names in files.items():save(file,pts[pts.scenario.isin(names)])
    save('AGE65_500_SENSITIVITY.csv',cis[cis.scenario.str.startswith('age65')])
    save('QUERY_IMPLEMENTATION_500.csv',cis[cis.scenario.str.startswith('query_')])
    save('FOLLOWUP2020_PAIRED_UNCERTAINTY.csv',cis[cis.scenario.str.startswith('2020')])
    save('FOLLOWUP2020_ENTRANTS_FAMILY_TASKS.csv',pro[pro.scenario.str.startswith('2020')])
    # Proper paired contrasts between inquiry implementations, not independent CIs.
    rows=[];names=[s[0] for s in sets]
    for mode in ['paid','fixed']:
        i=names.index('query_target_5_'+mode)
        for comparator in ['universal','union']:
            j=names.index('query_'+comparator+'_5_'+mode)
            for ix,met in enumerate(MET):
                hide=met in hide_all[names[i]] or met in hide_all[names[j]]
                for design,z in sources.items():
                    x=z['values'][:,i,1,ix]-z['values'][:,j,1,ix];lo,hi=interval(x)
                    rows.append(dict(mode=mode,contrast='target_minus_'+comparator,metric=met,design=design,
                      estimate=np.nan if hide else v[i,1,ix]-v[j,1,ix],lower=np.nan if hide else lo,upper=np.nan if hide else hi,
                      attempted=5000,valid=5000,status='SUPPRESSED_COMPLEMENT' if hide else 'PAIRED_SAME_SAMPLE'))
    save('QUERY_IMPLEMENTATION_PAIRED_CONTRASTS.csv',rows)
    # Resource expansion conditional on observed recipient vectors.
    ex,aa=expand(d0,w);rows=[]
    for design in sources:
        draws=np.load(R/'private'/f'expansion_{design}.npz')['values']
        for i,(name,o,ref) in enumerate(aa):
            if o is None:continue
            hidden=masks(d0,w,o.a,ref)
            for j,metric in enumerate(EM):
                # Suppress identifying rural resource complements, but publish
                # binary feasibility and conservative pre-query bounds separately.
                h=('rural_reached' in hidden and metric in ['rural_opportunities','RN_h','OT_h','USD','additional_RN_h','additional_OT_h','additional_USD'])
                h |= ('family_reached' in hidden and metric=='family_reached')
                x=draws[:,i,j];valid=np.isfinite(x)
                lo,hi=interval(x)
                rows.append(dict(scenario=name,metric=metric,design=design,estimate=np.nan if h else ex[i,j],
                     lower=np.nan if h else lo,upper=np.nan if h else hi,attempted=5000,valid=int(valid.sum()),
                     failed=int((~valid).sum()),status='SUPPRESSED_COMPLEMENT' if h else 'CONDITIONAL_RECIPIENT_VECTOR',
                     interval_scope='all attempted; undefined if any failed target'))
    ee=pd.DataFrame(rows);save('RURAL500_EQUITY_AND_PROTECTION.csv',ee)
    save('RURAL500_ROLE_BOTTLENECK.csv',ee[ee.metric.str.contains('topup_feasible|additional_|packages|RN_h|OT_h|USD')])
    save('RURAL500_NO_DISPLACEMENT_EXPANSION.csv',ee[ee.scenario.str.contains('union')])
    print('Public aggregates and paired intervals exported with linked disclosure masks.',flush=True)

if __name__=='__main__':main()

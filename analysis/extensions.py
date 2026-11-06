"""Conditional resource restoration under the SAME frozen S1 order."""
from engine import *
import time

EM=['packages','rural_opportunities','RN_h','OT_h','USD','additional_RN_h','additional_OT_h','additional_USD',
    'query_h','patient_h','gap_reached','I_total','family_reached','severity_retention',
    'package_restored','rural_restored','topup_feasible_RN','topup_feasible_OT','topup_feasible_budget',
    'topup_feasible_RN_OT','topup_feasible_all','conditional_prequery_guarantee_extra_RN',
    'conditional_prequery_guarantee_extra_OT','conditional_prequery_guarantee_extra_USD']

def evaluate(dm,w):
    pl=Planner(dm,w);s0=pl.fixed('S0-R',.5);s1=pl.fixed('S1-R',.5)
    n0=w@s0.a;r0=(w*s0.a)@dm.rural
    # Sequentially acquire additional boundary answers only as they become needed.
    q=s1.q.copy();rest=None
    for k in range(int(round(n0)),int(min(500,w.sum()))+1):
        q|=pl.at(k)[2];a=pl.decide(k,q)
        if (w*a)@dm.rural>=r0-1e-7:
            rest=Allocation(a,q,(w@q)/12);break
    cases=[('rural_S0_full500',pl.equal(500,'S0-R'),np.zeros(len(w))),
           ('rural_S1_full500_known',pl.equal(500,'S1-R'),np.zeros(len(w))),
           ('rural_S1_full500_paid',pl.equal(500,'S1-R',True),np.zeros(len(w))),
           ('rural_S1_restore_S0_fixed_packages_and_rural',rest,s0.a),
           ('rural_union_fixed_original',Allocation(np.maximum(s0.a,s1.a),s1.q,s1.h),s0.a)]
    a0=pl.equal(500,'S0-R');a1=pl.equal(500,'S1-R',True)
    cases.append(('rural_union_full500_original',Allocation(np.maximum(a0.a,a1.a),a1.q,a1.h),a0.a))
    values=[];aa=[]
    for name,o,ref in cases:
        if o is None:
            values.append(np.full(len(EM),np.nan));aa.append((name,None,ref));continue
        n=w@o.a;r=(w*o.a)@dm.rural;use=resource(w,o.a,dm.rural,o.h,.5);extra=np.maximum(use-CEILING,0)
        feas=[]
        for ix in [[0],[1],[2],[0,1],[0,1,2]]:
            cc=CEILING.copy();cc[ix]+=extra[ix];feas.append(float(np.all(use<=cc+1e-7)))
        base=(w*s0.a)@dm.f['N'];ret=(w*o.a)@dm.f['N']/base
        # Pre-query upper bound: at most all selected opportunities can be rural.
        # This is a safe budget envelope, not the conditional minimum realised above.
        worst=np.array([8*n+2*min(n,w@dm.rural)+o.h,11.5*n+3*min(n,w@dm.rural),
                        COST*n+RATE*(5*min(n,w@dm.rural)+o.h)])
        values.append([n,r,*use,*extra,o.h,10*n+o.h,(w*o.a)@dm.gap,(w*o.a)@dm.f['I'],(w*o.a)@dm.family,
                       ret,float(n>=n0-1e-7),float(r>=r0-1e-7),*feas,*np.maximum(worst-CEILING,0)])
        aa.append((name,o,ref))
    return np.asarray(values),aa

def main():
    d,b,d0,d20,e=load();w=1000*d.weight.to_numpy()/d.weight.sum()
    v,aa=evaluate(d0,w);np.savez_compressed(R/'private/expansion_points.npz',values=v,names=[x[0] for x in aa],metrics=EM)
    start=time.monotonic()
    for design in ['community_WR','county_WR']:
        dest=R/'private'/f'expansion_{design}.npz'
        if dest.exists():continue
        out=np.empty((5000,*v.shape))
        for rep,ww in old.weights(d,design):
            out[rep],_=evaluate(d0,ww)
            if (rep+1)%1000==0:print(f'expansion {design} {rep+1} elapsed {time.monotonic()-start:.1f}s',flush=True)
        np.savez_compressed(dest,values=out)
    print('Conditional restoration vectors completed; no third ranking introduced.',flush=True)

if __name__=='__main__':main()

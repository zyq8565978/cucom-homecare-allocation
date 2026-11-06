"""Frozen nine-capacity S0/S1 analysis, information cost and paired uncertainty."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import capacity_model as m
from inputs import load, output_root
from resampling import weights

CAPACITIES = list(range(100,901,100))
MODES = ['known_equal','paid_equal','fixed_resource']

def evaluate(dm, w):
    values, selections = [], []
    for k in CAPACITIES:
        ref = m.rank(dm.f['score'], w, k)
        for mode in MODES:
            if mode == 'fixed_resource':
                target, q, h = m.plan(dm.f, w, k)
            else:
                target, q = k, m.query(dm.f, w, k)
                h = float(w@q)/12
            a = m.decide(dm.f,w,target,dm.g,q)['S1-R']
            h = 0 if mode == 'known_equal' else h
            values.append([dm.metrics(w,ref,ref,0),dm.metrics(w,a,ref,h)])
            selections.append((k,mode,a,ref,q,h))
    return np.asarray(values), selections

def main():
    d,_ = load(); dm = m.Domain(d); root = output_root()
    w = 1000*dm.w0/dm.w0.sum()
    point, selections = evaluate(dm,w)
    np.save(root/'private/capacity_points.npy',point)
    points, masks = [], {}
    for i,(k,mode,a,ref,q,h) in enumerate(selections):
        for j,(label,v) in enumerate([('S0-R',ref),('S1-R',a)]):
            row, hidden = m.safe_point(dm,w,v,ref,point[i,j],dict(capacity=k,mode=mode,policy=label))
            points.append(row); masks[k,mode,label] = hidden
    pd.DataFrame(points).to_csv(root/'CAPACITY_RECOMPUTED.csv',index=False)
    summaries = []
    contrasts = ['packages','gap_reached','gap_coverage_percent','gap_unserved','B_total','I_total',
                 'family_reached','rural_reached','RN_h','OT_h','provider_USD','patient_total_h','inquiry_h',
                 'tier0_packages','tier1_packages','tier2_packages','tier3_packages']
    for design in ['community_WR','county_WR']:
        draws = np.empty((5000,*point.shape))
        for rep,wr in weights(d,design):
            draws[rep],_ = evaluate(dm,wr)
            if (rep+1)%1000 == 0: print(f'{design}: capacity {rep+1}/5000',flush=True)
        assert np.isfinite(draws).all()
        np.savez_compressed(root/'private'/f'capacity_{design}.npz',values=draws)
        for i,(k,mode,a,ref,q,h) in enumerate(selections):
            for metric in contrasts:
                j = m.METRICS.index(metric)
                x = draws[:,i,1,j]-draws[:,i,0,j]
                lo,hi = np.quantile(x,[.025,.975])
                hidden = metric in masks[k,mode,'S1-R']
                summaries.append(dict(design=design,capacity=k,mode=mode,metric=metric,
                    estimate=np.nan if hidden else point[i,1,j]-point[i,0,j],
                    lower=np.nan if hidden else lo,upper=np.nan if hidden else hi,
                    replicates=5000,suppressed=hidden))
    pd.DataFrame(summaries).to_csv(root/'PAIRED_CAPACITY_RECOMPUTED.csv',index=False)

if __name__ == '__main__': main()

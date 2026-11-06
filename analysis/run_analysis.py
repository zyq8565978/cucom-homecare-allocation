"""Run the frozen analyses using authorised files; no raw records are published."""
import argparse
import os
import runpy
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config',required=True,help='Private JSON input configuration outside the public repository')
    ap.add_argument('--component',choices=['capacity','followup','all'],default='all')
    args = ap.parse_args()
    os.environ['CUCOM_CONFIG'] = str(Path(args.config).resolve())
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    from engine import load, scenarios, MET, R, np, old, json
    if args.component in ['capacity','all']:
        import capacity_analysis
        capacity_analysis.main()
    if args.component in ['followup','all']:
        d,b,d0,d20,e = load(); w = 1000*d.weight.to_numpy()/d.weight.sum()
        point,prof,diag,sets = scenarios(d,b,d0,d20,e,w,True)
        names = [s[0] for s in sets]
        np.savez_compressed(R/'private/points.npz',values=point,profiles=prof,diagnostics=diag,names=names)
        (R/'logs/SCENARIOS.json').write_text(json.dumps(names,indent=2))
        for design in ['community_WR','county_WR']:
            v=np.empty((5000,*point.shape));pr=np.empty((5000,*prof.shape));dg=np.empty((5000,*diag.shape))
            for rep,ww in old.weights(d,design):
                v[rep],pr[rep],dg[rep],nn = scenarios(d,b,d0,d20,e,ww)
                assert nn == names and np.isfinite(v[rep]).all()
                if (rep+1)%1000==0: print(f'{design}: follow-up {rep+1}/5000',flush=True)
            np.savez_compressed(R/'private'/f'{design}.npz',values=v,profiles=pr,diagnostics=dg)
        import extensions
        extensions.main()
        import publish
        publish.main()
        import participation_and_prices
        participation_and_prices.main()
        import bottlenecks
        bottlenecks.main()
    print('Completed. Restricted arrays remain in the private output directory.')

if __name__ == '__main__': main()

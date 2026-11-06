from engine import *

def one(dm,w):
    pl=Planner(dm,w);rows=[]
    for pol in ['S0-R','S1-R']:
        o=pl.fixed(pol,.5);k=round(w@o.a)+1
        q=o.q|pl.at(k)[2] if pol=='S1-R' else pl.zero
        h=w@q/12 if pol=='S1-R' else 0
        a=pl.decide(k,q) if pol=='S1-R' else pl.at(k)[0]
        use=resource(w,a,dm.rural,h,.5)
        rows.append([*(use>CEILING+1e-7),k,w@o.a])
    return np.array(rows)

def main():
    d,b,dm,df,e=load();w=1000*d.weight.to_numpy()/d.weight.sum();pt=one(dm,w);rows=[]
    for design in ['community_WR','county_WR']:
        data=np.empty((5000,2,5))
        for rep,ww in old.weights(d,design):data[rep]=one(dm,ww)
        for i,pol in enumerate(['S0-R','S1-R']):
            for j,role in enumerate(['RN','OT','budget']):
                rows.append(dict(design=design,policy=pol,resource=role,point_next_package_violates=bool(pt[i,j]),
                   replicates_next_package_violates=int(data[:,i,j].sum()),attempted=5000,
                   interpretation='next integer package under the same paid inquiry protocol; not posterior probability'))
    save('RURAL_NEXT_PACKAGE_BINDING_DIAGNOSTICS.csv',rows)
    print('Next-package role constraints evaluated on all 10,000 paired samples.')

if __name__=='__main__':main()

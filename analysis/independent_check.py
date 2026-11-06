"""Independent grouped-lottery implementation, resources and nonanticipation tests."""
from engine import *
import time

class Independent:
    def __init__(self,dm,w):
        self.dm=dm;self.w=w
        x=dm.d[p.COLS].to_numpy(float)
        self.B=(x[:,:5]-1).sum(1);self.I=(x[:,5:]-1).sum(1)
        self.tier=np.where((x[:,:5]==4).any(1),3,np.where((x[:,:5]>=3).any(1),2,np.where((x[:,5:]>=3).any(1),1,0)))
        self.need=(x>=3).any(1)
        # Group tuple identities rather than using the original encoded scores.
        self.group={}
        for name,z in [('block',np.c_[self.tier,self.B]),('function',np.c_[self.tier,self.B,self.I])]:
            vals,inv=np.unique(z,axis=0,return_inverse=True)
            self.group[name]=(inv,len(vals))
        self.cached={}

    def rank(self,name,k):
        inv,n=self.group[name];mass=np.bincount(inv,weights=self.w,minlength=n)
        before=mass.sum()-np.cumsum(mass)
        return np.clip(np.divide(k-before,mass,out=np.zeros(n),where=mass>0),0,1)[inv]

    def at(self,k):
        k=min(k,self.w.sum())
        if k not in self.cached:
            ref=self.rank('function',k);f=self.rank('block',k)
            part=(f>1e-9)&(f<1-1e-9)&(self.w>0)
            q=part&self.need if part.sum()>1 else np.zeros(len(self.w),bool)
            self.cached[k]=(ref,part,q)
        return self.cached[k]

    def decide(self,k,q):
        ref,part,_=self.at(k);a=ref.copy()
        answers=np.full(len(a),np.nan);answers[~self.need]=0;answers[q]=self.dm.g[q]
        known=part&np.isfinite(answers)
        if known.any():
            vv,ii=np.unique(np.c_[answers[known],self.I[known]],axis=0,return_inverse=True)
            mass=np.bincount(ii,weights=self.w[known],minlength=len(vv));before=mass.sum()-mass.cumsum()
            quota=self.w[known]@ref[known]
            a[known]=np.clip(np.divide(quota-before,mass,out=np.zeros(len(mass)),where=mass>0),0,1)[ii]
        return a

    def use(self,a,h,t):
        z=self.w*a;n=z.sum();r=z@self.dm.rural
        return np.array([8*n+4*t*r+h,11.5*n+6*t*r,n*COST+(10*t*r+h)*RATE])

    def fixed(self,pol,t=0,mins=5,method='target'):
        w=self.w;upper=min(500,w.sum());ks=list(range(int(upper),-1,-1))
        if w.sum()<=upper+1e-8 and abs(w.sum()-round(w.sum()))>1e-8:ks=[w.sum()]+ks
        asked=np.zeros(len(w),bool)
        if method=='universal' and pol=='S1-R':asked=w>0
        if method=='union' and pol=='S1-R':
            for k in range(1,int(upper)+1):asked |= self.at(k)[2]
        for k in ks:
            a0,part,q=self.at(k)
            if pol=='S0-R':
                if np.all(self.use(a0,0,t)<=CEILING+1e-7):return a0,asked,0
                continue
            allasked=asked|q;h=w@allasked*mins/60
            if (q&~asked).any():
                rmin=(w[~part]*a0[~part])@self.dm.rural[~part]+max(0,w[part]@a0[part]-w[part]@(1-self.dm.rural[part]))
            else:rmin=(w*self.decide(k,asked))@self.dm.rural
            lower=np.array([8*k+4*t*rmin+h,11.5*k+6*t*rmin,k*COST+(10*t*rmin+h)*RATE])
            if np.any(lower>CEILING+1e-7):continue
            asked=allasked;a=self.decide(k,asked)
            if np.all(self.use(a,h,t)<=CEILING+1e-7):return a,asked,h
        raise AssertionError('independent feasibility failure')

def main():
    start=time.monotonic();d,b,d0,d20,e=load();w=1000*d.weight.to_numpy()/d.weight.sum()
    points,profiles,diag,sets=scenarios(d,b,d0,d20,e,w,True)
    n=0;maxerr=0.;leak=0
    def close(a,b):
        nonlocal n,maxerr
        err=float(np.max(np.abs(np.asarray(a)-np.asarray(b))));n+=1;maxerr=max(maxerr,err)
        assert err<1e-6,(err,n)
    # All point scenarios, including conservative queries and updated lists.
    for name,dm,ww,objs,t,k in sets:
        ind=Independent(dm,ww)
        if '_update_' in name:
            baseline=Independent(Frame(d.loc[e].reset_index(drop=True)),ww)
            close(baseline.at(k)[0],objs[0].a)
            close(ind.at(k)[0],objs[1].a)
            continue
        for ip,pol in enumerate(['S0-R','S1-R']):
            mins=int(name.split('_')[2]) if name.startswith('query_') else 5
            method=name.split('_')[1] if name.startswith('query_') else 'target'
            if 'fixed' in name:a,q,h=ind.fixed(pol,t,mins,method)
            else:
                q=ind.at(k)[2]
                if pol=='S0-R':a=ind.at(k)[0];q=np.zeros(len(ww),bool);h=0
                else:
                    if method=='universal':q=ww>0
                    if method=='union':
                        q=np.zeros(len(ww),bool)
                        for target in range(1,int(k)+1):q|=ind.at(target)[2]
                    a=ind.decide(k,q);h=ww@q*mins/60 if 'paid' in name else 0
            close(a,objs[ip].a);close(q.astype(int),objs[ip].q.astype(int));close(h,objs[ip].h)
        if '_update_' not in name:
            changed=Frame(dm.d.copy());changed.g=dm.g.copy()
            unasked=~objs[1].q
            changed.g[unasked]=np.where(np.isfinite(changed.g[unasked]),1-np.nan_to_num(changed.g[unasked]),1)
            pl=Planner(changed,ww)
            if 'fixed' in name:alter=pl.fixed('S1-R',t,mins,method)
            else:alter=pl.equal(k,'S1-R','paid' in name,mins,method)
            close(alter.a,objs[1].a);close(alter.q.astype(int),objs[1].q.astype(int));close(alter.h,objs[1].h);leak+=1
    # All 10,000 replicates: independent allocations for two current-2020
    # capacities plus both rural fixed-resource implementations.
    for design in ['community_WR','county_WR']:
        dat=np.load(R/'private'/f'{design}.npz');v=dat['values'];names=[s[0] for s in sets]
        for rep,wr in old.weights(d,design):
            for dm,ww,prefix in [(d0,wr,'2018'),(d20,wr[e],'2020')]:
                ind=Independent(dm,ww)
                if prefix=='2020':
                    for k,label in [(500,'equal500'),(ww.sum()/2,'eligible50')]:
                        i=names.index(prefix+'_'+label)
                        q=ind.at(k)[2]
                        for ip,a in enumerate([ind.at(k)[0],ind.decide(k,q)]):
                            y=(ww*a)@dm.matrix
                            close(v[rep,i,ip,[0,3,6,7,8,9]],[ww@a,y[0],y[1],y[2],y[3],y[4]])
                # At first 250 draws per design, fully independent rural scans;
                # for every draw validate the resource ledger and feasibility.
                if rep<250:
                    i=names.index(prefix+'_rural_fixed500')
                    for ip,pol in enumerate(['S0-R','S1-R']):
                        a,q,h=ind.fixed(pol,.5);y=(ww*a)@dm.matrix
                        close(v[rep,i,ip,[0,3,6,7,8,9,10]],[ww@a,y[0],y[1],y[2],y[3],y[4],h])
            if (rep+1)%1000==0:print(f'independent {design} {rep+1}',flush=True)
        for i,(name,dm,ww,objs,t,k) in enumerate(sets):
            z=v[:,i];nn=z[:,:,0];rh=z[:,:,9];h=z[:,:,10]
            close(z[:,:,11],8*nn+4*t*rh+h);close(z[:,:,12],11.5*nn+6*t*rh)
            close(z[:,:,13],COST*nn+RATE*(10*t*rh+h))
            close(z[:,:,15],10*nn+h)
            assert np.all(z[:,:,3]<=z[:,:,2]+1e-7)
            if 'fixed' in name:assert np.all(z[:,:,11:14]<=CEILING+1e-6)
        # Same paired sequence as the separately computed capacity analysis.
        oldz=np.load(R/'private'/f'capacity_{design}.npz')['values']
        j=names.index('2018_equal500')
        # Nine-capacity layout 3 modes * 9 capacities; equal500 index 4*3.
        close(v[:,j,:,3],oldz[:,12,:,m.METRICS.index('gap_reached')])
    # Independently reconstitute both rural full-package and union ledgers.
    ex=np.load(R/'private/expansion_points.npz');enames=list(ex['names']);em=list(ex['metrics'])
    ind=Independent(d0,w);q=ind.at(500)[2]
    ref=ind.at(500)[0];alt=ind.decide(500,q);h=w@q/12
    for name,a,hh in [('rural_S0_full500',ref,0),('rural_S1_full500_known',alt,0),
                      ('rural_S1_full500_paid',alt,h),('rural_union_full500_original',np.maximum(ref,alt),h)]:
        row=ex['values'][enames.index(name)];use=ind.use(a,hh,.5)
        close(row[[em.index(x) for x in ['RN_h','OT_h','USD']]],use)
        close(row[[em.index(x) for x in ['additional_RN_h','additional_OT_h','additional_USD']]],np.maximum(use-CEILING,0))
        close(row[em.index('packages')],w@a)
    result=dict(passed=True,numeric_checks=n,max_absolute_error=maxerr,nonanticipation_scenarios=leak,
      current2020_independent_draws=10000,rural_independent_draws_per_design=250,
      all_draw_resource_checks=10000,seconds=time.monotonic()-start)
    (R/'logs/INDEPENDENT_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

if __name__=='__main__':main()

"""Two inherited policies; explicit costs of acquiring information. Local inputs only."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import sys, hashlib, json
import numpy as np
import pandas as pd
sys.dont_write_bytecode=True
from inputs import output_root
import policies as p
import capacity_model as m
import resampling as old
R=output_root()
RATE=p.RATE; COST=p.COST; CEILING=np.array([4000.,5750.,500*COST])
MET=['packages','eligible_mass','gap_population','gap_reached','gap_unserved','eligible_unserved',
     'B_total','I_total','family_reached','rural_reached','inquiry_h','RN_h','OT_h','provider_USD',
     'patient_contact_h','patient_total_h','tier0_packages','tier1_packages','tier2_packages','tier3_packages',
     'family_hours_known_mass','recorded_family_month_hours','query_mass','travel_RN_h','travel_OT_h']
TASKS=p.ITEMS

def save(name,rows):
    dest=R/name;dest.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(dest,index=False,encoding='utf-8-sig',float_format='%.15g')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def load():
    d,b=p.load();d=d.reset_index(drop=True);b=b.reset_index(drop=True)
    assert d.ID.equals(b.ID) and len(d)==2433
    e=b.eligible_current.to_numpy(bool)
    return d,b,Frame(d),Frame(b.loc[e].reset_index(drop=True)),e

class Frame:
    def __init__(self,d):
        self.d=d;self.f=p.features(d);self.g=p.gap_answers(d)
        self.rural=d.rural.eq(1).to_numpy(float)
        self.gap=d.gap_known.to_numpy(float);self.family=d.family_confirmed.to_numpy(float)
        c=d.family_recorded_month_hours.to_numpy(float)
        self.ck=np.isfinite(c).astype(float);self.c=np.nan_to_num(c)
        self.matrix=np.column_stack([self.gap,self.f['B'],self.f['I'],self.family,self.rural,
          *[(self.f['tier']==j) for j in range(4)],self.ck,self.c])

class Allocation:
    def __init__(self,a,q,h,attempted=0,skipped=0):
        self.a=a;self.q=q;self.h=h;self.attempted=attempted;self.skipped=skipped

class Planner:
    def __init__(self,dm,w):
        self.dm=dm;self.w=w;self.f=dm.f
        self.mass=w.sum();self.zero=np.zeros(len(w),bool)
        self.cache={}

    def at(self,k):
        k=min(float(k),self.mass)
        if k not in self.cache:
            a0=m.rank(self.f['score'],self.w,k)
            fraction=m.rank(self.f['block'],self.w,k)
            part=(fraction>1e-9)&(fraction<1-1e-9)&(self.w>0)
            q=(part & self.f['need']) if part.sum()>1 else self.zero.copy()
            self.cache[k]=(a0,part,q)
        return self.cache[k]

    def decide(self,k,q):
        a0,part,_=self.at(k);a=a0.copy()
        answer=p.reveal(self.dm.g,q,self.f['need'])
        known=part & np.isfinite(answer)
        if known.any():
            quota=self.w[known]@a0[known]
            a[known]=m.rank(16*answer[known].astype(int)+self.f['I'][known],self.w[known],quota)
        assert abs(self.w@a-min(k,self.mass))<1e-6
        return a

    def equal(self,k,policy,paid=False,minutes=5,method='target'):
        k=min(k,self.mass);a0,_,q=self.at(k)
        if policy=='S0-R':return Allocation(a0,self.zero,0)
        if method=='universal':q=self.w>0
        if method=='union':q=p.union_query(self.f,self.w,int(k))
        a=self.decide(k,q)
        return Allocation(a,q,float(self.w@q)*minutes/60 if paid else 0)

    def fixed(self,policy,travel=0,minutes=5,method='target',ceiling=None):
        cap=CEILING if ceiling is None else np.asarray(ceiling)
        upper=min(500.,self.mass,cap[0]/8,cap[1]/11.5,cap[2]/COST)
        targets=list(range(int(np.floor(upper+1e-9)),-1,-1))
        if self.mass<=upper+1e-8 and abs(self.mass-round(self.mass))>1e-8:targets=[self.mass]+targets
        q=self.zero.copy();h=0.;attempted=skipped=0
        if policy=='S1-R' and method=='universal':q=self.w>0
        if policy=='S1-R' and method=='union':q=p.union_query(self.f,self.w,int(upper))
        for k in targets:
            a0,part,needed=self.at(k)
            if policy=='S0-R':
                if np.all(resource(self.w,a0,self.dm.rural,0,travel)<=cap+1e-7):return Allocation(a0,q,0,attempted,skipped)
                continue
            proposed=q|needed
            hh=float(self.w@proposed)*minutes/60
            # Lower bound before revealing ANY new answer. If all needed answers
            # are already acquired, use their actual permitted allocation.
            if not (needed & ~q).any():
                candidate=self.decide(k,q)
                lower_rural=(self.w*candidate)@self.dm.rural
            else:
                fixed=~part
                quota=self.w[part]@a0[part]
                urban=self.w[part]@(1-self.dm.rural[part])
                lower_rural=(self.w[fixed]*a0[fixed])@self.dm.rural[fixed]+max(0.,quota-urban)
            bound=np.array([8*k+4*travel*lower_rural+hh,11.5*k+6*travel*lower_rural,
                            COST*k+RATE*(10*travel*lower_rural+hh)])
            if np.any(bound>cap+1e-7):skipped+=1;continue
            q=proposed;h=hh;attempted+=1
            a=self.decide(k,q)
            if np.all(resource(self.w,a,self.dm.rural,h,travel)<=cap+1e-7):
                return Allocation(a,q,h,attempted,skipped)
        raise AssertionError('No executable zero-package outcome')

def resource(w,a,rural,h=0,travel=0):
    n=w@a;r=(w*a)@rural
    return np.array([8*n+4*travel*r+h,11.5*n+6*travel*r,COST*n+RATE*(10*travel*r+h)])

def metrics(dm,w,obj,travel=0):
    a=obj.a;z=w*a;n=z.sum();y=z@dm.matrix;gpop=w@dm.gap
    rn,ot,cost=resource(w,a,dm.rural,obj.h,travel)
    return np.array([n,w.sum(),gpop,y[0],gpop-y[0],w.sum()-n,y[1],y[2],y[3],y[4],
       obj.h,rn,ot,cost,10*n,10*n+obj.h,*y[5:9],y[9],y[10],w@obj.q,
       4*travel*y[4],6*travel*y[4]])

def exchange(dm,w,a,b):
    rows=[]
    for v in [np.maximum(a-b,0),np.maximum(b-a,0),np.minimum(a,b),1-np.maximum(a,b)]:
        z=w*v;n=z.sum();y=z@dm.matrix
        rows.append([n,*y,*[(z@(dm.f['x'][:,j]>=3)) for j in range(10)]])
    return np.array(rows)

def small(n):return 0<int(n)<10

def masks(dm,w,a,b):
    en=w*np.maximum(a-b,0)>1e-8;de=w*np.maximum(b-a,0)>1e-8
    hidden=set();resources={'packages','eligible_mass','eligible_unserved','inquiry_h','query_mass','RN_h','OT_h','provider_USD','patient_contact_h','patient_total_h','travel_RN_h','travel_OT_h'}
    if any(small(s.sum()) for s in [en,de]):hidden.update(set(MET)-resources)
    for name,cat in [('family_reached',dm.family.astype(bool)),('rural_reached',dm.rural.astype(bool))]:
        if any(small((s&c).sum()) for s in [en,de] for c in [cat,~cat]):hidden.add(name)
    for j in range(4):
        c=dm.f['tier']==j
        if any(small((s&x).sum()) for s in [en,de] for x in [c,~c]):hidden.add('tier'+str(j)+'_packages')
    if any(small((s&c).sum()) for s in [en,de] for c in [dm.ck.astype(bool),~dm.ck.astype(bool)]):
        hidden.update(['family_hours_known_mass','recorded_family_month_hours'])
    return hidden

def scenarios(d,b,d0,d20,e,w,arrays=False):
    age=d.age.ge(65).to_numpy();da=Frame(d.loc[age].reset_index(drop=True))
    planners={'2018':Planner(d0,w),'2020':Planner(d20,w[e]),'age65':Planner(da,w[age])}
    sets=[]
    for pop,pl in planners.items():
        dm=pl.dm;ww=pl.w
        for mode in ['equal500','paid500','fixed500','eligible50']:
            if pop=='2018' and mode=='eligible50':continue
            k=500 if mode!='eligible50' else ww.sum()/2
            objs=[pl.fixed(pol) if mode=='fixed500' else pl.equal(k,pol,mode=='paid500') for pol in ['S0-R','S1-R']]
            sets.append((pop+'_'+mode,dm,ww,objs,0,k))
        if pop!='age65':
            for mode in ['rural_equal500','rural_paid500','rural_fixed500']:
                objs=[pl.fixed(pol,.5) if mode=='rural_fixed500' else pl.equal(500,pol,mode=='rural_paid500') for pol in ['S0-R','S1-R']]
                sets.append((pop+'_'+mode,dm,ww,objs,.5,500))
        if pop=='2020':
            f18=p.features(d.loc[e].reset_index(drop=True))
            for k,label in [(500,'500'),(ww.sum()/2,'eligible50')]:
                stale=m.rank(f18['score'],ww,min(k,ww.sum()))
                objs=[Allocation(stale,pl.zero,0),pl.equal(k,'S0-R')]
                sets.append(('2020_update_'+label,dm,ww,objs,0,k))
            sets.append(('2020_historical299',dm,ww,[pl.equal(299,x) for x in ['S0-R','S1-R']],0,299))
        if pop=='2018':
            for minute in [3,5,10]:
                for method in ['target','universal','union']:
                    for mode in ['paid','fixed']:
                        if mode=='paid':objs=[pl.equal(500,'S0-R'),pl.equal(500,'S1-R',True,minute,method)]
                        else:objs=[pl.fixed('S0-R'),pl.fixed('S1-R',0,minute,method)]
                        sets.append((f'query_{method}_{minute}_{mode}',dm,ww,objs,0,500))
    vals=[];prof=[];diag=[]
    for name,dm,ww,objs,t,k in sets:
        vals.append([metrics(dm,ww,o,t) for o in objs]);prof.append(exchange(dm,ww,objs[1].a,objs[0].a))
        diag.append([ww.sum(),float(ww.sum()>=k-1e-7),*(float(np.all(resource(ww,o.a,dm.rural,o.h,t)<=CEILING+1e-7)) for o in objs),
                     *(o.attempted for o in objs),*(o.skipped for o in objs)])
    return np.array(vals),np.array(prof),np.array(diag),sets if arrays else [x[0] for x in sets]

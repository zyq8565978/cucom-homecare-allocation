"""Two-policy capacity comparison; no treatment-effect model or policy selection."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.dont_write_bytecode=True
import policies as p
RULES=['S0-R','S1-R']
CAPS=list(range(100,901,100))
METRICS=['packages','gap_population','gap_reached','gap_gain','gap_coverage_percent','gap_unserved','all_unserved',
         'B_total','I_total','N_retained','B_change','I_change','entrants','displaced',
         'family_reached','family_gain','rural_reached','rural_gain','inquiry_h','RN_h','OT_h','provider_USD',
         'patient_contact_h','patient_total_h','family_participation_0_h','family_participation_5_h','family_participation_10_h',
         'old60_packages','old60_gap_reached','old60_B_total','old60_I_total','known_family_hours_recipient_mass',
         'recorded_family_month_hours','tier0_packages','tier1_packages','tier2_packages','tier3_packages']
METRICS += ['I_'+name+'_total' for name in ['housework','meals','shopping','finances','medication']]

def rank(score,w,k):
    """Preordered integer-score weighted lottery, equivalent to frozen p.rank."""
    mass=np.bincount(score,weights=w,minlength=int(score.max())+1)
    before=np.cumsum(mass[::-1])[::-1]-mass
    frac=np.clip(np.divide(k-before,mass,out=np.zeros(len(mass)),where=mass>0),0,1)
    return frac[score]

def query(f,w,k):
    a=rank(f['block'],w,k)
    part=(a>1e-9)&(a<1-1e-9)&(w>0)
    return part&f['need'] if part.sum()>1 else np.zeros(len(w),bool)

def plan(f,w,K):
    # Deliberately no help answers, family status, or outcomes in this interface.
    ceiling=np.array([8*K,11.5*K,p.COST*K])
    for k in range(int(K),-1,-1):
        q=query(f,w,k);h=float(w@q)/12
        if np.all(np.array([8*k+h,11.5*k,p.COST*k+p.RATE*h])<=ceiling+1e-7):
            return k,q,h
    raise AssertionError('zero target must be feasible')

def decide(f,w,k,g,q):
    a0=rank(f['score'],w,k)
    part=rank(f['block'],w,k)
    part=(part>1e-9)&(part<1-1e-9)&(w>0)
    answer=p.reveal(g,q,f['need'])
    known=part&np.isfinite(answer)
    result={'S0-R':a0}
    quota=float(w[known]@a0[known])
    for rule,eta in [('S1-R',16)]:
        a=a0.copy()
        if known.any():
            I=f['I'][known];gap=answer[known].astype(int)
            score=16*gap+I if rule=='S1-R' else 16*(I+eta*gap)+I
            a[known]=rank(score,w[known],quota)
        assert abs(w@a-k)<1e-6
        result[rule]=a
    return result

class Domain:
    def __init__(self,d):
        self.d=d.reset_index(drop=True);self.f=p.features(self.d);self.g=p.gap_answers(self.d)
        self.w0=self.d.weight.to_numpy(float)
        self.gap=self.d.gap_known.to_numpy(float)
        self.family=self.d.family_confirmed.to_numpy(float)
        self.rural=self.d.rural.eq(1).to_numpy(float)
        self.old=self.d.age.ge(60).to_numpy(float)
        care=self.d.family_recorded_month_hours.to_numpy(float)
        self.care_known=np.isfinite(care).astype(float)
        self.care=np.nan_to_num(care)
        self.matrix=np.column_stack([self.gap,self.f['B'],self.f['I'],self.family,self.rural,
            self.old,self.old*self.gap,self.old*self.f['B'],self.old*self.f['I'],self.care_known,self.care,
            *[(self.f['tier']==i).astype(float) for i in range(4)],*[(self.f['x'][:,i]-1) for i in range(5,10)]])

    def metrics(self,w,a,ref,h):
        z=w*a;z0=w*ref
        y=z@self.matrix;b=z0@self.matrix
        n=z.sum();gpop=w@self.gap
        baseN=b[1]+b[2]
        return np.array([n,gpop,y[0],y[0]-b[0],100*y[0]/gpop if gpop else np.nan,gpop-y[0],w.sum()-n,
            y[1],y[2],(y[1]+y[2])/baseN if baseN else np.nan,y[1]-b[1],y[2]-b[2],
            w@np.maximum(a-ref,0),w@np.maximum(ref-a,0),y[3],y[3]-b[3],y[4],y[4]-b[4],
            h,8*n+h,11.5*n,p.COST*n+p.RATE*h,10*n,10*n+h,0,5*n,10*n,*y[5:]],float)

    def evaluate(self,w,K):
        q=query(self.f,w,K);aa=decide(self.f,w,K,self.g,q);ref=aa['S0-R']
        k,qf,hf=plan(self.f,w,K);af=decide(self.f,w,k,self.g,qf)
        rows=[];arrays=[]
        for mode in ['known_equal','paid_equal','fixed_resource']:
            for rule in RULES:
                if rule=='S0-R':a=ref;hh=0.;qq=np.zeros(len(w),bool)
                elif mode=='fixed_resource':a=af[rule];hh=hf;qq=qf
                else:a=aa[rule];hh=0. if mode=='known_equal' else float(w@q)/12;qq=q
                rows.append(self.metrics(w,a,ref,hh));arrays.append((mode,rule,a,ref,qq))
        return np.asarray(rows),arrays

def safe_point(domain,w,a,ref,values,metadata):
    """Inherit exchanged-group and complementary disclosure thresholds."""
    en=w*np.maximum(a-ref,0)>1e-8;lost=w*np.maximum(ref-a,0)>1e-8
    hidden=set()
    if any(0<int(m.sum())<10 for m in [en,lost]):
        resources={'packages','all_unserved','inquiry_h','RN_h','OT_h','provider_USD','patient_contact_h','patient_total_h',
                   'family_participation_0_h','family_participation_5_h','family_participation_10_h'}
        hidden.update(set(METRICS)-resources)
    for pref,cat in [('family',domain.family.astype(bool)),('rural',domain.rural.astype(bool)),
                     ('old60',domain.old.astype(bool))]:
        if any(0<int((m&c).sum())<10 for m in [en,lost] for c in [cat,~cat]):
            hidden.update(k for k in METRICS if k.startswith(pref) and not k.startswith('family_participation'))
    care=domain.care_known.astype(bool)
    if any(0<int((m&care).sum())<10 for m in [en,lost]):
        hidden.update(['known_family_hours_recipient_mass','recorded_family_month_hours'])
    for t in range(4):
        cat=domain.f['tier']==t
        if any(0<int((m&cat).sum())<10 for m in [en,lost]):hidden.add(f'tier{t}_packages')
    for j in range(5):
        cat=domain.f['x'][:,5+j]>=2
        if any(0<int((m&cat).sum())<10 for m in [en,lost]):hidden.add(METRICS[-5+j])
    out=dict(metadata)
    out.update({k:(np.nan if k in hidden else float(v)) for k,v in zip(METRICS,values)})
    out['suppression_applied']=bool(hidden)
    out['evidence']='ALLOCATION_MODEL; no health or family-time effect identified'
    return out,hidden

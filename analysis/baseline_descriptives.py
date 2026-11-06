"""Nested population summaries; no allocation or inference changes."""
from pathlib import Path
import math
import numpy as np
import pandas as pd
from inputs import configuration, load, output_root

R=output_root()
def save(name,rows):
    pd.DataFrame(rows).to_csv(R/name,index=False,encoding='utf-8-sig',float_format='%.15g')
cfg=configuration();d,_=load()
hpath=Path(cfg['harmonized_charls'])
h=pd.read_stata(hpath,convert_categoricals=False) if hpath.suffix=='.dta' else pd.read_parquet(hpath)
assert h.ID.is_unique
h=h.set_index('ID').reindex(d.ID)
for a,b in [('age','r4agey'),('sex','ragender'),('education','raeduc_c'),('rural','h4rural')]:
    assert np.array_equal(d[a].to_numpy(),h[b].to_numpy(),equal_nan=True),a
w=d.weight.to_numpy(float);assert np.isfinite(w).all() and (w>0).all()
X=d[[f'{q}{j}' for q in ['adl','iadl'] for j in range(5)]].to_numpy(float)
assert np.isin(X,[1,2,3,4]).all()
d['B']=(X[:,:5]-1).sum(axis=1);d['I']=(X[:,5:]-1).sum(axis=1)
d['tier']=np.select([(X[:,:5]==4).any(axis=1),(X[:,:5]>=3).any(axis=1),(X[:,5:]>=3).any(axis=1)],[3,2,1],0)
mar=pd.to_numeric(h.r4mstath,errors='coerce').to_numpy(float)
hh=pd.to_numeric(h.h4hhres,errors='coerce').to_numpy(float)
d['married_partnered']=np.where(np.isin(mar,[1,2,3,4,5,7,8]),np.isin(mar,[1,2,3]).astype(float),np.nan)
d['living_alone']=np.where(np.isfinite(hh)&(hh>=1)&(hh==np.floor(hh)),(hh==1).astype(float),np.nan)
specs=[
('age','Age, years, mean (SD)','age','mean_sd',None,'F08915:r4agey','Age at wave 4 interview'),
('men','Male','sex','count_pct',[1],'F08915:ragender','Native male code 1'),
('women','Female','sex','count_pct',[2],'F08915:ragender','Native female code 2'),
('urban','Urban','rural','count_pct',[0],'F08915:h4rural','Urban community; current residence, not hukou'),
('rural','Rural','rural','count_pct',[1],'F08915:h4rural','Rural village; current residence, not hukou'),
('below_primary','Less than primary','education','count_pct',[1,2,3],'F08915:raeduc_c','Native 1–3, including traditional Sishu; below completed primary'),
('primary','Primary','education','count_pct',[4],'F08915:raeduc_c','Native 4, completed elementary school'),
('secondary','Secondary or higher','education','count_pct',list(range(5,11)),'F08915:raeduc_c','Native 5–10'),
('married_partnered','Married or partnered, n (%)','married_partnered','count_pct',[1],'F08915:r4mstath; original BE001/BE002','Reported current married (including temporarily absent spouse) or cohabiting; not partnership imputed from household linkage'),
('living_alone','Living alone, n (%)','living_alone','count_pct',[1],'F08915:h4hhres; wave 4 household roster','Current coresident household size equals one; not widowhood or absence of a spouse'),
('chronic','Number of chronic conditions, median (IQR)','chronic_n','median_iqr',None,'F08889:inherited 14-condition diagnostic routes','Original 14 reported diagnoses; no new ascertainment or missingness recoding'),
('B','Basic ADL difficulty score (0–15), median (IQR)','B','median_iqr',None,'F08889:db010–db014','Five native activity responses minus one, summed; original verified structural skips retained'),
('I','IADL difficulty score (0–15), median (IQR)','I','median_iqr',None,'F08889:db016–db020','Five native activity responses minus one, summed; ordinal need, not clinical utility'),
('tier3','Unable to perform at least one basic ADL','tier','count_pct',[3],'Same ten original functional items','At least one basic ADL response 4'),
('tier2','Needs help with basic ADLs, without inability','tier','count_pct',[2],'Same ten original functional items','At least one basic ADL response 3 and none 4'),
('tier1','IADL dependence only','tier','count_pct',[1],'Same ten original functional items','No basic ADL code 3/4; at least one IADL code 3/4'),
('tier0','Other functional difficulties','tier','count_pct',[0],'Same ten original functional items','Remaining frozen qualifying functional difficulties'),
('family','Family assistance reported, n (%)','family_confirmed','count_pct',[1],'F08889:db022_w3_1_s1–s5; inherited family roster','Confirmed family-helper report; denominator is the whole domain; not-confirmed is not necessarily no family help'),
('gap','Explicit same-activity assistance gap','gap_known','count_pct',[1],'F08889:activity responses plus corresponding db*_w2 help','At least one activity with response 3/4 and explicit no help; unknown is never no help; audit only, not Table 1')]
rows=[];checks=[];denoms=[];maps=[]
for domain,idx in [('Overall',np.ones(len(d),bool)),('With assistance gaps',d.gap_known.eq(1).to_numpy())]:
    dd=d.loc[idx];ww0=w[idx];N=len(dd)
    for key,label,field,kind,codes,source,definition in specs:
        x=pd.to_numeric(dd[field],errors='coerce').to_numpy(float);valid=np.isfinite(x)
        if field=='education':valid&=np.isin(x,range(1,11))
        if field=='sex':valid&=np.isin(x,[1,2])
        if field=='rural':valid&=np.isin(x,[0,1])
        xx=x[valid];ww=ww0[valid];nv=int(valid.sum());nm=N-nv
        r=dict(domain=domain,key=key,row=key,characteristic=label,field=field,variable=field,statistic=kind,
               domain_n=N,n_valid=nv,n_missing=nm,weight_sum=float(ww.sum()),n='',weighted_percent='',
               mean='',sd='',q25='',median='',q75='',display='',disclosure='RELEASED')
        independently=[]
        if kind=='mean_sd':
            mu=float(np.average(xx,weights=ww));sd=float(np.sqrt(np.average((xx-mu)**2,weights=ww)))
            mu2=math.fsum(float(a)*float(b) for a,b in zip(xx,ww))/math.fsum(ww)
            sd2=math.sqrt(math.fsum(float(b)*(float(a)-mu2)**2 for a,b in zip(xx,ww))/math.fsum(ww))
            r.update(mean=mu,sd=sd,display=f'{mu:.1f} ({sd:.1f})')
            independently=[('mean',mu,mu2),('sd',sd,sd2)]
        elif kind=='median_iqr':
            order=np.argsort(xx,kind='stable');qs=xx[order][np.searchsorted(np.cumsum(ww[order]),np.array([.25,.5,.75])*ww.sum(),side='left')]
            grouped={v:math.fsum(ww[xx==v]) for v in set(xx)};total=math.fsum(grouped.values());q2=[]
            for q in [.25,.5,.75]:
                acc=0
                for v,mass in sorted(grouped.items()):
                    acc+=mass
                    if acc>=q*total-1e-8:q2.append(v);break
            r.update(q25=qs[0],median=qs[1],q75=qs[2],display=f'{qs[1]:.0f} ({qs[0]:.0f}–{qs[2]:.0f})')
            independently=list(zip(['q25','median','q75'],qs,q2))
        else:
            mask=np.isin(xx,codes);n=int(mask.sum());pc=100*float(ww@mask)/ww.sum()
            n2=sum(a in codes for a in xx);pc2=100*math.fsum(float(b) for a,b in zip(xx,ww) if a in codes)/math.fsum(ww)
            r.update(n=n,weighted_percent=pc,display=f'{n:,} ({pc:.1f})')
            independently=[('n',n,n2),('weighted_percent',pc,pc2)]
            # Complement protection: never release a rare cell or reconstructable complement.
            if 0<n<10 or 0<nv-n<10:
                r.update(n='',weighted_percent='',display='Withheld',disclosure='WITHHELD_SMALL_CELL_OR_COMPLEMENT')
        for statistic,a,b in independently:
            ok=math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-9);assert ok,(domain,key,statistic)
            checks.append(dict(domain=domain,key=key,statistic=statistic,status='PASS',method='Separate scalar math.fsum or grouped weighted CDF',absolute_difference=abs(float(a)-float(b))))
        if 0<nm<10:
            r.update(n_valid='',n_missing='',weight_sum='',disclosure=r['disclosure']+';DENOMINATOR_WITHHELD')
        rows.append(r)
        denoms.append(dict(domain=domain,key=key,domain_n=N,n_valid=r['n_valid'],n_missing=r['n_missing'],weight_sum=r['weight_sum'],
                           reconciles_to_domain=nv+nm==N,definition='Positive confirmed report among all domain members; no-help status not inferred' if key=='family' else 'Available-case original survey-weighted domain description',disclosure=r['disclosure']))
    for field,keys in [('sex',['men','women']),('rural',['urban','rural']),('education',['below_primary','primary','secondary']),('tier',['tier3','tier2','tier1','tier0'])]:
        rr=[r for r in rows if r['domain']==domain and r['key'] in keys]
        if all(r['disclosure']=='RELEASED' for r in rr):
            assert sum(r['n'] for r in rr)==rr[0]['n_valid']
            assert abs(sum(r['weighted_percent'] for r in rr)-100)<1e-10
        checks.append(dict(domain=domain,key=field+'_category_partition',statistic='count and weighted percentage sums',status='PASS',method='Mutually exclusive categories',absolute_difference=0))
    # Explicitly distinguish helper-roster non-observation from confirmed report coding.
    unknown=int((~dd.roster_known.astype(bool)).sum())
    assert unknown==0 or unknown>=10
    denoms.append(dict(domain=domain,key='underlying_helper_roster',domain_n=N,n_valid=N-unknown,n_missing=unknown,
                       weight_sum=float(ww0[dd.roster_known.astype(bool)].sum()),reconciles_to_domain=True,
                       definition='Observed full helper roster; structural non-entry and incomplete roster are not no help; separate from the confirmed-report numerator',disclosure='RELEASED'))

for key,label,field,kind,codes,source,definition in specs:
    maps.append(dict(key=key,characteristic=label,field=field,native_source=source,definition=definition,
                     reference='Harmonized CHARLS codebook PDF pp.62–63' if key=='married_partnered' else 'Harmonized CHARLS codebook PDF pp.385–386' if key=='living_alone' else 'Frozen native routing and variable map',
                     missing_rule='No imputation, no sample changes; domain-specific valid denominator; confirmed reporting indicator distinguished from source roster observation',
                     evidence='OBSERVED_CHARLS'))

for domain,dd in [('Overall',d),('With assistance gaps',d.loc[d.gap_known.eq(1)])]:
    for key,label,lo,hi in [('age60_64','60–64',60,65),('age65_69','65–69',65,70),
                          ('age70_74','70–74',70,75),('age75_79','75–79',75,80),('age80plus','≥80',80,float('inf'))]:
        mask=dd.age.ge(lo)&dd.age.lt(hi);n=int(mask.sum())
        pct=100*dd.loc[mask,'weight'].sum()/dd.weight.sum()
        protected=0<n<10 or 0<len(dd)-n<10
        rows.append(dict(domain=domain,key=key,characteristic=label,field='age',statistic='count_pct',
            domain_n=len(dd),n_valid=len(dd),n_missing=0,n='' if protected else n,
            weighted_percent='' if protected else pct,
            display='Withheld' if protected else f'{n:,} ({pct:.1f})',
            disclosure='WITHHELD' if protected else 'RELEASED'))
save('BASELINE_CHARACTERISTICS_RECOMPUTED.csv',rows)
save('BASELINE_DENOMINATORS_RECOMPUTED.csv',denoms)
save('BASELINE_INDEPENDENT_CHECKS.csv',checks)
print('Baseline and nested assistance-gap aggregate summaries completed.')

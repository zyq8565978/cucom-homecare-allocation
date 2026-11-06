"""Select frozen public estimates and format the authorised baseline summary."""
from pathlib import Path
import csv,json,math
R=Path(__file__).resolve().parents[1];SRC=R/'data/aggregates';OUT=R/'results/display'
OUT.mkdir(parents=True,exist_ok=True)
cache={};ledger=[];identities=[];T={};F={}
P=json.loads((R/'metadata/model_parameters.json').read_text(encoding='utf-8-sig'))
L=json.loads((R/'metadata/cost_tables.json').read_text(encoding='utf8'))
def data(name):
    if name not in cache:
        path=SRC/name if name.endswith('.csv') else SRC/(name+'.csv')
        cache[name]=list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
    return cache[name]
def eq(a,b):
    if isinstance(b,(int,float)):
        try:return float(a)==b
        except ValueError:return False
    return a==str(b)
def row(name,sel):
    rr=[r for r in data(name) if all(eq(r[k],v) for k,v in sel.items())];assert len(rr)==1,(name,sel,len(rr));return rr[0]
def cell(tag,name,sel,col='estimate',mult=1):
    r=row(name,sel)
    protected=r.get('suppressed','').lower()=='true' or col in r.get('suppressed_fields','').split(';') or 'SUPPRESS' in r.get('status','')
    raw='' if protected else r.get(col,'')
    val=None if raw=='' else float(raw)*mult
    status='Withheld' if protected else ('Available' if val is not None else 'Unavailable')
    # Row-wide suppression_applied is not used: released S0 cells remain valid.
    if val is None and r.get('suppression_applied','').lower()=='true':status='Withheld'
    ledger.append(dict(display_id=tag,source_file=name if name.endswith('.csv') else name+'.csv',selector=json.dumps(sel,sort_keys=True),column=col,multiplier=mult,raw_value=raw,value=val,status=status))
    return val,status
def point(tag,name,sel,col='estimate',lo='lower',hi='upper'):
    v,s=cell(tag,name,sel,col);p=dict(value=v,status=s)
    if lo:p.update(lower=cell(tag+'.lower',name,sel,lo)[0],upper=cell(tag+'.upper',name,sel,hi)[0])
    return p
def fmt(v,d=2):
    if v is None:return 'Withheld'
    if abs(v)<.5*10**-d:v=0
    return f'{v:,.{d}f}'.replace('-','−')
def text(p,d=2,ci=True):
    if p['status']=='Withheld':return 'Withheld'
    if p['value'] is None:return '—'
    if abs(p['value'])<1e-8 and (not ci or (abs(p.get('lower',0))<1e-8 and abs(p.get('upper',0))<1e-8)):return '0'
    s=fmt(p['value'],d)
    if ci and p.get('lower') is not None:s+=f" ({fmt(p['lower'],d)} to {fmt(p['upper'],d)})"
    return s
def pair(tag,cap,mode,metric,design='community_WR'):
    return point(tag,'PAIRED_NINE_CAPACITY_RESULTS',dict(capacity=cap,mode=mode,metric=metric,design=design))
def aggregate(tag,scenario,policy,metric,source='ALL_PAIRED_UNCERTAINTY'):
    return point(tag,source,dict(scenario=scenario,policy=policy,metric=metric,design='community_WR'))
def tab(key,title,headers,rows,note,widths):T[key]=dict(title=title,headers=headers,rows=rows,note=note,widths=widths)
def translated(tag,p,offset):
    q=p.copy()
    for k in ['value','lower','upper']:
        if q.get(k) is not None:
            identities.append(dict(display_id=tag+'.'+k,component=p[k],offset=offset,total=p[k]+offset))
            q[k]+=offset
    return q

baseline=data('BASELINE_CHARACTERISTICS_BY_GROUP.csv')
order=['age','@Age group, years, n (%)','age60_64','age65_69','age70_74','age75_79','age80plus','@Sex, n (%)','men','women','@Residence, n (%)','urban','rural',
       '@Educational attainment, n (%)','below_primary','primary','secondary','married_partnered','living_alone',
       'chronic','B','I','@Functional dependency tier, n (%)','tier3','tier2','tier1','tier0','family']
baseline_rows=[];row_keys=[];headings=[];indented=[]
for key in order:
    row_keys.append(key)
    if key.startswith('@'):
        headings.append(len(baseline_rows));baseline_rows.append([key[1:],'','']);continue
    rr=[next(r for r in baseline if r['domain']==domain and r['key']==key)
        for domain in ['Overall','With assistance gaps']]
    baseline_rows.append([rr[0]['characteristic'],rr[0]['display'],rr[1]['display']])
    if key.startswith('age') or key in ['men','women','urban','rural','below_primary','primary','secondary','tier3','tier2','tier1','tier0']:
        if key=='age':continue
        indented.append(len(baseline_rows)-1)
tab('Table1','Baseline characteristics of the study population and participants with assistance gaps',
    ['Characteristic','Overall (N = 2,433)','With assistance gaps\n(n = 564)'],baseline_rows,
    'Counts are unweighted; percentages are survey weighted within each column and may not total 100 because of rounding. Continuous summaries are survey weighted. The 564 participants with gaps are a subset of the overall population; no between-column tests were performed. A gap requires an activity reported as needing help or impossible to perform and explicit non-receipt of help for that activity. Family assistance denotes a confirmed helper report and may coexist with a gap; other records do not establish absence of family help. ADL, activities of daily living; IADL, instrumental ADL; IQR, interquartile range; SD, standard deviation. Measurement and source-availability details are in Table S1.',[9.9,3.6,4.5])
T['Table1'].update(row_keys=row_keys,heading_rows=headings,indented_rows=indented)
labels=[('packages','Complete programmes'),('gap_reached','Allocations to people with assistance gaps'),('B_total','Basic ADL need covered (index units)'),('I_total','IADL need covered (index units)'),('family_reached','Allocations to people reporting family assistance'),('RN_h','Total nursing time (h)'),('OT_h','Occupational therapy time (h)'),('patient_total_h','Patient participation time (h)'),('provider_USD','Provider cost (2024 US$)')]
rows=[]
for metric,label in labels:
    ss=[]
    for pol in ['S0-R','S1-R']:
        ss.append(text(aggregate('T2.'+metric+'.'+pol,'2018_paid500',pol,metric),d=0 if metric=='packages' else 2,ci=False))
    ss.append(text(aggregate('T2.'+metric+'.difference','2018_paid500','paired_difference',metric)))
    rows.append([label]+ss)
tab('Table2','Allocation and resource consequences at 500 complete programmes per 1,000 candidates',
    ['Outcome','S0','S1','Difference (95% CI)'],rows,
    'S0, function-first; S1, gap-first. Both allocate 500 complete programmes per 1,000 original, survey-weighted candidates; S1 additionally pays for targeted enquiry. Differences are S1 minus S0, with paired percentile 95% CIs from community resampling; structural equalities are shown as 0. Nursing and patient time include enquiry. Time and 2024 US$ costs are planning estimates. Family assistance means confirmed reports (Table S1). Allocations are modelled opportunities, not observed counts; covered need is not functional improvement.',[6.4,2.8,2.8,6.0])

F['Figure1']=[];F['Figure2']=[]
for cap in range(100,901,100):
    rr={'capacity':cap}
    for pol in ['S0-R','S1-R']:
        rr[pol]=point(f'F1A.{cap}.{pol}','CAPACITY_100_900_RESULTS',dict(capacity=cap,mode='known_equal',policy=pol),'gap_coverage_percent',lo=None)
    rr['difference']=pair(f'F1B.{cap}',cap,'known_equal','gap_reached');F['Figure1'].append(rr)
    for mode in ['known_equal','fixed_resource']:
        x=pair(f'F2.{cap}.{mode}.x',cap,mode,'gap_reached');y=pair(f'F2.{cap}.{mode}.I',cap,mode,'I_total')
        F['Figure2'].append(dict(capacity=cap,mode=mode,x=x,I_difference=y,
            y_loss=None if y['value'] is None else -y['value']))
F['Figure3A']=[]
for how in ['universal','target']:
    F['Figure3A'].append(dict(process=how,point=aggregate('F3A.'+how,'query_'+how+'_5_paid','S1-R','inquiry_h','QUERY_IMPLEMENTATION_500')))
F['Figure3B']=[]
for scenario,pol,label in [('query_target_5_fixed','S0-R','Function-first, no extra travel'),('query_target_5_fixed','S1-R','Gap-first, targeted enquiry'),('query_universal_5_fixed','S1-R','Gap-first, universal enquiry'),('2018_rural_fixed500','S0-R','Function-first, extra rural travel'),('2018_rural_fixed500','S1-R','Gap-first, extra rural travel')]:
    p=aggregate('F3B.'+scenario+'.'+pol,scenario,pol,'packages')
    F['Figure3B'].append(dict(scenario=scenario,policy=pol,label=label,packages=p,reduction=500-p['value'],
                            reduction_lower=500-p['upper'],reduction_upper=500-p['lower']))
F['FigureS1']={
    'baseline':[dict(stage=r['stage'],n=int(float(r['n']))) for r in data('SOURCE_FLOW_FINAL')],
    'followup':[dict(category=r['category'],n=int(float(r['n'])),mass=float(r['weighted_per_original1000'])) for r in data('FOLLOWUP2020_FLOW_AND_ELIGIBILITY') if r['section']=='current_eligibility_partition']}
F['FigureS2']=[r for r in data('CONDITIONAL_ACCEPTABILITY_GRID') if eq(r['capacity'],500) and r['mode'] in ['known_equal','fixed_resource']]

measurement=[
['Population','2018 interview; age ≥60; community dwelling; at least two reported chronic conditions; qualifying functional difficulty.','Exact frozen 2,433 members; no selection using follow-up.'],
['Functional entry','At least one basic ADL difficulty or at least two IADL difficulties.','Ten activity responses resolved in the original cohort.'],
['Age and recorded sex','Harmonized CHARLS r4agey and ragender; native codes 1 man, 2 woman. Age groups: 60–64, 65–69, 70–74, 75–79 and ≥80.','Matched to the same frozen records. Age groups are exhaustive and nonoverlapping; counts and weighted percentages use each column’s full denominator (2,433 or 564). No missing values.'],
['Education','raeduc_c: 1–3 below completed primary (including traditional Sishu), 4 primary, 5–10 secondary or higher.','No missing values in this cohort; schooling group is descriptive.'],
['Residence','h4rural: urban community or rural village at the current interview.','Current residence, not household registration (hukou); no missing values in either column.'],
['Marital status','r4mstath codes 1, 2 or 3: reported married or cohabiting; original BE001/BE002.','Includes temporarily absent spouses; no implied partnership recoding. No missing values in either column.'],
['Living alone','h4hhres = 1; documented current coresident household roster.','Not inferred from widowhood or absence of a spouse. No missing values in either column.'],
['Chronic conditions','Original count of 14 reported conditions, retaining verified diagnostic routes.','No new case definitions, imputation or selection.'],
['Basic ADL','Dressing, bathing, eating, bed transfer and toileting; db010–db014.','Native 1 no difficulty; 2 difficulty but independent; 3 needs help; 4 unable.'],
['Instrumental ADL','Housework, meal preparation, shopping, finances and medication; db016–db020.','Same four native categories; inability remains distinct.'],
['Need indices','B and I each sum response minus 1 across five activities, range 0–15.','Ordinal need indices, not utility or formal disability grades.'],
['Structural skip','Verified negative basic-ADL screening may establish no difficulty.','Ordinary missing responses are not assigned zero difficulty.'],
['Explicit assistance gap','Code 3 or 4 plus explicit no help for that same activity.','A confirmed gap remains confirmed despite another unknown item.'],
['Unknown help','Needed-help answers incomplete without any confirmed gap.','Unknown is not no help; original function-first probability retained.'],
['Family assistance','Confirmed family-helper report from the functional-module roster; denominator is all members of the column.','May coexist with a gap; non-confirmation is not absence of help. Full roster unobserved/incomplete in 728 overall and 186 gap-subgroup records, including structural non-entry.'],
['Nested subgroup and summaries','gap_known = 1 identifies exactly 564 of the original 2,433 participants. Original INDV_weight_ad2; descriptive SD and inverse weighted empirical quartiles.','Each column uses its own weighted denominator. No p values, SMDs, complete-case selection or imputation. All displayed indicators have defined values; roster availability is distinguished above.'],
['Follow-up','Same-person 2018–2020 link and current activity/help measurements.','Death, unresolved qualification and measured non-entry remain separate.']]
tab('TableS1','Measurements, eligibility and missing-data rules',['Construct','Definition and source','Routing or interpretation'],measurement,
    'Baseline values are in Table 1. Exact sources and derivations are in BASELINE_VARIABLE_MAP_UPDATED.csv; valid and missing denominators, including source roster availability, are in UPDATED_BASELINE_DENOMINATORS.csv. Functional tiers are mutually exclusive model priorities, not validated disability grades. Brief ranking enquiry is not a formal clinical or statutory disability assessment.',[3.2,7.5,7.3])
for key in ['TableS2','TableS3']:T[key]=L[key]
# Retain the previous audited cell provenance for unchanged supplementary tables.
oldledger=R/'metadata/cost_source_ledger.csv'
for r in csv.DictReader(oldledger.open(encoding='utf-8-sig')):
    if r['display_id'].startswith('S3.'):
        r['multiplier']=1/float(r.pop('divisor'));r['source_file']=r['source_file'].replace('../INNER/','')
        ledger.append(r)

inputs=[
('Programme duration','programme_months','months','CAPABLE 2014 protocol; 2019 RCT [1,2].'),
('Nursing visits','RN_visits','up to visits','CAPABLE protocol [1]; complete programme retained.'),
('Occupational therapy visits','OT_visits','up to visits','CAPABLE protocol [1]; complete programme retained.'),
('Nursing time per programme','RN_h_per_package','h','Planning: 4 contact hours plus travel and coordination.'),
('OT time per programme','OT_h_per_package','h','Planning: 6 contact hours plus travel and coordination.'),
('Patient contact per programme','patient_contact_h_per_package','h','Protocol contact schedule, 4 nursing + 6 OT hours; enquiry additional.'),
('Targeted support enquiry','question_minutes','min/person','Planning assumption for ranking information, not a formal disability assessment.'),
('Extra rural travel','rural_extra_h_per_visit','h/visit','Planning scenario, separately applied to four nursing and six OT visits.'),
('Annual industry wage reference','industry_wage_reference_CNY','CNY/year','NBS wage table: 2024 health and social work value [4]; not occupation-specific wages.'),
('Employer cost factor','employer_planning_factor','multiplier','Planning assumption; not an official conversion rule.'),
('Productive work time','productive_hours_planning','h/year','Planning assumption.'),
('Home adaptation and implementation','implementation_home_adaptation_bundle_CNY','CNY/programme','CNY5,000 policy-anchored adaptation ceiling [5] + CNY500 implementation planning allowance; not a Chinese CAPABLE quotation.'),
('2024 average exchange rate','fx_CNY_per_USD','CNY/US$','NBS 2024 statistical communiqué [6]; converted once.'),
('Professional hourly reference','reference_hourly_USD','2024 US$/h','143,173 × 1.25 ÷ 1,600 ÷ 7.1217; common planning proxy, not interchangeable staff.'),
('Complete programme cost','complete_package_USD','2024 US$','19.5 professional hours × hourly reference + 5,500 ÷ 7.1217.'),
('Reference nursing ceiling','resource_ceiling_RN_h','h/1,000','500 complete programmes × 8 h; planning resource ceiling.'),
('Reference OT ceiling','resource_ceiling_OT_h','h/1,000','500 complete programmes × 11.5 h; planning resource ceiling.'),
('Reference budget ceiling','resource_ceiling_USD','2024 US$/1,000','500 × unrounded complete-programme cost.')]
rows=[]
for label,key,unit,source in inputs:
    value=P[key]
    ledger.append(dict(display_id='S2.'+key,source_file='MODEL_PARAMETERS_FINAL.json',selector=json.dumps({'key':key}),column=key,multiplier=1,raw_value=value,value=value,status='Available'))
    decimals=4 if key=='fx_CNY_per_USD' else 5 if key=='reference_hourly_USD' else 2 if key in ['complete_package_USD','resource_ceiling_USD'] else 0 if float(value).is_integer() else 2
    shown=('Up to '+fmt(value,0)+' visits') if key in ['RN_visits','OT_visits'] else fmt(value,decimals)+' '+unit
    rows.append([label,shown,source])
tab('TableS2','Complete service and resource inputs',['Input','Frozen value','Source or planning basis'],rows,
    'All monetary outcomes are 2024 US$. Full-precision parameters and inherited sources accompany the electronic tables. The CNY5,500 bundle combines adaptation and implementation, not adaptation alone. Enquiry is added separately. No new prices, clinical effects, inflation adjustments or currency conversions were introduced. References [1,2,4–6] appear at the start of this appendix.',[5.0,4.1,8.9])
oldS3=T['TableS3']
oldS3['headers']=['Characteristic','Gaining allocation','Losing allocation']
oldS3['rows']=[[r[0],r[1],r[3]] for r in oldS3['rows']]
oldS3['widths']=[8,5,5]
oldS3['note']='The 53 gaining and 49 losing source records contribute changes in allocation probability, not simple participant averages. Each side represents 17.40 weighted opportunities per 1,000 original candidates. Profiles and CIs are weighted by allocation-probability changes. All released intervals use 5,000 valid paired community draws except recorded family-help hours for gaining records (4,974). Withheld cells and protected valid-draw counts remain undisclosed. Family-help hours are recorded assistance, not estimated time savings.'

rows=[]
for mode,label in [('known_equal','Equal places'),('fixed_resource','Fixed resources')]:
    for cap in range(100,901,100):
        rows.append([label,str(cap)]+[text(pair(f'S4.{mode}.{cap}.{m}',cap,mode,m)) for m in ['packages','gap_reached','I_total','family_reached']])
tab('TableS4','Paired allocation differences across nine capacity scenarios',
    ['Comparison','Capacity','Δ Programmes\n(95% CI)','Δ Gap allocations\n(95% CI)','Δ Covered IADL\n(95% CI)','Δ Family-help allocations\n(95% CI)'],rows,
    'S1-R minus S0-R, per 1,000 original candidates; 5,000 paired community draws. Equal places assumes information already known; fixed resources charges targeted enquiry to the corresponding capacity ceilings. Structural zeros are shown as 0. Protected cells are withheld, not zero. The IADL difference is an index total, not patient deterioration. Figure 2 reverses its sign to show the need-coverage loss.',[2.4,1.7,3.0,3.6,3.7,3.6])

rows=[]
for mode,metric,label in [('paid','inquiry_h','Nursing enquiry (h)'),('paid','provider_USD','Provider cost (US$)'),('paid','patient_total_h','Patient participation (h)'),('fixed','packages','Complete programmes'),('fixed','inquiry_h','Nursing enquiry (h)'),('fixed','OT_h','Occupational therapy (h)'),('fixed','patient_total_h','Patient participation (h)'),('fixed','provider_USD','Provider cost (US$)')]:
    aa=[aggregate('S5.query.'+mode+'.'+metric+'.'+x,'query_'+x+'_5_'+mode,'S1-R',metric,'QUERY_IMPLEMENTATION_500') for x in ['universal','target']]
    dd=point('S5.query.'+mode+'.'+metric+'.delta','QUERY_IMPLEMENTATION_PAIRED_CONTRASTS',dict(mode=mode,metric=metric,contrast='target_minus_universal',design='community_WR'))
    rows.append([('Equal 500' if mode=='paid' else 'Fixed resources')+'; targeted vs universal',label]+[text(x,ci=False) for x in aa]+[text(dd)])
for metric,label in [('packages','Complete programmes (n)'),('gap_reached','Gap allocations (n)'),('I_total','Covered IADL (index units)'),('family_reached','Family-help allocations (n)'),('rural_reached','Rural allocations (n)')]:
    vals=[aggregate('S5.rural.'+metric+'.'+p,'2018_rural_fixed500',p,metric) for p in ['S0-R','S1-R','paired_difference']]
    rows.append(['Extra rural travel; S1-R vs S0-R',label,text(vals[0],ci=False),text(vals[1],ci=False),text(vals[2])])
for metric,label,base in [('total_packages','Complete programmes',500),('extra_RN_h','Nursing time (h)',P['resource_ceiling_RN_h']),('extra_OT_h','Occupational therapy (h)',P['resource_ceiling_OT_h']),('extra_provider_USD','Provider cost (US$)',P['resource_ceiling_USD'])]:
    pp=point('S5.no_replace.'+metric,'NO_DISPLACEMENT_EXPANSION',dict(capacity=500,starting_S1='known_equal',metric=metric))
    delta=translated('S5.no_replace.delta.'+metric,pp,-base) if metric=='total_packages' else pp
    total=pp if metric=='total_packages' else translated('S5.no_replace.total.'+metric,pp,base)
    rows.append(['No displacement; original S0-R reference',label,fmt(base),text(total,ci=False),text(delta)])
for metric,label,base in [('additional_RN_h','Nursing time (h)',P['resource_ceiling_RN_h']),('additional_OT_h','Occupational therapy (h)',P['resource_ceiling_OT_h']),('additional_USD','Provider cost (US$)',P['resource_ceiling_USD'])]:
    pp=point('S5.restore.'+metric,'RURAL500_EQUITY_AND_PROTECTION',dict(scenario='rural_S1_full500_paid',metric=metric,design='community_WR'))
    total=translated('S5.restore.total.'+metric,pp,base)
    rows.append(['Restore rural S1-R 500; original ceilings',label,fmt(base),text(total,ci=False),text(pp)])
tab('TableS5','Information acquisition, rural constraints and expansion requirements',
    ['Scenario/comparison','Outcome (unit)','Reference total','Alternative total','Difference (95% CI)'],rows,
    'Per 1,000 original candidates; costs are 2024 US$. Enquiry rows compare S1 targeted (alternative) with universal (reference) enquiry; rural fixed-resource rows compare S1 with S0. No-displacement expansion retains original S0 opportunities and adds complete programmes. Rural restoration compares S1 resources for 500 programmes with the original ceilings, NOT rural S1 with S0. Totals add stored increments to unrounded constants; intervals are the original paired increments (or the stored package-total interval translated by 500). Rural travel adds 0.5 h to each of four nursing and six OT visits. OT binds the next-programme step in all 5,000 community and county draws; RN also binds in two county draws for S1. Money alone cannot replace staff time.',[4.1,3.6,2.6,2.9,4.8])

rows=[]
for scenario,context in [('2020_equal500','500 programmes'),('2020_fixed500','Original 500-resource ceilings'),('2020_eligible50','Half current eligibility (278.58)'),('2020_update_500','Updated vs frozen function; 500')]:
    policies=['frozen2018_function','updated2020_function','paired_difference'] if scenario=='2020_update_500' else ['S0-R','S1-R','paired_difference']
    for metric,label in [('gap_reached','Gap allocations (n)'),('I_total','Covered IADL (index units)')]:
        vals=[aggregate('S6.'+scenario+'.'+metric+'.'+p,scenario,p,metric) for p in policies]
        rows.append([context,label,text(vals[0],ci=False),text(vals[1],ci=False),text(vals[2])])
tab('TableS6','Reallocation after reassessment of needs in 2020',
    ['Capacity or comparison','Outcome','Reference','Alternative','Paired difference\n(95% CI)'],rows,
    'Per 1,000 original 2018 candidates. The same 1,386 observable eligible participants represent 557.16 original opportunities; half is 278.58, not 500. Reference and alternative are S0-R and S1-R except the explicitly labelled updating rows, which compare frozen 2018 with updated 2020 functional priority. No failures or capacity shortfalls occurred in the original 5,000 community or county resamples of these contrasts. Unknown qualification is not absence of need. Current-eligibility compatibility bounds are 557.16–632.45; they are not CIs. This is natural reassessment, not a programme treatment effect.',[4.5,4.0,2.5,2.5,4.5])

rows=[]
for sc,label in [('age65_equal500','Age ≥65; 500 original-scale places'),('age65_eligible50','Age ≥65; 50% of subgroup'),('query_target_3_fixed','Three-minute targeted enquiry'),('query_target_10_fixed','Ten-minute targeted enquiry')]:
    for metric,lbl in [('packages','Complete programmes (n)'),('gap_reached','Gap allocations (n)'),('I_total','Covered IADL (index units)')]:
        policies=['S0-R','S1-R','paired_difference']
        vals=[aggregate('S7.'+sc+'.'+metric+'.'+p,sc,p,metric) for p in policies]
        rows.append([label,lbl,text(vals[0],ci=False),text(vals[1],ci=False),text(vals[2])])
for metric,label in [('gap_reached','Gap allocations (n)'),('I_total','Covered IADL (index units)'),('family_reached','Family-help allocations (n)')]:
    v=pair('S7.county.'+metric,500,'known_equal',metric,'county_WR')
    vv=[text(point('S7.county.point.'+metric+'.'+pol,'CAPACITY_100_900_RESULTS',dict(capacity=500,mode='known_equal',policy=pol),metric,lo=None),ci=False) for pol in ['S0-R','S1-R']]
    rows.append(['County resampling; equal 500',label]+vv+[text(v)])
for hours in [0,5,10]:
    vals=[]
    for pol in ['S0-R','S1-R','paired_difference']:
        v=point(f'S7.family.{hours}.{pol}','FAMILY_PARTICIPATION_CURRENT',dict(scenario='2018_fixed500',policy=pol,design='community_WR',programme_family_h_per_package=hours,inquiry_family_fraction=.5),'total_family_participation_h')
        vals.append(text(v,ci=pol=='paired_difference'))
    rows.append([f'Family {hours} h/programme; 50% enquiry accompaniment','Family participation (h)']+vals)
tab('TableS7','Age, enquiry duration and clustering sensitivities',
    ['Sensitivity','Outcome','S0-R','S1-R','S1-R − S0-R\n(95% CI)'],rows,
    'Per 1,000 original candidates. The ≥65 subgroup has 1,935 participants and weighted mass 819.12; its own 50% capacity is 409.56. It is not renormalised to 1,000. Enquiry-duration rows retain original resource ceilings and S1-R ordering. County intervals use the same point estimates and separate 5,000 paired county draws. Family participation scenarios of 0, 5 and 10 hours per programme and 0%, 50% and 100% enquiry accompaniment are supplied in FAMILY_PARTICIPATION_CURRENT.csv; none are caregiver-time savings.',[4.5,4.0,2.5,2.5,4.5])

def reader_names(obj):
    if isinstance(obj,str):return obj.replace('S0-R','S0').replace('S1-R','S1')
    if isinstance(obj,list):return [reader_names(x) for x in obj]
    if isinstance(obj,dict):return {reader_names(k):reader_names(v) for k,v in obj.items()}
    return obj
T=reader_names(T);F=reader_names(F)
for t in T.values():
    t['headers']=[s.replace(' (n)','') for s in t['headers']]
    t['rows']=[[s.replace('allocations (n)','allocations').replace('programmes (n)','programmes') for s in rr] for rr in t['rows']]
for name,obj in [('tables',T),('figures',F)]:
    (OUT/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
for key,t in T.items():
    with (OUT/(key+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        ww=csv.writer(f);ww.writerow(t['headers']);ww.writerows(t['rows'])
with (OUT/'SOURCE_VALUE_LEDGER.csv').open('w',encoding='utf-8-sig',newline='') as f:
    ww=csv.DictWriter(f,fieldnames=ledger[0].keys());ww.writeheader();ww.writerows(ledger)
with (OUT/'DERIVED_DISPLAY_IDENTITIES.csv').open('w',encoding='utf-8-sig',newline='') as f:
    ww=csv.DictWriter(f,fieldnames=identities[0].keys());ww.writeheader();ww.writerows(identities)
print('Prepared 2 main tables, 3 main figures, 7 supplementary tables and 2 supplementary figures.')
print('Frozen source cells:',len(ledger))

"""File integrity, public provenance and disclosure tests; standard library only."""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
checks=0
def check(ok):
    global checks
    assert ok
    checks+=1
def near(a,b):return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8)
def matches(row,sel):
    for k,v in sel.items():
        if isinstance(v,(int,float)):
            try:
                if float(row[k])!=v:return False
            except (ValueError,KeyError):return False
        elif str(row.get(k))!=str(v):return False
    return True

cache={}
for r in read(ROOT/'metadata/SOURCE_VALUE_LEDGER.csv'):
    name=r['source_file'];sel=json.loads(r['selector'])
    if name.endswith('.json'):
        source=json.loads((ROOT/'metadata/model_parameters.json').read_text())
        raw=source[sel['key']];protected=False
    else:
        if name not in cache:cache[name]=read(ROOT/'data/aggregates'/name)
        found=[x for x in cache[name] if matches(x,sel)]
        check(len(found)==1);x=found[0]
        protected=x.get('suppressed','').lower()=='true' or r['column'] in x.get('suppressed_fields','').split(';') or 'SUPPRESS' in x.get('status','')
        raw='' if protected else x.get(r['column'],'')
    if r['status']=='Withheld':check(r['value']=='' and (protected or raw==''))
    elif r['value']=='':check(raw=='')
    else:check(not protected and raw!='' and near(r['value'],float(raw)*float(r['multiplier'])))

F=json.loads((ROOT/'data/display/figures.json').read_text(encoding='utf8'))
for row in F['Figure1']:
    check((row['S1']['value'] is None)==(row['capacity'] in [100,200,700]))
    check((row['difference']['value'] is None)==(row['capacity'] in [100,200,700]))
T=json.loads((ROOT/'data/display/tables.json').read_text(encoding='utf8'))
check(T['Table1']['headers']==['Characteristic','Overall (N = 2,433)','With assistance gaps\n(n = 564)'])
check(T['Table2']['rows'][0]==['Complete programmes','500','500','0'])
manifest=ROOT/'metadata/FILE_MANIFEST.csv'
if manifest.exists():
    for r in read(manifest):
        p=ROOT/r['path'];check(p.is_file())
        check(hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'])
print(json.dumps(dict(passed=True,checks=checks,scope='Aggregate provenance, suppression and file integrity'),indent=2))

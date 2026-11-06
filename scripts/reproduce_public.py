"""Rebuild public tables/figures and check aggregates without participant data."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def run(name):
    subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,check=True)

run('check_arithmetic.py')
run('prepare_displays.py')
for name in ['tables.json','figures.json']:
    original=json.loads((ROOT/'data/display'/name).read_text(encoding='utf8'))
    generated=json.loads((ROOT/'results/display'/name).read_text(encoding='utf8'))
    assert original==generated, 'Frozen display changed: '+name
tables=json.loads((ROOT/'data/display/tables.json').read_text(encoding='utf8'))
lines=[]
for key,t in tables.items():
    lines += ['## '+key+': '+t['title'],'']
    clean=lambda x:str(x).replace('\n',' ').replace('|','/')
    lines += ['| '+' | '.join(map(clean,t['headers']))+' |',
              '| '+' | '.join(['---']*len(t['headers']))+' |']
    lines += ['| '+' | '.join(map(clean,row))+' |' for row in t['rows']]
    lines += ['',t['note'],'']
(ROOT/'results/TABLES.md').write_text('\n'.join(lines),encoding='utf8')
if '--no-plots' not in sys.argv:run('plot_figures.py')
print('Frozen tables and figure data reproduced exactly. No participant-level analysis was run.')

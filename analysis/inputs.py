"""Explicit, local-only access to authorised analytical inputs."""
from pathlib import Path
import json
import os
import numpy as np
import pandas as pd

REPOSITORY = Path(__file__).resolve().parents[1]

def configuration():
    name = os.environ.get('CUCOM_CONFIG')
    if not name:
        raise RuntimeError('Set CUCOM_CONFIG to your private configuration JSON. See docs/RESTRICTED_INPUTS.md.')
    return json.loads(Path(name).read_text(encoding='utf-8-sig'))

def output_root():
    if not os.environ.get('CUCOM_CONFIG'):
        return REPOSITORY / 'results'
    path = Path(configuration()['output_directory']).resolve()
    if path == REPOSITORY or REPOSITORY in path.parents:
        raise ValueError('Restricted analysis outputs must remain outside this public repository.')
    for child in ['private', 'logs', 'supplement']:
        (path / child).mkdir(parents=True, exist_ok=True)
    return path

def load():
    cfg = configuration()
    d = pd.read_parquet(cfg['baseline_2018'])
    b = pd.read_parquet(cfg['followup_2020'])
    if not (len(d) == len(b) == 2433 and d.ID.is_unique and b.ID.is_unique and d.ID.equals(b.ID)):
        raise ValueError('The frozen 2,433-person analytical files must have identical unique local ID order.')
    assert d.age.ge(60).all() and d.weight.gt(0).all() and np.isfinite(d.weight).all()
    assert int(d.gap_known.sum()) == 564
    assert int(b.eligible_current.sum()) == 1386
    return d.reset_index(drop=True), b.reset_index(drop=True)

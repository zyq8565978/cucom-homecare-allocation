"""Frozen clinical-need priorities. No outcomes or family status enter ranking."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.dont_write_bytecode = True
COLS = [f'adl{i}' for i in range(5)] + [f'iadl{i}' for i in range(5)]
ITEMS = ['dressing','bathing','eating','transferring','toileting','housework','meals','shopping','finances','medication']
RATE = 15.706068249154
COST = 1078.5558464797732
CAPS = [100, 200, 300, 400, 500]

from inputs import load

def features(d, cumulative=False):
    x = d[COLS].to_numpy(float)
    assert np.isin(x, [1, 2, 3, 4]).all()
    B = (x[:, :5] - 1).sum(axis=1).astype(int)
    I = (x[:, 5:] - 1).sum(axis=1).astype(int)
    unable = (x[:, :5] == 4).any(axis=1)
    dependent = (x[:, :5] >= 3).any(axis=1)
    tier = np.select([unable, dependent, (x[:, 5:] >= 3).any(axis=1)], [3, 2, 1], 0)
    if cumulative:
        tier = np.where(tier == 3, 2, tier)
    return dict(x=x, B=B, I=I, N=B+I, tier=tier, block=16*tier+B,
                score=256*tier+16*B+I, need=(x >= 3).any(axis=1), unable=unable, dependent=dependent)

def rank(score, w, k):
    assert -1e-7 <= k <= w.sum()+1e-7
    levels, inverse = np.unique(score, return_inverse=True)
    mass = np.bincount(inverse, weights=w, minlength=len(levels))
    before = np.cumsum(mass[::-1])[::-1] - mass
    frac = np.divide(k-before, mass, out=np.zeros(len(mass)), where=mass > 0)
    return np.clip(frac, 0, 1)[inverse]

def query_mask(f, w, k):
    a = rank(f['block'], w, k)
    partial = (a > 1e-9) & (a < 1-1e-9) & (w > 0)
    if partial.sum() <= 1:
        return np.zeros(len(w), bool)
    return partial & f['need']

def union_query(f, w, k):
    # Functional blocks intersecting at least one integer target in [0,k].
    result = np.zeros(len(w), bool)
    before = 0.
    for block in np.unique(f['block'])[::-1]:
        ix = (f['block'] == block) & (w > 0)
        after = before + w[ix].sum()
        first = max(1, int(np.floor(before + 1e-8)) + 1)
        if first <= k and first < after-1e-8 and ix.sum() > 1:
            result |= ix & f['need']
        before = after
    return result

def gap_answers(d):
    g = d.gap_known.to_numpy(float)
    unknown = d.unknown_need_n.gt(0).to_numpy() & ~d.gap_known.to_numpy(bool)
    g[unknown] = np.nan
    return g

def reveal(g, mask, need):
    answer = np.full(len(g), np.nan)
    answer[~need] = 0.  # Screened out: no explicit help need, not an unanswered need.
    answer[mask] = g[mask]
    return answer

def decide(f, w, k, answer):
    a0 = rank(f['score'], w, k)
    a1 = a0.copy()
    block_fraction = rank(f['block'], w, k)
    part = (block_fraction > 1e-9) & (block_fraction < 1-1e-9) & (w > 0)
    if part.sum() > 1:
        known = part & np.isfinite(answer)
        # Genuinely unknown support keeps its original probability.
        quota = w[known] @ a0[known]
        if known.any():
            a1[known] = rank(16*answer[known] + f['I'][known], w[known], quota)
    assert abs(w @ a1 - k) < 1e-6
    n0, n1 = (w*a0) @ f['N'], (w*a1) @ f['N']
    policies = {'S0-R': a0, 'S1-R': a1}
    lambdas = {'S0-R': 0., 'S1-R': 1.}
    return policies, lambdas

def allocate(f, w, k, g):
    q = query_mask(f, w, k)
    policies, lambdas = decide(f, w, k, reveal(g, q, f['need']))
    return policies, lambdas, q

def resource(w, a, rural, inquiry_h=0., travel=0.):
    n = w @ a
    r = (w*a) @ rural
    return np.array([8*n+4*travel*r+inquiry_h, 11.5*n+6*travel*r,
                     COST*n+RATE*(10*travel*r+inquiry_h)])

def constrained(f, w, k, g, rural, policy, minutes=5., travel=0., universal=False):
    a0 = rank(f['score'], w, k)
    ceiling = resource(w, a0, rural, 0, travel)
    q = (f['need'] & (w > 0)) if universal else union_query(f, w, k)
    if policy == 'S0-R':
        return a0, 0., 0., k
    h = w @ q * minutes / 60
    answer = reveal(g, q, f['need'])
    for target in range(int(k), -1, -1):
        aa, _ = decide(f, w, target, answer)
        a = aa[policy]
        if np.all(resource(w, a, rural, h, travel) <= ceiling+1e-7):
            return a, h, w@q, target
    return None, h, w@q, np.nan

def quantile(x, w, q):
    ix = np.isfinite(x) & (w > 0)
    if not ix.any():
        return np.nan
    j = np.argsort(x[ix], kind='stable')
    xx, ww = x[ix][j], w[ix][j]
    return xx[min(np.searchsorted(ww.cumsum(), q*ww.sum()), len(xx)-1)]

"""Paired with-replacement cluster approximation, not official stratified PPS variance."""
import numpy as np
import pandas as pd
from inputs import configuration

def weights(d, level, replicates=5000):
    source = pd.read_parquet(configuration()['sampling_frame_2018'], columns=['weight','raw_interview','psu'])
    full = source.loc[source.weight.gt(0) & source.raw_interview.eq(True), 'psu'].astype(str)
    ids = d.psu.astype(str)
    if level == 'county_WR':
        full, ids = full.str[:6], ids.str[:6]
    elif level != 'community_WR':
        raise ValueError('Unknown clustering approximation')
    pool = np.sort(full.unique())
    assert len(pool) == (150 if level == 'county_WR' else 449)
    indices = pd.Index(pool).get_indexer(ids)
    assert (indices >= 0).all()
    rng = np.random.default_rng(20261027)
    for replicate in range(replicates):
        values, counts = np.unique(rng.choice(pool, len(pool), replace=True), return_counts=True)
        multiplicity = pd.Series(counts, index=values).reindex(pool, fill_value=0).to_numpy()
        w = d.weight.to_numpy(float) * multiplicity[indices]
        assert w.sum() > 0
        yield replicate, 1000*w/w.sum()

"""Synthetic tests only: no study participants or plausible individual records."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
import policies as p
import capacity_model as m

class PolicyTests(unittest.TestCase):
    def frame(self):
        x=np.array([[4,1,1,1,1,1,1,1,1,1],
                    [3,1,1,1,1,4,4,4,4,4],
                    [3,1,1,1,1,3,3,3,3,3],
                    [1,1,1,1,1,4,1,1,1,1]])
        return pd.DataFrame(x,columns=p.COLS)
    def test_functional_tiers(self):
        f=p.features(self.frame())
        self.assertEqual(f['tier'].tolist(),[3,2,2,1])
        self.assertTrue(np.all(np.diff(f['score'])<0))
    def test_weighted_lottery_mass(self):
        for k in [0,100,300,500,1000]:
            a=m.rank(np.array([2,2,1,0]),np.array([100,200,300,400]),k)
            self.assertAlmostEqual(np.array([100,200,300,400])@a,k)
    def test_gap_does_not_cross_basic_priority(self):
        f=p.features(self.frame());w=np.full(4,250.)
        q=m.query(f,w,500)
        a=m.decide(f,w,500,np.array([0.,0.,1.,1.]),q)['S1-R']
        self.assertEqual(a.tolist(),[1.,0.,1.,0.])
    def test_unasked_answers_cannot_change_allocation(self):
        f=p.features(self.frame());w=np.full(4,250.)
        q=m.query(f,w,500)
        g=np.array([0.,0.,1.,1.]);a=m.decide(f,w,500,g,q)['S1-R']
        g[~q]=1-g[~q]
        np.testing.assert_array_equal(a,m.decide(f,w,500,g,q)['S1-R'])
    def test_unknown_is_not_gap(self):
        f=p.features(self.frame());w=np.full(4,250.)
        q=m.query(f,w,500)
        a=m.decide(f,w,500,np.array([0.,np.nan,1.,0.]),q)['S1-R']
        ref=m.rank(f['score'],w,500)
        self.assertEqual(a[1],ref[1])
    def test_fixed_resources_paid_before_answers(self):
        f=p.features(self.frame());w=np.full(4,250.)
        k,q,h=m.plan(f,w,500)
        self.assertLessEqual(8*k+h,4000+1e-7)
        self.assertLessEqual(11.5*k,5750+1e-7)
        self.assertLessEqual(p.COST*k+p.RATE*h,p.COST*500+1e-7)

if __name__=='__main__':unittest.main()

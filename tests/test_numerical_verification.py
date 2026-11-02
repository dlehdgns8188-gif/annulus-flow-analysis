"""검증 판정과 기존 계산값 회귀. 계산 엔진의 수식을 테스트용으로 복제하지 않는다."""
import unittest
from unittest.mock import patch
import warnings
import numpy as np
from analysis import (analyze_basic_flow, numerical_verification, sweep_geometry_ratio,
                      design_inner_radius, design_with_shear_limit, verify_flow_model)
from flow import volumetric_flow_rate, velocity_profile


class NumericalVerificationTests(unittest.TestCase):
    def basic(self, k=.5, dp=100.):
        return analyze_basic_flow(1000, .1, 1., k*.01, .01, dp)

    def test_default_values_and_all_checks(self):
        b=self.basic(); r=b['verification']
        self.assertAlmostEqual(b['Q'],4.947381662033e-7,places=18)
        self.assertAlmostEqual(b['V'],.002099733991666,places=14)
        self.assertAlmostEqual(b['u_max'],.003165942182285,places=14)
        self.assertAlmostEqual(b['r_max'],.007355342550374,places=14)
        self.assertEqual(r['overall'],'PASS')
        for row in r['no_slip']+r['extremum']:
            self.assertEqual(row['status'],'PASS')
            self.assertLess(abs(row['value']),row['tolerance'])
        self.assertLess(r['relative_error']*100,.01)
        self.assertGreater(r['wall_gradients'][0],0)
        self.assertLess(r['wall_gradients'][1],0)
        self.assertTrue(np.all(r['wall_tractions']<0))

    def test_reverse_flow_wall_tractions(self):
        # 기존 UI는 양의 압력차만 지원한다. 저수준 검증의 방향 의존성 확인.
        b=self.basic(); b['Q']=volumetric_flow_rate(.005,.01,.1,1.,-100.)
        r=numerical_verification(.005,.01,.1,1.,-100.,b)
        self.assertTrue(r['sign_ok'])
        self.assertTrue(np.all(r['wall_tractions']>0))
        self.assertLess(r['wall_stresses'][0],0)
        self.assertGreater(r['wall_stresses'][1],0)

    def test_extreme_ratios_do_not_hide_loss_of_precision(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for k in [1e-8, .999, .9999, .999999]:
                r=self.basic(k)['verification']
                self.assertTrue(np.isfinite(r['Q_numerical']))
                self.assertGreater(r['Q_numerical'],0)
                if k==1e-8:self.assertEqual(r['overall'],'PASS')
                if k==.9999:self.assertEqual(r['flow_status'],'CAUTION')
                if k==.999999:self.assertEqual(r['flow_status'],'FAIL')

    def test_no_slip_strict_tolerance_and_failed_gradient(self):
        b=self.basic()
        with patch('analysis.velocity_profile', return_value=np.array([1e-9,0.])):
            r=numerical_verification(.005,.01,.1,1.,100.,b)
        self.assertEqual(r['no_slip'][0]['status'],'FAIL')
        r=dict(b);r['r_max']=.006
        checked=numerical_verification(.005,.01,.1,1.,100.,r)
        self.assertEqual(checked['extremum'][0]['status'],'FAIL')
        self.assertEqual(checked['overall'],'FAIL')

    def test_relative_flow_threshold_and_zero_not_false_pass(self):
        b=self.basic(); b['Q']*=1.001
        r=numerical_verification(.005,.01,.1,1.,100.,b)
        self.assertEqual(r['flow_status'],'FAIL')
        with patch('analysis.analytical_flow_rate',return_value=0.):
            r=numerical_verification(.005,.01,.1,1.,100.,b)
        self.assertIsNone(r['relative_error'])
        self.assertNotEqual(r['flow_status'],'PASS')

    def test_sweep_and_design_regression(self):
        table=sweep_geometry_ratio(.01,.1,1.,100.)
        self.assertEqual(table.shape,(30,6))
        self.assertTrue(np.all(np.diff(table[:,2])<0))
        q=4.947381662033e-7
        r,_=design_inner_radius(q,.01,.1,1.,100.)
        self.assertAlmostEqual(r['Ri'],.005,places=12)
        for allowed,expected in [(.30,True),(.25,False)]:
            r,_=design_with_shear_limit(q,allowed,.01,.1,1.,100.)
            self.assertEqual(r['passed'],expected)
        self.assertTrue(verify_flow_model(1000,.1,1.,.005,.01,100.)['flow_ok'])

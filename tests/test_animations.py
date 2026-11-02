"""웹 애니메이션 데이터가 계산 엔진과 같은 값인지 확인한다."""
import unittest
from copy import deepcopy
import numpy as np
from analysis import analyze_basic_flow, sweep_geometry_ratio
from flow import velocity_profile, velocity_gradient, shear_stress
from web_animations import basic_animation_data, sweep_animation_data, animation_html

VALUES=dict(rho=1000.,mu=.1,L=1.,Ri=.005,Ro=.01,DeltaP=100.)


class AnimationTests(unittest.TestCase):
    def test_basic_values_and_maximum(self):
        b=analyze_basic_flow(1000,.1,1,.005,.01,100)
        original=deepcopy(b)
        data=basic_animation_data(b,VALUES)
        f=data['frames'][0];args=(.005,.01,.1,1.,100.)
        np.testing.assert_array_equal(f['u'],velocity_profile(f['r'],*args))
        np.testing.assert_array_equal(f['gradient'],velocity_gradient(f['r'],*args))
        np.testing.assert_array_equal(f['tau'],shear_stress(f['r'],*args))
        self.assertEqual(f['u'][0],0.)
        self.assertEqual(f['u'][-1],0.)
        j=f['r'].index(b['r_max'])
        self.assertAlmostEqual(f['u'][j],b['u_max'],places=15)
        self.assertLess(abs(f['gradient'][j]),data['gradient_tolerance'])
        np.testing.assert_array_equal(b['u'],original['u'])
        self.assertEqual(b['Q'],original['Q'])

    def test_sweep_reuses_all_thirty_rows(self):
        table=sweep_geometry_ratio(.01,.1,1.,100.)
        before=table.copy()
        data=sweep_animation_data(table,VALUES)
        self.assertEqual(len(data['frames']),30)
        for f,row in zip(data['frames'],table):
            self.assertEqual(f['q'],row[2]);self.assertEqual(f['um'],row[4])
            self.assertEqual(f['rm'],row[5]);self.assertEqual(f['ro'],.01)
            self.assertEqual(f['ri'],row[1])
        np.testing.assert_array_equal(table,before)
        html=animation_html(data)
        self.assertNotIn('__ANIMATION_DATA__',html)
        self.assertIn('requestAnimationFrame',html)
        self.assertNotIn('https://',html)
        self.assertLess(len(html.encode('utf-8')),150000)

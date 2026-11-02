"""메뉴별 교육 설명과 실제 구현 범위를 확인한다."""
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'app.py'


class EducationTests(unittest.TestCase):
    def test_principles_and_details_all_pages(self):
        for i in range(5):
            app=AppTest.from_file(str(APP),default_timeout=30).run()
            if i:app.radio[0].set_value(app.radio[0].options[i]).run()
            self.assertFalse(app.exception)
            self.assertTrue(any(h.value=='계산 원리' for h in app.subheader))
            self.assertTrue(any(e.label=='상세 이론 및 유도 과정' for e in app.expander))
            self.assertGreater(len(app.latex),2)
            app.button[0].click().run()
            self.assertFalse(app.exception)
            if i in (2,3):
                self.assertTrue(any(m.label.startswith('목표 체적유량') for m in app.metric))
            if i==1:
                self.assertTrue(any('Sweep 표에 전단응력이 포함된 것은 아닙니다' in c.value for c in app.caption))
            if i==3:
                self.assertTrue(any('최적화 기능은 아닙니다' in c.value for c in app.caption))

    def test_basic_graphs_and_units_are_preserved(self):
        app=AppTest.from_file(str(APP),default_timeout=30).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,'4.94738 × 10⁻⁷ m³/s')
        self.assertEqual(len(app.get('vega_lite_chart'))+len(app.get('arrow_vega_lite_chart')),2)
        self.assertTrue(any(e.label=='계산 결과 검증 보고서' for e in app.expander))

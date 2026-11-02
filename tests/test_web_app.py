r"""웹 UI 회귀 검증: .venv\Scripts\python.exe -m unittest discover -s tests -v"""

from pathlib import Path
import unittest
from unittest.mock import patch
import io
import re

import numpy as np
from streamlit.testing.v1 import AppTest
import pandas as pd
from app import description, download_table, format_number, format_quantity

APP = Path(__file__).resolve().parents[1] / "app.py"


class WebAppTests(unittest.TestCase):
    def open_page(self, index=0):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        if index:
            app.radio[0].set_value(app.radio[0].options[index]).run()
        self.assertFalse(app.exception)
        return app

    def submit(self, app):
        app.button[0].click().run()
        self.assertFalse(app.exception)
        return app

    def test_basic_defaults_and_charts(self):
        app = self.submit(self.open_page())
        self.assertFalse(app.error)
        result = app.session_state["computed"][1]
        self.assertAlmostEqual(result["Q"], 4.947381662033e-07, places=18)
        self.assertAlmostEqual(result["Re"], .2099733991666, places=12)
        self.assertEqual(len(app.metric), 8)
        self.assertEqual(len(app.get("vega_lite_chart")) + len(app.get("arrow_vega_lite_chart")), 2)
        self.assertTrue(result["walls_ok"] and result["shear_zero_ok"])
        self.assertEqual(app.metric[0].value, "4.94738 × 10⁻⁷ m³/s")
        self.assertTrue(any("단위시간당" in c.value for c in app.caption))
        self.assertTrue(any("mm" in c.value for c in app.caption))
        self.assertTrue(any("정확한 전이 기준이 아니" in c.value for c in app.caption))

    def test_invalid_input_clears_previous_result_and_recovers(self):
        app = self.submit(self.open_page())
        app.number_input(key="input_Ri").set_value(.02)
        self.submit(app)
        self.assertTrue(app.error)
        self.assertNotIn("computed", app.session_state)
        self.assertEqual(len(app.metric), 0)
        app.number_input(key="input_Ri").set_value(.005)
        app.number_input(key="input_mu").set_value(0.)
        self.submit(app)
        self.assertTrue(app.error)
        app.number_input(key="input_mu").set_value(.1)
        self.submit(app)
        self.assertFalse(app.error)

    def test_sweep_table_charts_and_download(self):
        app = self.submit(self.open_page(1))
        table = app.session_state["computed"][1]
        self.assertEqual(table.shape, (30, 6))
        self.assertTrue(np.all(np.diff(table[:, 2]) < 0))
        self.assertTrue(np.all(np.diff(table[:, 4]) < 0))
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertEqual(len(app.get("vega_lite_chart")) + len(app.get("arrow_vega_lite_chart")), 2)
        # 다운로드 등의 재실행 뒤에도 계산 결과가 유지되어야 한다.
        app.run()
        self.assertEqual(len(app.get("download_button")), 1)

    def test_inverse_and_impossible_target(self):
        app = self.submit(self.open_page(2))
        result, _ = app.session_state["computed"][1]
        self.assertAlmostEqual(result["Ri"], .005, places=12)
        self.assertLess(result["relative_error"], 1e-8)
        app.number_input(key="input_Q_target").set_value(1.)
        self.submit(app)
        self.assertTrue(app.warning)
        self.assertEqual(len(app.metric), 0)

    def test_shear_pass_and_fail(self):
        app = self.submit(self.open_page(3))
        self.assertTrue(app.session_state["computed"][1][0]["passed"])
        app.number_input(key="input_tau_allow").set_value(.25)
        self.submit(app)
        result = app.session_state["computed"][1][0]
        self.assertFalse(result["passed"])
        self.assertTrue(app.error)
        self.assertAlmostEqual(result["excess"], .04101064033336, places=12)

    def test_model_verification(self):
        app = self.submit(self.open_page(4))
        result = app.session_state["computed"][1]
        self.assertTrue(result["flow_ok"] and result["decreasing"] and result["recovery_ok"])
        self.assertLess(result["relative_error"], 1e-8)
        self.assertEqual(result["limit_table"].shape, (5, 5))
        self.assertEqual(len(app.get("download_button")), 1)

    def test_navigation_and_high_re_warning(self):
        app = self.open_page()
        app.number_input(key="input_DeltaP").set_value(1100000.)
        self.submit(app)
        self.assertEqual(app.session_state["computed"][1]["laminar_status"], "CAUTION")
        self.assertTrue(app.warning)
        app.radio[0].set_value(app.radio[0].options[1]).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 0)
        self.assertNotIn("computed", app.session_state)

    def test_display_format_and_units(self):
        cases = [(4.947381662033e-7, "4.94738 × 10⁻⁷"),
                 (-4.336808689942e-17, "-4.33681 × 10⁻¹⁷"),
                 (1.234567e6, "1.23457 × 10⁶"),
                 (.2099733991666, "0.209973"), (0., "0"), (-0., "0")]
        for number, expected in cases:
            self.assertEqual(format_number(number), expected)
        self.assertEqual(format_quantity(4.947381662033e-7, "m³/s"), "4.94738 × 10⁻⁷ m³/s")
        self.assertNotRegex(format_number(99999.99), r"\de[+-]")
        self.assertIn("무차원수", description("Reynolds 수 Re"))
        self.assertIn("백분율", description("목표유량 상대오차 [%]"))

    def test_csv_keeps_original_precision(self):
        original = pd.DataFrame({"Q": [4.947381662033e-7], "Ri": [.005]})
        with patch("app.st.download_button") as button:
            download_table(original, "test.csv")
        data = button.call_args.args[1]
        expected = original.to_csv(index=False, float_format="%.12e").encode("utf-8-sig")
        self.assertEqual(data, expected)
        self.assertIn(b"4.947381662033e-07", data)
        self.assertNotIn("×".encode(), data)
        restored = pd.read_csv(io.BytesIO(data))
        np.testing.assert_allclose(restored, original, rtol=1e-12)

    def test_all_pages_use_display_not_e_notation(self):
        for index in range(5):
            app = self.submit(self.open_page(index))
            for metric in app.metric:
                self.assertFalse(re.search(r"\de[+-]\d", metric.value), metric.value)
            if index in (1, 4):
                # 화면 표와 계산 원본을 분리해도 다운로드 및 검증은 유지된다.
                self.assertTrue(app.get("download_button"))


if __name__ == "__main__":
    unittest.main()

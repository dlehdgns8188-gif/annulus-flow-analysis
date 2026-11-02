"""공개 배포용 화면 문구·의존성·Git 제외 규칙 검증. 외부 통신 없음."""

import ast
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

from packaging.requirements import Requirement
from streamlit.testing.v1 import AppTest
from app import APP_TITLE, APP_SUBTITLE, APP_FOOTER, PAGE_DESCRIPTIONS, PAGES
from app import line_plot
from unittest.mock import patch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_chart_unit_columns_are_literal_fields(self):
        frame = pd.DataFrame({'반지름 r [m]': [.005, .007, .01], '속도 u [m/s]': [0., .003, 0.]})
        with patch('app.st.altair_chart') as chart:
            line_plot(frame, *frame.columns, point=(.007, .003))
        spec = chart.call_args.args[0].to_dict()
        for layer in spec['layer']:
            self.assertEqual(layer['encoding']['x']['field'], '반지름 r \\[m\\]')
            self.assertEqual(layer['encoding']['y']['field'], '속도 u \\[m/s\\]')

    def test_branding_descriptions_and_footer_all_pages(self):
        for index, page in enumerate(PAGES):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
            if index:
                app.radio[0].set_value(page).run()
            self.assertFalse(app.exception)
            self.assertTrue(any(title.value == APP_TITLE for title in app.title))
            self.assertTrue(any(c.value == APP_SUBTITLE for c in app.caption))
            self.assertTrue(any(h.value == page for h in app.header))
            self.assertTrue(any(m.value == PAGE_DESCRIPTIONS[page] for m in app.markdown))
            self.assertTrue(any(c.value == APP_FOOTER for c in app.caption))
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(sum(c.value == APP_FOOTER for c in app.caption), 1)

    def test_error_page_keeps_footer(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
        app.number_input(key='input_Ri').set_value(.02)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertTrue(any(c.value == APP_FOOTER for c in app.caption))

    def test_requirements_cover_direct_imports_and_installed_versions(self):
        requirements = [Requirement(line) for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines()
                        if line.strip() and not line.startswith('#')]
        declared = {r.name.lower() for r in requirements}
        imports = set()
        for filename in ('app.py', 'flow.py', 'analysis.py', 'main.py'):
            tree = ast.parse((ROOT / filename).read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(n.name.split('.')[0] for n in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split('.')[0])
        external = imports & {'numpy', 'scipy', 'matplotlib', 'streamlit', 'pandas', 'altair'}
        self.assertEqual(external, declared)
        for requirement in requirements:
            self.assertIn(importlib.metadata.version(requirement.name), requirement.specifier)
        self.assertIn('-r requirements.txt', (ROOT / 'requirements-web.txt').read_text(encoding='utf-8'))

    @unittest.skipUnless(shutil.which('git'), 'Git이 설치된 환경에서 제외 규칙 확인')
    def test_gitignore_excludes_private_and_generated_files(self):
        with tempfile.TemporaryDirectory(prefix='annulus-ignore-') as directory:
            subprocess.run(['git', 'init', '--quiet', directory], check=True, capture_output=True)
            shutil.copy2(ROOT / '.gitignore', Path(directory) / '.gitignore')
            ignored = ['.venv/Scripts/python.exe', '__pycache__/app.pyc', '.env', '.env.production',
                       '.streamlit/secrets.toml', 'tmp/log.txt', 'results/parameter_sweep.csv',
                       'private/data.txt', '개인정보/이름.txt', '과제.pdf', 'error.log']
            # Windows의 text 파이프 CRLF가 파일명에 포함되지 않도록 NUL 구분 사용.
            check = subprocess.run(['git', 'check-ignore', '--no-index', '-z', '--stdin'], cwd=directory,
                                   input=('\0'.join(ignored)+'\0').encode('utf-8'), capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertEqual(len(check.stdout.split(b'\0')) - 1, len(ignored))
            public = ['app.py', 'flow.py', 'analysis.py', 'main.py', 'README.md', 'requirements.txt',
                      '.streamlit/config.toml', '.github/workflows/tests.yml', 'tests/test_release.py',
                      '실행.bat', '웹실행.bat']
            check = subprocess.run(['git', 'check-ignore', '--no-index', '-z', '--stdin'], cwd=directory,
                                   input=('\0'.join(public)+'\0').encode('utf-8'), capture_output=True)
            self.assertEqual(check.returncode, 1, check.stdout + check.stderr)

    def test_cloud_config_and_portable_entrypoint(self):
        config = tomllib.loads((ROOT / '.streamlit/config.toml').read_text(encoding='utf-8'))
        self.assertNotIn('server', config)  # Cloud의 host/port를 강제로 덮어쓰지 않는다.
        self.assertFalse(config['browser']['gatherUsageStats'])
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                # 모듈 실행 안내 docstring을 제외한 런타임 문자열에 OS 종속 경로가 없어야 한다.
                if node.value.startswith('기존 Annulus'):
                    continue
                self.assertNotIn('C:\\Users\\', node.value)
        workflow = (ROOT / '.github/workflows/tests.yml').read_text(encoding='utf-8')
        self.assertIn('ubuntu-latest', workflow)
        self.assertIn('python-version: "3.12"', workflow)
        self.assertIn('python -m unittest discover -s tests -v', workflow)


if __name__ == '__main__':
    unittest.main()

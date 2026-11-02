# 동심 이중관(Annulus) 층류 유동 해석 프로그램

**화공유체역학 팀프로젝트 | 유체역학 10조**

동심 이중관의 정상·비압축성 Newtonian 유체·축대칭·완전발달 층류와 양쪽 벽 no-slip을 가정하는 교육용 해석 프로그램입니다. 웹 버전과 기존 Windows 터미널 버전을 함께 제공합니다.

## 기능

1. **기본 유동 해석:** 물성·형상·압력차를 입력해 속도·전단응력 분포, Q, V, 최대속도·위치, 수력직경, Re를 계산합니다.
2. **형상비 Parameter Sweep:** Ri/Ro = 0.1~0.9의 30조건을 비교하고 그래프와 전체 CSV를 제공합니다.
3. **목표 유량 역설계:** 기존 SciPy brentq 근찾기로 Ri를 찾습니다.
4. **목표 유량 + 허용 전단응력 설계:** 두 벽 전단응력 절댓값 중 큰 값을 허용값과 비교합니다.
5. **모델 검증:** 수치적분·해석식 유량 비교, no-slip, zero-shear, 원관 극한, 기본값 역설계 재현을 확인합니다.

기본 해석과 모델 검증 화면의 **수치 검증 및 이론 일치성 판정**은 같은 분석 보고서를 재사용합니다.
양쪽 벽에서 속도식을 직접 평가해 각각 `|u| < 1e-9 m/s`를 확인하고, 도함수 근의 위치·기울기·전단응력을 표시합니다.
기울기 허용오차는 `1e-10 + 1e-10*max(|벽면 기울기|)` [1/s], 전단응력은 `1e-12 + 1e-10*max(|벽면 전단응력|)` [Pa]입니다.
유량은 독립 해석식과 기존 SciPy quad(QUADPACK 적응형 Gauss–Kronrod)를 비교하며 상대오차 **0.01% 미만**을 요구합니다.
`|Q_analytical| <= 1e-15 m³/s`에서는 적분 절대오차 요청과 매우 좁은 간극의 상쇄 오차를 고려해, 상대 비교가 맞더라도 CAUTION으로 표시합니다. 기준 초과나 비물리적 부호는 FAIL입니다.
이 검증 실패는 계산 결과를 삭제하거나 프로그램을 종료하지 않고 화면에 표시됩니다.

전단응력 성분 `τ_rz=μ du/dr`와 벽이 유체에 주는 힘/면적 `t_z`는 다릅니다. 유체영역 외향법선이 내벽 -r, 외벽 +r이므로 `t_z(inner)=-τ_rz(Ri)`, `t_z(outer)=+τ_rz(Ro)`입니다. 두 벽의 힘은 모두 유동에 저항합니다.
기존 웹 입력은 양의 압력차만 지원하며, 검증 계산의 부호 관계는 음의 압력차에서도 별도 테스트합니다.
극단적인 `Ri/Ro=0.999999`에서는 기존 해석 유량식의 상쇄 오차가 커질 수 있습니다. 물리식은 그대로 유지하며 이 영역의 정확도를 PASS로 보장하지 않습니다.

화면은 6자리 유효숫자와 `4.94738 × 10⁻⁷ m³/s` 형태의 지수 표기를 사용합니다. 길이는 m/mm로 병기합니다. 표시 변환은 계산값에 적용하지 않으며, CSV는 기존 `%.12e` 형식의 수치 정밀도를 유지합니다.

전단응력 부호는 방향 정보이고 허용값 판정에는 절댓값을 사용합니다. Re 판정은 원관 기준을 참고한 교육용 예비 판정으로 Annulus의 실제 전이점을 확정하지 않습니다. 현재 입력은 양의 압력차를 지원합니다.

## 파일 구조와 의존관계

```text
app.py ──→ analysis.py ──→ flow.py ──→ NumPy / SciPy
  │             ↑
  │          main.py ──→ Matplotlib
  └── Streamlit / pandas / Altair / NumPy
```

`app.py`는 물리식을 복제하지 않고 기존 계산 함수를 호출합니다. `실행.bat`는 `main.py`, `웹실행.bat`는 `app.py`를 실행합니다. 배치파일은 Windows 편의 기능이며 Linux 웹 배포에서 사용하지 않습니다.

교육용 애니메이션은 `web_animations.py`가 기존 계산값을 준비하고 `animation_view.html`이 브라우저 Canvas로 재생합니다. 기본 해석의 입자 속도는 실제 u(r)에 비례하며, 8초 주기와 입자 재생 배율은 실제 유속·물리 경과시간과 구분해 표시합니다. 양쪽 벽의 점은 정지하고 r_max를 표시합니다. 형상비 애니메이션은 기존 Sweep의 30개 정상상태를 차례로 비교하며 관 변형 중의 비정상 유동 계산은 아닙니다. 재생·일시정지, 프레임 이동을 지원하고 외부 CDN이나 새 라이브러리는 사용하지 않습니다.

## 로컬 설치 및 웹 실행

Python **3.12**를 권장합니다. 저장소를 내려받은 프로젝트 폴더에서 실행하세요.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

이미 이 프로젝트의 `.venv`가 설치되어 있다면 재생성할 필요 없이 `웹실행.bat`를 더블클릭하세요. 기존 가상환경에 pip가 없는 경우 `python -m ensurepip --upgrade`로 설치 도구를 준비하거나 별도의 Python 설치에서 가상환경을 새로 만드세요.

Linux / macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

브라우저가 자동으로 열리지 않으면 터미널에 표시된 localhost 주소를 여세요. 사이드바에서 기능을 고르고 **계산 실행**을 누릅니다. 서버 종료는 실행한 터미널에서 Ctrl+C입니다.

기존 Windows 터미널 버전은 `실행.bat` 또는 다음 명령을 사용합니다.

```powershell
.\.venv\Scripts\python.exe main.py
```

기본 입력: ρ=1000 kg/m³, μ=0.1 Pa·s, L=1 m, Ri=0.005 m, Ro=0.010 m, ΔP=100 Pa. 기준 결과는 Q≈4.947381662033×10⁻⁷ m³/s, Re≈0.209973입니다. 기본 목표유량에서 허용 전단응력 0.30 Pa는 PASS, 0.25 Pa는 FAIL입니다.

## 자동 테스트

```bash
python -m unittest discover -s tests -v
```

프로젝트 가상환경의 Python으로 실행하세요. 웹 5개 메뉴, 입력 오류 복구, 표시값·단위·설명, 그래프 생성, CSV 정밀도, 설계 PASS/FAIL과 모델 검증을 검사합니다. `.github/workflows/tests.yml`은 업로드 후 Ubuntu / Python 3.12에서 같은 테스트를 실행하도록 준비한 설정입니다. 이 파일을 준비한 것만으로 실제 Linux 테스트가 완료된 것은 아닙니다.

## GitHub에 포함할 파일

- `app.py`, `flow.py`, `analysis.py`, `main.py`
- `web_animations.py`, `animation_view.html` (애니메이션 화면에 필요)
- `requirements.txt`, `requirements-web.txt`
- `README.md`, `웹사용법.md`
- `실행.bat`, `웹실행.bat`
- `tests/test_web_app.py`, `tests/test_release.py`, `tests/test_numerical_verification.py`
- `tests/test_animations.py`
- `.gitignore`, `.streamlit/config.toml`, `.github/workflows/tests.yml`

이 목록의 소스·설정·문서만 업로드하면 됩니다. `.venv/`, `__pycache__/`, `tmp/`, `results/`, `.env*`, `.streamlit/secrets.toml`, 개인 설정·인증서·로그·개인 문서·수업 PDF는 제외합니다. CSV 다운로드는 메모리에서 만들어지므로 기존 결과 파일은 웹 배포에 필요하지 않습니다.

`.gitignore`는 파일 내용을 검사하거나 이미 Git에 추적 중인 파일을 자동으로 제거하지 않습니다. 업로드 전 선택한 파일 목록과 내용을 확인하고, 위 목록에 없는 파일은 개별 검토하세요. GitHub 웹의 파일 업로드 화면에서는 `.gitignore`가 수동 선택을 막아주지 않으므로 폴더 전체를 끌어넣지 마세요.

## Streamlit Community Cloud 배포 절차 (사용자가 직접 진행)

1. GitHub 저장소를 만들고 위 소스 파일을 같은 구조로 업로드합니다.
2. Community Cloud에서 GitHub 계정을 연결하고 **Create app**을 선택합니다.
3. 저장소·브랜치를 지정하고 진입 파일을 루트의 **`app.py`**로 설정합니다.
4. Advanced settings에서 Python **3.12**를 선택합니다. 이 앱은 API 키나 별도 secrets가 필요하지 않습니다.
5. Deploy를 누르면 루트 `requirements.txt`로 의존성을 설치합니다.
6. 배포 로그와 5개 메뉴를 확인하고 기본 Q·Re 및 CSV 다운로드를 확인합니다.

Windows 절대경로, 로컬 글꼴, `.venv` 업로드, `packages.txt`의 OS 패키지에 의존하지 않습니다. 웹 차트는 브라우저에서 표시하며 Windows 배치파일은 Cloud에서 실행하지 않습니다. 실제 Linux/Cloud 빌드 성공 여부는 배포 시 의존성 설치와 테스트 로그로 최종 확인해야 합니다.

공식 안내: [앱 배포](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [의존성 설정](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [비밀정보 관리](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

이 작업에서는 GitHub 업로드·push·외부 배포를 수행하지 않았습니다.

---

유체역학 10조 · Annulus Flow Analysis

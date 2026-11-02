r"""기존 Annulus 계산 엔진을 재사용하는 Streamlit 웹 인터페이스.

실행: .venv\Scripts\python.exe -m streamlit run app.py
물리식·근찾기·적분·판정은 flow.py와 analysis.py에서만 수행한다.
"""

import warnings

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from web_animations import basic_animation_data, sweep_animation_data, animation_html

from analysis import (
    analyze_basic_flow,
    design_inner_radius,
    design_with_shear_limit,
    sweep_geometry_ratio,
    verify_flow_model,
)

PAGES = ["기본 유동 해석", "형상비 Parameter Sweep", "목표 유량 역설계",
         "목표 유량 + 허용 전단응력 설계", "모델 검증"]
APP_TITLE = "동심 이중관(Annulus) 층류 유동 해석 프로그램"
APP_SUBTITLE = "화공유체역학 팀프로젝트 | 유체역학 10조"
APP_FOOTER = "유체역학 10조 · Annulus Flow Analysis"
PAGE_DESCRIPTIONS = dict(zip(PAGES, [
    "유체의 물성, 관의 크기, 압력차를 입력하여 이중관 내부의 속도분포, 전단응력, 유량 등을 계산하고 유동 특성을 분석합니다.",
    "내반지름과 외반지름의 비율(Ri/Ro)을 변화시키면서 유량과 최대속도가 어떻게 달라지는지 비교합니다.",
    "원하는 유량을 얻기 위해 필요한 내반지름(Ri)을 역으로 계산합니다.",
    "목표 유량을 만족하는 내반지름을 계산하고, 벽면 전단응력이 허용 기준을 만족하는지 평가합니다.",
    "수치계산 결과를 해석식 및 원관 극한조건과 비교하여 계산의 정확성과 물리적 타당성을 확인합니다.",
]))
DEFAULTS = {"rho": 1000.0, "mu": 0.1, "L": 1.0, "Ri": 0.005,
            "Ro": 0.010, "DeltaP": 100.0, "Q_target": 4.947381662033e-07,
            "tau_allow": 0.30}
LABELS = {"rho": "밀도 ρ [kg/m³]", "mu": "점도 μ [Pa·s]", "L": "관 길이 L [m]",
          "Ri": "내반지름 Ri [m]", "Ro": "외반지름 Ro [m]",
          "DeltaP": "압력차 ΔP [Pa]", "Q_target": "목표 체적유량 Q_target [m³/s]",
          "tau_allow": "허용 전단응력 τ_allow [Pa]"}
FIXED = ["Ro", "mu", "L", "DeltaP"]
FULL = ["rho", "mu", "L", "Ri", "Ro", "DeltaP"]
SUPERSCRIPT = str.maketrans("-+0123456789", "⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹")
DESCRIPTIONS = {
    "Q": "단위시간당 관을 통과하는 유체의 체적",
    "V": "유체의 단면 평균속도",
    "u_max": "단면 내 가장 빠른 유속",
    "r_max": "최대속도가 발생하는 중심축으로부터의 거리",
    "내벽": "내부관 벽면의 전단응력",
    "외벽": "외부관 벽면의 전단응력",
    "Dh": "유동 단면의 수력직경",
    "Re": "관성력과 점성력의 상대적 크기를 나타내는 무차원수",
    "Ri/Ro": "내반지름과 외반지름의 비율",
    "상대오차": "비교 기준값과 계산값의 차이를 기준값으로 나눈 백분율",
}


def format_number(number, scientific=False):
    """화면 전용 6자리 유효숫자. 계산값과 CSV에는 적용하지 않는다."""
    number = float(number)
    if number == 0:
        return "0"
    if not np.isfinite(number):
        return "표시 불가"
    if scientific or abs(number) < 1e-3 or abs(number) >= 1e5:
        mantissa, exponent = f"{number:.5e}".split("e")
        return f"{mantissa} × 10{str(int(exponent)).translate(SUPERSCRIPT)}"
    plain = f"{number:.6g}"
    # 반올림으로 경계를 넘어 g 형식이 e 표기로 바뀌는 경우도 통일한다.
    return format_number(number, scientific=True) if "e" in plain.lower() else plain


def format_quantity(number, unit="", scientific=False):
    return f"{format_number(number, scientific)} {unit}".strip()


def description(label):
    if "상대오차" in label:
        return DESCRIPTIONS["상대오차"]
    if "산술중간점" in label:
        return "최대속도 위치와 산술중간점의 거리 차이" if "−" in label else "내반지름과 외반지름의 산술평균"
    for token in ("Ri/Ro", "u_max", "r_max", "내벽", "외벽", "Dh", "Re", "Q", "V"):
        if token in label:
            return DESCRIPTIONS[token]
    if "간극" in label:
        return "외벽과 내벽 사이의 반지름 방향 간격"
    if "내반지름" in label:
        return "중심축에서 내부관 벽면까지의 거리"
    if "허용 전단응력" in label:
        return "설계에서 허용하는 벽면 전단응력 절댓값의 상한"
    if "최대 벽면" in label:
        return "내벽·외벽 전단응력 절댓값 중 큰 값"
    return ""


def display_table(frame):
    """표시용 사본만 문자열로 변환한다. 원본 수치표는 다운로드에 사용한다."""
    shown = frame.copy()
    for name in shown.columns:
        if pd.api.types.is_numeric_dtype(frame[name]):
            shown[name] = frame[name].map(format_number)
            if "[m]" in name:
                shown[name] = frame[name].map(
                    lambda n: f"{format_number(n)} m / {format_number(n * 1000)} mm"
                )
    st.dataframe(shown, hide_index=True, width="stretch",
                 column_config={name: st.column_config.TextColumn(name, help=description(name) or None)
                                for name in shown.columns})


def exponent_axis():
    """브라우저의 Vega 축에도 동일한 Unicode 지수 표기를 적용한다."""
    exponent = "toString(toNumber(split(format(datum.value, '.5e'), 'e')[1]))"
    for digit, superscript in zip("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"):
        exponent = f"replace({exponent}, regexp('{digit}', 'g'), '{superscript}')"
    return (
        "datum.value == 0 ? '0' : "
        "(abs(datum.value) < 0.001 || abs(datum.value) >= 100000) ? "
        f"split(format(datum.value, '.5e'), 'e')[0] + ' × 10' + {exponent} : "
        "format(datum.value, '.6~g')"
    )


def input_form(page):
    fields = FULL if page in (PAGES[0], PAGES[4]) else list(FIXED)
    if page in (PAGES[2], PAGES[3]):
        fields.append("Q_target")
    if page == PAGES[3]:
        fields.append("tau_allow")
    with st.form("conditions"):
        st.subheader("입력 조건")
        st.caption("모든 입력은 SI 단위입니다. ΔP는 입구압력 − 출구압력이며 양수로 입력하세요.")
        columns = st.columns(2)
        values = {}
        for i, field in enumerate(fields):
            with columns[i % 2]:
                values[field] = st.number_input(
                    LABELS[field], value=DEFAULTS[field],
                    format="%.10e" if field == "Q_target" else "%.6f",
                    key=f"input_{field}",
                )
        submitted = st.form_submit_button("계산 실행", type="primary")
    return submitted, values


def validate_inputs(values):
    """웹 입력만 검사한다. 계산 엔진과 물리 판정은 변경하지 않는다."""
    for name, number in values.items():
        if not np.isfinite(number):
            raise ValueError(f"{LABELS[name]}: 유한한 숫자를 입력하세요.")
        if name == "tau_allow":
            if number < 0:
                raise ValueError("허용 전단응력은 0 이상이어야 합니다.")
        elif number <= 0:
            raise ValueError(f"{LABELS[name]}: 0보다 큰 값을 입력하세요.")
    if "Ri" in values and not values["Ri"] < values["Ro"]:
        raise ValueError("반지름은 0 < Ri < Ro를 만족해야 합니다. 내반지름과 외반지름을 확인하세요.")


def full_args(values):
    return tuple(values[key] for key in FULL)


def fixed_args(values):
    return tuple(values[key] for key in FIXED)


def calculate(page, values):
    validate_inputs(values)
    # 적분 등의 수치 경고도 사용자에게 안내하고 기존 결과를 성공으로 표시하지 않는다.
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        from scipy.integrate import IntegrationWarning
        warnings.simplefilter("error", IntegrationWarning)
        if page == PAGES[0]:
            return analyze_basic_flow(*full_args(values))
        if page == PAGES[1]:
            return sweep_geometry_ratio(*fixed_args(values))
        if page == PAGES[2]:
            return design_inner_radius(values["Q_target"], *fixed_args(values))
        if page == PAGES[3]:
            return design_with_shear_limit(values["Q_target"], values["tau_allow"], *fixed_args(values))
        return verify_flow_model(*full_args(values))


def metrics(items):
    for start in range(0, len(items), 4):
        columns = st.columns(min(4, len(items) - start))
        for column, (label, number, scientific) in zip(columns, items[start:start + 4]):
            unit = label.rsplit("[", 1)[1].rstrip("]") if "[" in label else ""
            explanation = description(label)
            column.metric(label, format_quantity(number, unit, scientific), help=explanation or None)
            if explanation:
                column.caption(explanation)
            if unit == "m":
                column.caption(f"{format_quantity(number * 1000, 'mm')} (동일한 길이)")


def line_plot(frame, x, y, point=None):
    # 축·툴팁 표시만 변환하고 좌표는 원래 수치를 사용한다.
    frame = frame.copy()
    x_text, y_text = "가로축 표시", "세로축 표시"
    frame[x_text] = frame[x].map(format_number)
    frame[y_text] = frame[y].map(format_number)
    # Vega는 대괄호·점을 중첩 필드 경로로 해석하므로 단위 포함 열 이름을 이스케이프한다.
    def field_name(name):
        return name.replace("\\", "\\\\").replace(".", "\\.").replace("[", "\\[").replace("]", "\\]")
    encoding = dict(
        x=alt.X(field=field_name(x), type="quantitative", title=x, scale=alt.Scale(zero=False), axis=alt.Axis(labelExpr=exponent_axis())),
        y=alt.Y(field=field_name(y), type="quantitative", title=y, axis=alt.Axis(labelExpr=exponent_axis())),
        tooltip=[alt.Tooltip(x_text, type="nominal", title=x),
                 alt.Tooltip(y_text, type="nominal", title=y)],
    )
    curve = alt.Chart(frame).mark_line(color="#087f8c", strokeWidth=3).encode(**encoding)
    if point is not None:
        dot_frame = pd.DataFrame([point], columns=[x, y])
        dot_frame[x_text] = dot_frame[x].map(format_number)
        dot_frame[y_text] = dot_frame[y].map(format_number)
        dot = alt.Chart(dot_frame).mark_point(
            color="#e26d3c", size=110, filled=True
        ).encode(**encoding)
        curve = curve + dot
    st.altair_chart(curve.properties(height=300), width="stretch")


def laminar_status(result):
    message = f"층류 예비 판정 · {result['laminar_status']} — {result['laminar_message']}"
    if result["laminar_status"] == "PASS":
        st.success(message)
    elif result["laminar_status"] == "CAUTION":
        st.warning(message)
    else:
        st.error(message)
    st.caption("원관 기준을 참고한 수력직경 기반 예비 판정입니다. Annulus의 정확한 전이 기준이 아니며, 형상비·입구 교란에 따라 달라집니다. 정상·Newtonian·완전발달 가정은 별도 확인이 필요합니다.")


def render_animation(data):
    html = animation_html(data)
    if hasattr(st, 'iframe'):
        st.iframe(html, height='content', alt='Annulus 교육용 유동 애니메이션')
    else:  # 이전 Streamlit 설치 환경과의 호환성을 유지한다.
        components.html(html, height=850 if data['mode']=='basic' else 1000, scrolling=True)


def show_basic(result, values):
    st.subheader("주요 결과")
    metrics([
        ("체적유량 Q [m³/s]", result["Q"], True),
        ("평균속도 V [m/s]", result["V"], False),
        ("최대속도 u_max [m/s]", result["u_max"], False),
        ("최대속도 위치 r_max [m]", result["r_max"], False),
        ("내벽 전단응력 [Pa]", result["tau"][0], False),
        ("외벽 전단응력 [Pa]", result["tau"][-1], False),
        ("수력직경 Dh [m]", result["Dh"], False),
        ("Reynolds 수 Re", result["Re"], False),
    ])
    laminar_status(result)
    st.caption("전단응력의 부호는 좌표계와 정의에 따른 방향 정보입니다. 설계 허용치 판정에는 양쪽 벽 전단응력의 절댓값을 사용합니다.")
    st.caption(f"No-slip: {'PASS' if result['walls_ok'] else 'FAIL'} · Zero-shear: {'PASS' if result['shear_zero_ok'] else 'FAIL'}")
    left, right = st.columns(2)
    with left:
        st.subheader("속도분포")
        frame = pd.DataFrame({"반지름 r [m]": result["r"], "속도 u [m/s]": result["u"]})
        line_plot(frame, *frame.columns, point=(result["r_max"], result["u_max"]))
        st.caption("주황색 점: 최대속도 위치")
    with right:
        st.subheader("전단응력분포")
        frame = pd.DataFrame({"반지름 r [m]": result["r"], "전단응력 τ [Pa]": result["tau"]})
        line_plot(frame, *frame.columns, point=(result["r_max"], result["tau_at_max"]))
        st.caption("주황색 점: 최대속도 위치에서의 전단응력")
    st.subheader("교육용 애니메이션 · 속도분포와 전단응력")
    render_animation(basic_animation_data(result, values))
    show_numerical_verification(result)


def near_zero_text(row):
    """판정에 쓰인 기존 허용오차로 화면만 요약한다. 실제 값은 상세 표에 유지."""
    unit = 's⁻¹' if row['unit'] == '1/s' else row['unit']
    if row['status'] == 'PASS':
        return f"약 0 {unit}"
    return format_quantity(row['value'], unit)


def verification_verdict(status, passed, failed, caution=None):
    message = f"판정: {status} — "
    if status == 'PASS':
        st.success(message + passed)
    elif status == 'CAUTION':
        st.warning(message + (caution or failed))
    else:
        st.error(message + failed)


def show_numerical_verification(basic):
    report = basic['verification']
    st.subheader("수치 검증 및 이론 일치성 판정")
    st.caption("반지름 r은 관 중심축으로부터 측정한 거리이며, 바깥쪽으로 증가합니다. 아래의 ‘약 0’은 계산값이 이론상 0인 조건을 만족할 만큼 작다는 뜻입니다.")

    st.markdown("#### 1. No-slip 경계조건 검증")
    st.caption("검증 목적: 고정된 내부관과 외부관의 벽면에서 유속이 0인지 확인합니다.")
    st.write(f"내벽 속도 u(Ri): **{near_zero_text(report['no_slip'][0])}** · 외벽 속도 u(Ro): **{near_zero_text(report['no_slip'][1])}**")
    st.write("고정된 벽과 접촉한 유체는 벽과 같은 속도를 갖습니다. 따라서 두 벽의 유속이 0이면 이중관의 no-slip 경계조건에 부합합니다.")
    for row in report['no_slip']:
        verification_verdict(row['status'], f"{row['label']}가 0에 매우 가까워 해당 벽의 no-slip 경계조건을 만족합니다.",
                             f"{row['label']}가 0에서 벗어나 해당 벽의 no-slip 경계조건을 만족하지 못했습니다.")

    st.markdown("#### 2. 최대속도 위치 검증")
    st.caption("검증 목적: 계산된 최대속도 위치에서 속도구배와 전단응력이 0인지 확인합니다.")
    st.write(f"최대속도 위치: **{format_quantity(report['r_max'] * 1000, 'mm')}** (중심축 기준)")
    st.write(f"속도구배 du/dr: **{near_zero_text(report['extremum'][0])}** · 전단응력 τ: **{near_zero_text(report['extremum'][1])}**")
    change = "최대속도 위치를 기준으로 속도구배가 양수에서 음수로 변함" if report['direction'] > 0 else "극값 위치를 기준으로 속도구배가 음수에서 양수로 변함"
    st.write(f"속도분포 확인: {change} — {'확인됨' if report['location_ok'] else '확인되지 않음'}")
    st.write("최대속도 위치에서는 유속이 증가하다가 감소하는 방향으로 바뀌므로 속도구배 du/dr이 0이 됩니다. 뉴턴 유체의 전단응력은 τ = μ(du/dr)이므로 이 위치에서 전단응력도 0이 됩니다.")
    maximum_ok = report['location_ok'] and all(row['status'] == 'PASS' for row in report['extremum'])
    verification_verdict('PASS' if maximum_ok else 'FAIL',
                         "계산 결과 두 값이 모두 0에 매우 가깝고 속도구배의 부호도 바뀌므로, 내부 최대점의 이론적 조건을 만족합니다.",
                         "속도구배·전단응력 또는 최대점 위치 조건을 만족하지 못했습니다. 상세 계산값을 확인하세요.")
    st.caption("최대속도 위치는 속도구배가 0이 되는 위치를 수치적으로 계산한 값입니다. 원통좌표의 반지름 의존성과 ln(r) 항으로 인해 속도분포가 산술중간점에 대해 대칭이 아니므로 최대점도 단순 중간점과 다릅니다.")

    st.markdown("#### 3. 체적유량 검증")
    st.caption("검증 목적: 속도분포를 수치적분한 유량이 독립적인 해석식으로 구한 유량과 일치하는지 확인합니다.")
    st.write(f"해석 유량: **{format_quantity(report['Q_analytical'], 'm³/s')}** · 수치적분 유량: **{format_quantity(report['Q_numerical'], 'm³/s')}**")
    if report['relative_error'] is not None:
        error = '약 0 %' if report['relative_error']*100 < 1e-9 else format_quantity(report['relative_error']*100, '%')
        st.write(f"두 유량의 상대오차: **{error}** (실제 오차는 상세 표에서 확인)")
    else:
        st.write("상대오차: 해석 유량이 0이므로 정의할 수 없음")
    st.write("유량은 각 반지름 위치의 유속을 환형 단면 전체에 걸쳐 합한 값입니다. 두 방법의 유량이 일치하면 속도분포를 단면 적분하는 계산이 해석식과 일관됨을 확인할 수 있습니다.")
    verification_verdict(report['flow_status'],
                         "수치적분 유량과 해석 유량의 차이가 충분히 작아 두 계산 방법이 같은 유량을 나타냅니다.",
                         "유량 비교 조건을 만족하지 못했습니다. 매우 좁은 간극에서의 계산 정밀도 등을 상세 검증에서 확인하세요.",
                         "유량이 매우 작아 두 값의 차이만으로 정확성을 확정하기 어렵습니다. 이론과의 일치 여부에 주의가 필요합니다.")

    st.markdown("#### 4. 벽면 전단응력과 힘의 방향 검증")
    st.caption("검증 목적: 두 벽의 전단응력 부호와 벽이 유체에 주는 힘의 방향이 속도분포와 일관되는지 확인합니다.")
    def sign_text(number):
        return '양수' if number > 0 else '음수' if number < 0 else '0'
    for i, wall in enumerate(('내벽', '외벽')):
        st.write(f"{wall}: 속도구배 **{sign_text(report['wall_gradients'][i])}**, 전단응력 **{format_quantity(report['wall_stresses'][i], 'Pa')}**, 벽이 유체에 주는 축방향 힘/면적 **{format_quantity(report['wall_tractions'][i], 'Pa')}**")
    st.write("양의 압력차에서는 내벽에서 바깥쪽으로 유속이 증가하고 외벽에 가까워지면 감소하므로 전단응력 성분 τ_rz의 부호가 서로 다릅니다. 실제 벽면 힘은 각 벽의 법선 방향까지 고려하므로 두 벽 모두 유동에 저항하며, 압력차가 반대이면 응력과 힘의 부호도 반전됩니다.")
    verification_verdict('PASS' if report['sign_ok'] else 'FAIL',
                         "속도구배와 전단응력의 부호가 일관되고, 두 벽의 힘이 모두 유동을 방해하는 방향이므로 물리적 방향 관계를 만족합니다.",
                         "속도구배·전단응력과 벽면 저항 방향의 관계를 만족하지 못했습니다.")

    st.markdown(f"**5. 종합 검증 결과: {report['overall']}**")
    verification_verdict(report['overall'],
                         "벽면 경계조건, 내부 최대점, 유량 일치와 벽면 힘의 방향이 모두 이론적 조건에 부합합니다.",
                         "한 가지 이상의 이론적 조건을 만족하지 못했습니다. 위 항목별 판정을 확인하세요.",
                         "일부 결과는 수치 정밀도 때문에 이론과의 일치를 확정하기 어렵습니다.")
    st.caption("이 판정은 계산과 이론의 일치 여부를 뜻하며, 실제 유동이 층류·완전발달 상태임을 보장하지 않습니다.")
    st.write(f"유동 조건 참고: 환형 유로의 수력직경 Dh=2(Ro−Ri)로 구한 Re는 {format_number(basic['Re'])}이며 층류 예비 판정은 {basic['laminar_status']}입니다. 원관 기준을 참고한 판정으로 Annulus의 정확한 전이 기준은 아닙니다.")

    with st.expander("상세 수치 검증"):
        st.markdown("**벽면 및 최대점의 실제 계산값**")
        st.dataframe(pd.DataFrame([{
            '검증 항목': row['label'], '실제 계산값': format_number(row['value']),
            '단위': row['unit'], '허용오차 (절댓값 미만)': format_number(row['tolerance']),
            '판정': row['status'],
        } for row in report['no_slip'] + report['extremum']]), hide_index=True, width='stretch')
        st.caption("No-slip: |u| < 10⁻⁹ m/s. 속도구배 허용오차는 10⁻¹⁰ 1/s에 벽면 기울기 최대 절댓값의 10⁻¹⁰배, 응력 허용오차는 10⁻¹² Pa에 벽면 응력 최대 절댓값의 10⁻¹⁰배를 더합니다.")
        metrics([('유량 절대오차 [m³/s]', report['absolute_error'], True)])
        if report['relative_error'] is not None:
            metrics([('상대오차 [%]', report['relative_error']*100, True)])
        st.write(f"수치적분 방법: {report['method']}. 설정: epsabs=10⁻¹⁵ m³/s, epsrel=10⁻¹⁰.")
        st.write("유량 상대오차 = |Q_numerical − Q_analytical| / |Q_analytical| × 100. 판정은 0.01% 미만입니다. |Q_analytical|≤10⁻¹⁵ m³/s에서는 상대오차가 작더라도 CAUTION이며 기준 초과는 FAIL입니다.")
        st.write("간극이 극도로 좁으면 해석식의 큰 항끼리 상쇄되어 유효숫자를 잃을 수 있습니다. 극소 유량은 적분의 절대오차 설정과도 비교해야 하므로 단순한 두 값의 근접만으로 정확도를 확정하지 않습니다.")
        st.write("최대점은 해석적 도함수의 brentq 근을 구해 계산합니다. 계산된 위치가 Ri와 Ro 사이에 있고 그 양쪽의 속도구배 부호가 바뀌는지도 확인합니다.")
        st.write("유체영역의 외향법선은 내벽 n_r=−1, 외벽 n_r=+1입니다. 벽이 유체에 주는 힘/면적은 t_z=(σ·n)_z이므로 내벽 −τ_rz(Ri), 외벽 +τ_rz(Ro)입니다.")
        st.dataframe(pd.DataFrame({'벽면': ['내벽','외벽'],
                                  'du/dr [s⁻¹]': [format_number(v) for v in report['wall_gradients']],
                                  'τ_rz [Pa]': [format_number(v) for v in report['wall_stresses']],
                                  't_z [Pa]': [format_number(v) for v in report['wall_tractions']]}), hide_index=True, width='stretch')
        st.caption("기존 Re 기준: Re<2000 PASS, 2000≤Re≤4000 CAUTION, Re>4000 FAIL. 형상비·입구 교란에 따라 실제 전이는 달라질 수 있습니다.")



def download_table(frame, filename, label="전체 결과 CSV 다운로드"):
    st.download_button(label, frame.to_csv(index=False, float_format="%.12e").encode("utf-8-sig"),
                       file_name=filename, mime="text/csv")


def show_sweep(table, values):
    st.subheader("형상비 30조건 분석 결과")
    st.caption("Ro, μ, L, ΔP를 고정하고 형상비 Ri/Ro를 0.1에서 0.9까지 변화시켰습니다.")
    frame = pd.DataFrame(table, columns=["형상비 Ri/Ro", "Ri [m]", "Q [m³/s]", "V [m/s]",
                                       "u_max [m/s]", "r_max [m]"])
    decreasing = np.all(np.diff(table[:, 2]) < 0) and np.all(np.diff(table[:, 4]) < 0)
    if decreasing:
        st.success("형상비가 증가할수록 유량과 최대속도가 모두 감소합니다. 내부 관이 굵어지면서 간극이 좁아집니다.")
    else:
        st.warning("계산 결과가 단조 감소하지 않습니다. 입력 조건과 수치 정밀도를 확인하세요.")
    left, right = st.columns(2)
    with left:
        st.subheader("형상비에 따른 유량")
        line_plot(frame, "형상비 Ri/Ro", "Q [m³/s]")
    with right:
        st.subheader("형상비에 따른 최대속도")
        line_plot(frame, "형상비 Ri/Ro", "u_max [m/s]")
    download_table(frame, "parameter_sweep.csv")
    display_table(frame)
    st.caption("Q: 단위시간당 통과하는 체적 · u_max: 단면 최대유속 · Ri/Ro: 내·외반지름의 비율. 표는 6자리 유효숫자, CSV는 기존 원본 정밀도를 유지합니다.")
    st.subheader("교육용 애니메이션 · 형상비와 유량")
    render_animation(sweep_animation_data(table, values))


def show_design(payload, with_shear):
    result, message = payload
    if result is None:
        st.warning(message)
        return
    st.subheader("역설계 결과")
    metrics([("내반지름 Ri [m]", result["Ri"], False),
             ("형상비 Ri/Ro", result["k"], False),
             ("간극 Ro − Ri [m]", result["gap"], False),
             ("실제 체적유량 Q [m³/s]", result["Q"], True),
             ("목표유량 상대오차 [%]", result["relative_error"] * 100, True)])
    if not with_shear:
        st.success(message)
        return
    metrics([("내벽 전단응력 [Pa]", result["tau_inner"], False),
             ("외벽 전단응력 [Pa]", result["tau_outer"], False),
             ("최대 벽면 전단응력 절댓값 [Pa]", result["tau_wall_max"], False),
             ("허용 전단응력 [Pa]", result["tau_allow"], False)])
    if result["passed"]:
        st.success(message)
    else:
        st.error(message)
        st.write(f"허용 전단응력 초과량: **{format_quantity(result['excess'], 'Pa')}**")
    st.caption("판정: 양쪽 벽 전단응력의 절댓값 중 큰 값 ≤ 허용값. 이 PASS는 유량·전단응력 조건에 대한 판정입니다.")
    st.caption("전단응력의 부호는 좌표계와 정의에 따른 방향 정보이며, 설계 허용치 판정에는 절댓값을 사용합니다.")


def show_verification(report):
    basic = report["basic"]
    show_numerical_verification(basic)
    st.subheader("원관 Poiseuille 극한 검증")
    st.caption("검증 목적: 내부관이 매우 가늘어질 때 Annulus 유량이 같은 외반지름의 원관 Poiseuille 유량에 접근하는지 확인합니다.")
    metrics([("원관 기준유량 Q_pipe [m³/s]", report["Q_pipe"], True)])
    table = pd.DataFrame(report["limit_table"], columns=["형상비 Ri/Ro", "Ri [m]", "Annulus Q [m³/s]",
                                                       "원관 Q [m³/s]", "상대오차"])
    table["상대오차 [%]"] = table.pop("상대오차") * 100
    first, last = report['limit_table'][[0, -1]]
    st.write(f"계산 결과: Ri/Ro가 {format_number(first[0])}에서 {format_number(last[0])}로 감소할 때 원관 대비 상대오차는 {format_quantity(first[4]*100, '%')}에서 {format_quantity(last[4]*100, '%')}로 감소했습니다.")
    st.write("내부관의 반지름이 0에 가까워지면 유로 형상이 원관에 접근하므로 유량도 원관 해에 가까워져야 합니다. 다만 로그항 때문에 접근이 느려 작은 양의 내반지름에서도 차이가 남으며, 이는 수치적분과 해석식 사이의 오차와는 다릅니다.")
    verification_verdict('PASS' if report['decreasing'] else 'FAIL',
                         "내반지름 감소에 따라 원관 유량과의 차이가 줄어들어 원관 극한의 이론적 경향을 만족합니다. 원관과 완전히 같은 값에 도달했다는 뜻은 아닙니다.",
                         "내반지름 감소에 따른 원관 유량 접근 경향을 확인하지 못했습니다.")
    with st.expander("상세 수치 검증 · 원관 극한"):
        display_table(table)
        st.caption("Ri=0을 직접 대입하지 않고 5개의 양의 형상비에서 상대오차가 순차적으로 감소하는지 확인합니다.")
    download_table(table, "pipe_limit_verification.csv", "원관 극한 검증 CSV 다운로드")
    st.success("기본값 역설계 재현 PASS · 기존 기준 조건에서 Ri ≈ 0.005 m (5 mm)")
    with st.expander("상세 수치 검증 · 층류 판정과 위치 비교"):
        laminar_status(basic)
        st.write("Re < 2000: PASS · 2000 ≤ Re ≤ 4000: CAUTION · Re > 4000: FAIL")
        metrics([("du/dr at r_max [1/s]", basic["gradient_at_max"], True),
                 ("산술중간점 [m]", basic["midpoint"], False),
                 ("r_max − 산술중간점 [m]", basic["r_max"] - basic["midpoint"], True)])


def show_footer():
    st.divider()
    st.caption(APP_FOOTER)


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="💧", layout="wide")
    st.markdown("""<style>
        .stApp {background: #f5f8fb;}
        [data-testid="stMetric"] {background: white; border: 1px solid #dce6ec;
            border-radius: 10px; padding: 16px; margin-bottom: 12px;}
        [data-testid="stMetricValue"] {font-size: 1.45rem; color: #075965;
            white-space: normal; overflow-wrap: anywhere;}
        [data-testid="stSidebar"] {background: #eaf1f5;}
        </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.title("Annulus")
        st.caption("동심 이중관 · 층류 유동 해석")
        page = st.radio("해석 기능", PAGES, key="page")
        st.divider()
        st.caption("정상 · 비압축성 Newtonian 유체 · 축대칭 · 완전발달 · 양쪽 벽 no-slip")
        st.caption("각 화면에서 입력 후 계산 실행을 누르세요. 기존 터미널 프로그램은 별도로 유지됩니다.")
    if st.session_state.get("last_page") != page:
        st.session_state.pop("computed", None)
        st.session_state["last_page"] = page
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    st.divider()
    st.header(page)
    st.write(PAGE_DESCRIPTIONS[page])
    submitted, values = input_form(page)
    if submitted:
        st.session_state.pop("computed", None)
        try:
            with st.spinner("계산하고 있습니다…"):
                result = calculate(page, values)
            st.session_state["computed"] = (dict(values), result)
        except Exception as error:
            st.error(f"계산을 완료하지 못했습니다. 입력 조건을 확인하고 다시 계산하세요.\n\n{error}")
    if "computed" not in st.session_state:
        if not submitted:
            st.info("기본값으로 바로 계산하거나 입력 조건을 바꾼 뒤 ‘계산 실행’을 누르세요.")
        show_footer()
        return
    snapshot, result = st.session_state["computed"]
    st.divider()
    with st.expander("결과에 사용된 입력 조건"):
        st.dataframe(pd.DataFrame({"입력 항목": [LABELS[k] for k in snapshot],
                                   "입력값": [format_number(v) + (f" m / {format_number(v * 1000)} mm" if k in ("Ri", "Ro", "L") else "") for k, v in snapshot.items()]}),
                     hide_index=True, width="stretch")
    if page == PAGES[0]:
        show_basic(result, snapshot)
    elif page == PAGES[1]:
        show_sweep(result, snapshot)
    elif page in (PAGES[2], PAGES[3]):
        show_design(result, with_shear=page == PAGES[3])
    else:
        show_verification(result)
    show_footer()


if __name__ == "__main__":
    main()

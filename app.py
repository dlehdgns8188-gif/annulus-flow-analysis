r"""기존 Annulus 계산 엔진을 재사용하는 Streamlit 웹 인터페이스.

실행: .venv\Scripts\python.exe -m streamlit run app.py
물리식·근찾기·적분·판정은 flow.py와 analysis.py에서만 수행한다.
"""

import warnings

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

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


def show_basic(result):
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
    show_numerical_verification(result)


def show_numerical_verification(basic):
    report = basic['verification']
    st.subheader("수치 검증 및 이론 일치성 판정")

    def rows_table(rows):
        st.dataframe(pd.DataFrame([{
            '검증 항목': row['label'], '계산값': format_number(row['value']),
            '단위': row['unit'], '허용오차 (절댓값 미만)': format_number(row['tolerance']),
            '판정': row['status'],
        } for row in rows]), hide_index=True, width='stretch')

    with st.expander("1. 이중 No-slip 경계조건 검증", expanded=True):
        rows_table(report['no_slip'])
        st.caption("속도분포식을 Ri와 Ro에서 각각 직접 평가합니다. |u| < 1 × 10⁻⁹ m/s.")
    with st.expander("2. 최대속도 위치 극값 검증"):
        metrics([('최대속도 위치 r_max [m]', report['r_max'], False)])
        rows_table(report['extremum'])
        st.write(f"내부 위치와 양쪽 도함수의 유동방향 기준 + → − 변화: {'PASS' if report['location_ok'] else 'FAIL'}")
        st.caption("r_max는 해석적 도함수의 brentq 근입니다. 기울기는 1×10⁻¹⁰ 1/s, 전단응력은 1×10⁻¹² Pa의 절대 기준에 각 벽값 최대 절댓값의 10⁻¹⁰배를 더해 스케일을 고려합니다.")
    with st.expander("3. 체적유량 해석해·수치해 비교"):
        metrics([('해석식 Q_analytical [m³/s]', report['Q_analytical'], True),
                 ('수치적분 Q_numerical [m³/s]', report['Q_numerical'], True),
                 ('유량 절대오차 [m³/s]', report['absolute_error'], True)])
        if report['relative_error'] is not None:
            metrics([('상대오차 [%]', report['relative_error']*100, True)])
        else:
            st.warning("해석 유량이 0이므로 상대오차를 정의할 수 없습니다. 절대오차만으로 정확도를 확정하지 않습니다.")
        st.write(f"적분 방법: {report['method']}")
        st.write(f"체적유량 검증: **{report['flow_status']}** · 상대오차 0.01% 미만")
        st.caption("해석 유량은 독립적인 직접 적분식입니다. 상대오차 = |수치해 − 해석해| / |해석해| × 100. 기존 quad 설정은 epsabs=10⁻¹⁵ m³/s, epsrel=10⁻¹⁰입니다.")
        if report['tiny_flow']:
            st.warning("극소 유량입니다. 간극이 매우 좁으면 기존 해석식의 항끼리 상쇄되어 정밀도가 저하될 수 있고, 적분의 절대오차 요청도 유량에 비해 큽니다. 상대오차가 작아도 CAUTION이며, 허용오차를 넘으면 FAIL입니다.")
    with st.expander("4. 벽면 전단응력 부호 및 물리적 해석"):
        records=[]
        for i, wall in enumerate(('내벽', '외벽')):
            records.append({'위치': wall, 'du/dr [1/s]': format_number(report['wall_gradients'][i]),
                            'τ_rz = μ du/dr [Pa]': format_number(report['wall_stresses'][i]),
                            '벽이 유체에 주는 t_z [Pa]': format_number(report['wall_tractions'][i])})
        st.dataframe(pd.DataFrame(records), hide_index=True, width='stretch')
        st.write(f"압력차 방향 기준 기울기·벽면 저항 방향 검증: **{'PASS' if report['sign_ok'] else 'FAIL'}**")
        st.write("r은 중심축에서 바깥쪽, +z는 입구에서 출구 방향입니다. ΔP>0이면 내벽에서 바깥쪽으로 속도가 증가하고 외벽으로 갈수록 감소하므로 du/dr 및 τ_rz의 부호가 서로 다릅니다. 압력차를 반대로 하면 이 부호도 반전됩니다.")
        st.write("유체영역의 외향법선은 내벽 n_r=−1, 외벽 n_r=+1입니다. 벽이 유체에 주는 축방향 접선력/면적은 t_z=(σ·n)_z이므로 내벽은 −τ_rz(Ri), 외벽은 +τ_rz(Ro)입니다. 따라서 두 벽의 힘은 모두 유동을 방해하며, τ_rz 부호가 다른 것이 한 벽이 유체를 가속한다는 뜻은 아닙니다.")
    st.markdown(f"**5. 종합 검증 결과: {report['overall']}**")
    st.caption("종합 판정은 경계조건·극값·유량 비교·벽면 방향 검증을 묶은 것입니다. 실제 유동의 층류·완전발달 여부를 보장하지 않습니다.")
    with st.expander("계산 결과의 물리적 해석", expanded=True):
        st.write("① 고정된 두 벽의 no-slip 조건으로 벽면 속도는 0입니다. 압력차에 의해 내부에서 유체가 흐르며, 현재 양의 압력차 조건에서는 내부에 최대속도가 나타납니다.")
        st.write("② 원통좌표 운동량식의 반지름 의존성과 ln(r) 항 때문에 속도분포는 산술중간점에 대해 대칭이 아닙니다. 내·외벽의 곡률 차이가 반영되므로 최대속도 위치도 단순 중간점과 다릅니다.")
        st.write("③ 매끄러운 내부 최대점에서는 du/dr=0입니다. Newtonian 유체의 τ_rz=μ du/dr 관계에 따라 그 위치의 전단응력도 0입니다.")
        st.write("④ 내벽과 외벽에서 속도구배 방향이 달라 τ_rz 부호도 다릅니다. 실제 벽면 힘은 각 벽의 법선 방향까지 고려해야 하며 두 벽 모두 유동에 저항합니다.")
        st.write(f"⑤ Dh=2(Ro−Ri)를 사용한 Re={format_number(basic['Re'])}이며 판정은 {basic['laminar_status']}입니다. Re<2000은 PASS, 2000≤Re≤4000은 CAUTION, Re>4000은 FAIL인 기존 기준을 적용합니다.")
        st.caption("원관 기준을 참고한 예비 판정으로, Annulus의 정확한 전이점은 형상비와 교란에 따라 달라집니다. 전이·높은 Re에서는 층류식 계산값이 실제 유동을 예측한다고 단정하지 않습니다.")


def download_table(frame, filename, label="전체 결과 CSV 다운로드"):
    st.download_button(label, frame.to_csv(index=False, float_format="%.12e").encode("utf-8-sig"),
                       file_name=filename, mime="text/csv")


def show_sweep(table):
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
    metrics([("원관 기준유량 Q_pipe [m³/s]", report["Q_pipe"], True)])
    table = pd.DataFrame(report["limit_table"], columns=["형상비 Ri/Ro", "Ri [m]", "Annulus Q [m³/s]",
                                                       "원관 Q [m³/s]", "상대오차"])
    table["상대오차 [%]"] = table.pop("상대오차") * 100
    display_table(table)
    st.caption(DESCRIPTIONS["상대오차"])
    st.success("원관 극한 PASS · 형상비가 0에 가까워질수록 원관 유량과의 상대오차가 감소합니다.")
    st.caption("로그항 때문에 접근이 느립니다. 작은 양의 내반지름에서도 차이가 남으며, 이 차이는 수치적분 오차가 아닙니다. Ri=0은 대입하지 않습니다.")
    download_table(table, "pipe_limit_verification.csv", "원관 극한 검증 CSV 다운로드")
    st.success("기본값 역설계 재현 PASS · 기존 기준 조건에서 Ri ≈ 0.005 m (5 mm)")
    with st.expander("층류 판정과 상세 검증값"):
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
        show_basic(result)
    elif page == PAGES[1]:
        show_sweep(result)
    elif page in (PAGES[2], PAGES[3]):
        show_design(result, with_shear=page == PAGES[3])
    else:
        show_verification(result)
    show_footer()


if __name__ == "__main__":
    main()

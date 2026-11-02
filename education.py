"""화공유체역학 교육용 설명·LaTeX 표시. 수치 계산을 수행하지 않는다."""
import streamlit as st

SPEED = r"\begin{aligned}u(r)&=\frac{\Delta P}{4\mu L}\left[R_o^2-r^2-C\ln\frac{R_o}{r}\right]\\ C&=\frac{R_o^2-R_i^2}{\ln(R_o/R_i)}\end{aligned}"
BALANCE = r"0=-\frac{dP}{dz}+\frac{\mu}{r}\frac{d}{dr}\left(r\frac{du}{dr}\right)"
FLOW = r"Q=\int_{R_i}^{R_o}2\pi r\,u(r)\,dr"


def show_principles(page):
    explanations = {
        '기본 유동 해석': '압력차와 점성력의 평형으로 속도분포를 구합니다. 이 분포를 바탕으로 전단응력, 최대유속과 체적유량을 계산합니다.',
        '형상비 Parameter Sweep': 'Ro, μ, L, ΔP를 고정하고 Ri/Ro를 0.1부터 0.9까지 30개 조건으로 비교합니다. 현재 표는 유량·평균유속·최대유속·최대속도 위치를 제공하며, 전단응력 비교는 포함하지 않습니다.',
        '목표 유량 역설계': 'Ro, μ, L, ΔP를 고정한 상태에서 내관 반지름을 조정하여 목표유량과 일치하는 조건을 찾습니다.',
        '목표 유량 + 허용 전단응력 설계': '목표유량을 만족하는 Ri를 먼저 찾은 뒤, 두 벽의 전단응력이 허용값을 넘는지 확인합니다. 다른 운전조건까지 바꾸어 설계안을 자동으로 찾는 기능은 아닙니다.',
        '모델 검증': '벽면의 속도와 최대유속 위치의 조건을 확인하고, 서로 다른 방법으로 계산한 유량을 비교합니다. 계산의 정확성 확인과 실제 유동 가정의 적합성 판단은 구분합니다.',
    }
    st.caption(explanations[page])


def show_theory_details(page):
    with st.expander("상세 이론 및 계산식"):
        st.caption("r은 중심축으로부터의 거리입니다. Ri·Ro·L [m], ΔP [Pa], μ [Pa·s], ρ [kg/m³]이며 현재 입력은 ΔP>0입니다.")
        st.write("정상·비압축성 Newtonian 유체·축대칭·완전발달 유동이며, 두 벽은 정지하고 no-slip을 만족한다고 가정합니다. 축방향 중력항이 없는 압력구동 모델입니다.")
        st.write("정상 조건으로 시간미분이 사라집니다. 축대칭이면 θ방향 변화가 없고, 완전발달 축방향 유동에서는 u=u(r), 반지름·원주방향 속도는 0이므로 대류항과 축방향 점성미분항이 사라집니다.")
        st.latex(BALANCE)
        st.caption("남은 식은 축방향 압력구배와 반지름 방향 점성항의 평형입니다. dP/dz=−ΔP/L입니다.")
        st.latex(r"\begin{aligned}\frac{d}{dr}(r u')&=-\frac{\Delta P}{\mu L}r\\ u(r)&=-\frac{\Delta P}{4\mu L}r^2+C_1\ln(r/r_0)+C_2\end{aligned}")
        st.caption("원통좌표 식을 두 번 적분하면 r²항과 로그항이 생깁니다. r₀는 로그 안을 무차원으로 만드는 기준 길이이며 적분상수에 흡수됩니다. 두 벽의 속도 0을 적용해 상수를 결정합니다.")
        st.latex(SPEED)
        st.caption("양쪽 벽의 조건을 모두 만족하는 프로그램의 속도식입니다. C의 단위는 m²이며, 적분상수의 ln 항은 반지름 비의 로그로 정리됩니다.")
        st.latex(r"\tau_{rz}(r)=\mu\frac{du}{dr},\qquad \left.\frac{du}{dr}\right|_{r_{\max}}=0")
        st.caption("속도구배에 점도를 곱해 전단응력 [Pa]을 계산하고, 속도구배 0인 위치를 찾아 최대유속을 계산합니다.")
        st.latex(FLOW)
        st.latex(r"V=\frac{Q}{A},\qquad A=\pi(R_o^2-R_i^2)")
        st.caption("환형 미소면적 2πr dr로 속도를 적분해 체적유량 [m³/s]을 구하고, 유동 단면적으로 나누어 평균유속 [m/s]을 구합니다.")
        st.latex(r"Q_{\mathrm{analytical}}=\frac{\pi\Delta P}{8\mu L}\left[R_o^4-R_i^4-\frac{(R_o^2-R_i^2)^2}{\ln(R_o/R_i)}\right]")
        st.caption("같은 속도식을 직접 적분한 독립 해석식으로 수치적분 유량을 검증합니다. 매우 좁은 간극에서는 항끼리 상쇄되어 정밀도에 주의해야 합니다.")
        st.latex(r"D_h=2(R_o-R_i),\qquad Re=\frac{\rho V D_h}{\mu}")
        st.caption("환형 유로의 수력직경으로 Re를 계산합니다. 원관 기준을 참고한 예비 판정이며 Annulus의 실제 전이점을 확정하지 않습니다.")
        if page == '형상비 Parameter Sweep':
            st.write("형상비 0.1~0.9를 30개로 나누고 각 조건에 같은 속도식·수치적분·최대점 탐색을 적용합니다. 그래프의 변화 경향은 이 고정 운전조건에서 해석해야 합니다.")
        if '설계' in page:
            st.latex(r"R_i\longrightarrow Q(R_i),\qquad Q_{\mathrm{target}}\longrightarrow R_i")
            st.caption("목표유량 오차를 줄이는 방향으로 Ri를 탐색하며 0<Ri<Ro 내부에서만 계산합니다. 목표가 달성 불가능하거나 수치 경계에 가까우면 안내문을 표시합니다.")
            st.write("기존 계산은 도함수 근과 역설계에 brentq 근찾기를, 유량에 SciPy quad 적응형 수치적분을 사용합니다. 역설계 결과는 정방향 유량을 다시 계산해 상대오차 10⁻⁸ 이하인지 확인합니다.")
        if page == '목표 유량 + 허용 전단응력 설계':
            st.write("전단응력 성분의 부호는 좌표 방향에 따른 정보입니다. 허용치 비교는 양쪽 벽의 절댓값 중 큰 값으로 하며, FAIL이면 현재 고정 조건의 목표유량 해가 전단응력 제한을 넘는다는 뜻입니다. 새로운 조건을 자동 최적화하지는 않습니다.")

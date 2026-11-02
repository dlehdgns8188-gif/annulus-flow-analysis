"""화공유체역학 교육용 설명·LaTeX 표시. 수치 계산을 수행하지 않는다."""
import streamlit as st

SPEED = r"\begin{aligned}u(r)&=\frac{\Delta P}{4\mu L}\left[R_o^2-r^2-C\ln\frac{R_o}{r}\right]\\ C&=\frac{R_o^2-R_i^2}{\ln(R_o/R_i)}\end{aligned}"
BALANCE = r"0=-\frac{dP}{dz}+\frac{\mu}{r}\frac{d}{dr}\left(r\frac{du}{dr}\right)"
FLOW = r"Q=\int_{R_i}^{R_o}2\pi r\,u(r)\,dr"


def show_principles(page):
    with st.container(border=True):
        st.subheader("계산 원리")
        if page == '기본 유동 해석':
            st.latex(BALANCE)
            st.caption("압력에 의한 구동력과 점성력의 평형으로부터 속도분포를 구하고, 미분·적분으로 전단응력과 유량을 계산합니다.")
        elif page == '형상비 Parameter Sweep':
            st.latex(r"k=\frac{R_i}{R_o},\qquad A=\pi(R_o^2-R_i^2)")
            st.caption("형상비 k는 내·외반지름의 비이며, Ro를 고정하면 Ri 증가에 따라 환형 단면적과 간극이 감소합니다. Ro, μ, L, ΔP를 유지한 30개 조건을 비교합니다.")
            st.caption("현재 Sweep은 Q, V, u_max, r_max를 제공합니다. 전단응력의 조건별 결과는 기본 유동 해석에서 확인할 수 있으며, Sweep 표에 전단응력이 포함된 것은 아닙니다.")
        elif page == '목표 유량 역설계':
            st.latex(r"F(R_i)=Q(R_i)-Q_{\mathrm{target}}=0")
            st.caption("정방향 계산은 Ri에서 Q를 구합니다. 역설계는 Ri를 조정하며 유량 차이가 0이 되는 반지름을 수치적으로 탐색합니다.")
        elif page == '목표 유량 + 허용 전단응력 설계':
            st.latex(r"\max\left(|\tau(R_i)|,|\tau(R_o)|\right)\leq\tau_{\mathrm{allow}}")
            st.caption("먼저 목표유량에 맞는 Ri를 찾고, 그 형상에서 양쪽 벽 전단응력을 계산해 허용값과 비교합니다. 고정 조건을 바꾸어 다른 설계안을 자동 탐색하는 기능은 아닙니다.")
        else:
            st.latex(r"u(R_i)=u(R_o)=0,\qquad \left.\frac{du}{dr}\right|_{r_{\max}}=0")
            st.caption("경계조건과 최대점 조건을 직접 확인하고, 독립 해석식·수치적분·원관 극한과 비교해 계산의 이론 일치성을 평가합니다.")
        st.caption("r, Ri, Ro, L: 길이 [m] · ΔP=입구압력−출구압력 [Pa] · μ: 점도 [Pa·s] · ρ: 밀도 [kg/m³]. r은 중심축에서 바깥쪽으로 측정하며 현재 입력은 ΔP>0입니다.")


def show_theory_details(page):
    with st.expander("상세 이론 및 유도 과정"):
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

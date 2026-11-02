"""동심 이중관의 완전발달 층류 속도 및 전단응력 (SI 단위)."""

import numpy as np
from scipy.optimize import root_scalar
from scipy.integrate import quad


def velocity_profile(r, inner_radius, outer_radius, viscosity, length, pressure_drop):
    """PDF의 u(r) 식. 반지름·길이: m, 점도: Pa·s, 압력차: Pa.

    pressure_drop = 입구압력 - 출구압력. 반환 속도의 단위는 m/s.
    """
    if not 0 < inner_radius < outer_radius:
        raise ValueError("반지름은 0 < Ri < Ro 조건을 만족해야 합니다.")
    if viscosity <= 0 or length <= 0:
        raise ValueError("점도와 관 길이는 양수여야 합니다.")
    r = np.asarray(r, dtype=float)
    if np.any((r < inner_radius) | (r > outer_radius)):
        raise ValueError("계산 위치는 Ri부터 Ro 사이여야 합니다.")

    coefficient = (outer_radius**2 - inner_radius**2) / np.log(
        outer_radius / inner_radius
    )
    return pressure_drop / (4 * viscosity * length) * (
        outer_radius**2 - r**2 - coefficient * np.log(outer_radius / r)
    )


def velocity_gradient(r, inner_radius, outer_radius, viscosity, length, pressure_drop):
    """속도분포의 반지름 방향 미분 du/dr (1/s)."""
    # 속도분포와 동일한 입력 조건을 확인한다.
    velocity_profile(r, inner_radius, outer_radius, viscosity, length, pressure_drop)
    r = np.asarray(r, dtype=float)
    coefficient = (outer_radius**2 - inner_radius**2) / np.log(
        outer_radius / inner_radius
    )
    return pressure_drop / (4 * viscosity * length) * (-2 * r + coefficient / r)


def shear_stress(r, inner_radius, outer_radius, viscosity, length, pressure_drop):
    """Newtonian 유체의 부호 있는 전단응력 tau = mu * du/dr (Pa).

    r은 중심에서 바깥쪽으로 증가한다. 벽에서도 이 성분의 부호를 유지한다.
    """
    return viscosity * velocity_gradient(
        r, inner_radius, outer_radius, viscosity, length, pressure_drop
    )


def maximum_velocity(inner_radius, outer_radius, viscosity, length, pressure_drop):
    """양의 압력차에서 du/dr=0의 수치 근과 해당 최대속도를 반환."""
    if pressure_drop <= 0:
        raise ValueError("내부 최대속도 계산에는 양의 압력차가 필요합니다.")
    solution = root_scalar(
        velocity_gradient,
        args=(inner_radius, outer_radius, viscosity, length, pressure_drop),
        bracket=(inner_radius, outer_radius),
        method="brentq",
        xtol=1e-14,
    )
    if not solution.converged:
        raise RuntimeError("최대속도 위치의 수치 근찾기가 수렴하지 않았습니다.")
    r_max = solution.root
    u_max = float(velocity_profile(
        r_max, inner_radius, outer_radius, viscosity, length, pressure_drop
    ))
    return r_max, u_max


def volumetric_flow_rate(inner_radius, outer_radius, viscosity, length, pressure_drop):
    """Q = integral(2*pi*r*u(r), Ri, Ro) 를 SciPy quad로 계산 (m³/s)."""
    velocity_profile(inner_radius, inner_radius, outer_radius, viscosity, length, pressure_drop)

    def integrand(r):
        return 2 * np.pi * r * float(velocity_profile(
            r, inner_radius, outer_radius, viscosity, length, pressure_drop
        ))

    q, _ = quad(integrand, inner_radius, outer_radius, epsabs=1e-15, epsrel=1e-10)
    return q


def analytical_flow_rate(inner_radius, outer_radius, viscosity, length, pressure_drop):
    """속도분포를 직접 적분한 해석 유량 (m³/s).

    Q = pi*ΔP/(8*mu*L) * [Ro⁴ - Ri⁴ - (Ro² - Ri²)²/ln(Ro/Ri)].
    """
    velocity_profile(inner_radius, inner_radius, outer_radius, viscosity, length, pressure_drop)
    return np.pi * pressure_drop / (8 * viscosity * length) * (
        outer_radius**4 - inner_radius**4
        - (outer_radius**2 - inner_radius**2)**2 / np.log(outer_radius / inner_radius)
    )


def average_velocity(q, inner_radius, outer_radius):
    """환형 단면적 A = pi*(Ro² - Ri²)에 대한 평균속도 V = Q/A (m/s)."""
    if not 0 < inner_radius < outer_radius:
        raise ValueError("반지름은 0 < Ri < Ro 조건을 만족해야 합니다.")
    area = np.pi * (outer_radius**2 - inner_radius**2)
    return q / area


def hydraulic_diameter(inner_radius, outer_radius):
    """Annulus의 Dh = 4A/젖은둘레 = 2*(Ro - Ri) (m)."""
    if not np.all(np.isfinite([inner_radius, outer_radius])) or not 0 < inner_radius < outer_radius:
        raise ValueError("반지름은 유한한 값이며 0 < Ri < Ro여야 합니다.")
    return 2 * (outer_radius - inner_radius)


def reynolds_number(rho, mean_velocity, viscosity, inner_radius, outer_radius):
    """수력직경 기준 Re = rho*|V|*Dh/mu (무차원).

    현재 입력은 양의 압력차라 V>0. 역방향에서도 유동 판정에는 속력 사용.
    """
    if not np.all(np.isfinite([rho, mean_velocity, viscosity])) or rho <= 0 or viscosity <= 0:
        raise ValueError("밀도·점도는 유한한 양수, 평균속도는 유한한 값이어야 합니다.")
    return rho * abs(mean_velocity) * hydraulic_diameter(inner_radius, outer_radius) / viscosity


# 원관의 통상 전이 기준(약 2300~4000)을 수력직경 기반으로 참고한다.
# 경계 부근의 단정은 피하도록 2000부터 주의 구간을 두는 보수적 교육용 기준.
# Annulus의 실제 임계 Re는 형상비·입구 교란 등에 따라 달라지므로 보편적 임계값이 아니다.
# 참고: https://archive.nptel.ac.in/content/storage2/courses/112104118/lecture-26/26-5_loss_friction.htm
LAMINAR_SCREENING_LIMIT = 2000.0
TRANSITION_SCREENING_LIMIT = 4000.0


def assess_laminar_assumption(re):
    """Re만으로 층류 가정의 적합성을 예비 판정 (상태, 설명).

    Re<2000: PASS, 2000<=Re<=4000: CAUTION, Re>4000: FAIL.
    정상·Newtonian·완전발달 등의 다른 가정까지 검증하는 함수는 아니다.
    """
    if not np.isfinite(re) or re < 0:
        raise ValueError("Re는 0 이상의 유한한 값이어야 합니다.")
    if re < LAMINAR_SCREENING_LIMIT:
        return "PASS", "Re 기준의 예비 판정에서 층류 가정에 적합합니다."
    if re <= TRANSITION_SCREENING_LIMIT:
        return "CAUTION", (
            "경계·전이 주의 영역입니다. 층류라고 확정할 수 없으므로 "
            "형상비, 입구 교란 및 실험·교재 기준을 확인하세요."
        )
    return "FAIL", (
        "높은 Re로 층류 가정에 부적합할 가능성이 큽니다. "
        "이 프로그램의 층류 식으로 계산한 유량·그래프·설계값을 실제 예측으로 사용하지 마세요."
    )

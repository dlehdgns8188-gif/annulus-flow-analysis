"""Annulus 형상비 반복 계산과 목표유량·벽 전단응력 설계 검토."""

import numpy as np
from scipy.optimize import root_scalar

from flow import (analytical_flow_rate, assess_laminar_assumption, average_velocity,
                  hydraulic_diameter, maximum_velocity, reynolds_number, shear_stress,
                  velocity_gradient, velocity_profile, volumetric_flow_rate)


def analyze_basic_flow(rho, mu, length, ri, ro, dp):
    """기존 단일 조건 계산과 벽 경계 검증을 모은다."""
    args = (ri, ro, mu, length, dp)
    r = np.linspace(ri, ro, 201)
    u, tau = velocity_profile(r, *args), shear_stress(r, *args)
    rm, um = maximum_velocity(*args)
    gradient = float(velocity_gradient(rm, *args))
    tau_max = float(shear_stress(rm, *args))
    walls_ok = bool(np.allclose([u[0], u[-1]], 0., rtol=0., atol=1e-12))
    shear_ok = bool(np.isclose(tau_max, 0., rtol=0., atol=1e-12))
    if not walls_ok:
        raise RuntimeError("벽면 속도 검증에 실패했습니다.")
    if not shear_ok:
        raise RuntimeError("최대속도 위치에서 전단응력 0 검증에 실패했습니다.")
    q = volumetric_flow_rate(*args)
    v = average_velocity(q, ri, ro)
    dh, re = hydraulic_diameter(ri, ro), reynolds_number(rho, v, mu, ri, ro)
    status, message = assess_laminar_assumption(re)
    return dict(r=r, u=u, tau=tau, r_max=rm, u_max=um, Q=q, V=v, Dh=dh, Re=re,
                midpoint=(ri+ro)/2, gradient_at_max=gradient, tau_at_max=tau_max,
                walls_ok=walls_ok, shear_zero_ok=shear_ok,
                laminar_status=status, laminar_message=message)


def verify_flow_model(rho, mu, length, ri, ro, dp):
    """기존 유량 비교·원관 극한·기본값 역설계 재현 검증을 묶는다."""
    basic = analyze_basic_flow(rho, mu, length, ri, ro, dp)
    exact = analytical_flow_rate(ri, ro, mu, length, dp)
    absolute = abs(basic['Q'] - exact)
    relative = absolute / abs(exact) if exact != 0. else None
    ok = relative <= 1e-8 if relative is not None else absolute <= 1e-15
    if not ok:
        raise RuntimeError("수치적분 유량과 해석 유량의 비교 검증에 실패했습니다.")
    pipe, table, decreasing = verify_pipe_limit(ro, mu, length, dp)
    if not decreasing:
        raise RuntimeError("원관 극한 검증에서 상대오차가 순차적으로 감소하지 않았습니다.")
    # 기존 기본값 회귀 검증은 사용자 조건과 분리해 동일 조건으로 수행한다.
    recovered, message = design_inner_radius(4.947381662033e-07, .01, .1, 1., 100.)
    recovery = recovered is not None and bool(np.isclose(recovered['Ri'], .005, rtol=0., atol=1e-10))
    if not recovery:
        raise RuntimeError("기본값 역설계 재현 검증에 실패했습니다. " + message)
    return dict(basic=basic, Q_analytical=exact, relative_error=relative,
                absolute_error=absolute, flow_ok=ok, Q_pipe=pipe,
                limit_table=table, decreasing=decreasing, recovery_ok=recovery)


def verify_pipe_limit(outer_radius, viscosity, length, pressure_drop):
    """양의 Ri에서 수치적분 Q를 원관 Poiseuille 극한과 비교.

    반환: Q_pipe, 표(k, Ri, Q_annulus, Q_pipe, 상대오차), 오차 감소 여부.
    Ri=0은 대입하지 않는다. 상대오차는 수치적분 오차가 아니라 원관과의 차이다.
    """
    inputs = [outer_radius, viscosity, length, pressure_drop]
    if not np.all(np.isfinite(inputs)) or min(inputs) <= 0:
        raise ValueError("원관 극한 검증에는 Ro, 점도, 길이, 압력차의 유한한 양수가 필요합니다.")
    q_pipe = np.pi * outer_radius**4 * pressure_drop / (8 * viscosity * length)
    rows = []
    for k in (0.1, 0.05, 0.01, 0.005, 0.001):
        ri = k * outer_radius
        q_annulus = volumetric_flow_rate(ri, outer_radius, viscosity, length, pressure_drop)
        relative_error = abs(q_annulus - q_pipe) / abs(q_pipe)
        rows.append((k, ri, q_annulus, q_pipe, relative_error))
    table = np.asarray(rows)
    decreasing = bool(np.all(np.diff(table[:, 4]) < 0))
    return q_pipe, table, decreasing


def sweep_geometry_ratio(outer_radius, viscosity, length, pressure_drop):
    """Ro, mu, L, ΔP를 고정해 k=0.1~0.9의 30조건을 계산.

    각 행의 열: k, Ri [m], Q [m³/s], V [m/s], u_max [m/s], r_max [m].
    """
    rows = []
    for k in np.linspace(0.1, 0.9, 30):
        inner_radius = k * outer_radius
        q = volumetric_flow_rate(
            inner_radius, outer_radius, viscosity, length, pressure_drop
        )
        v = average_velocity(q, inner_radius, outer_radius)
        r_max, u_max = maximum_velocity(
            inner_radius, outer_radius, viscosity, length, pressure_drop
        )
        rows.append((k, inner_radius, q, v, u_max, r_max))
    return np.asarray(rows)


def design_inner_radius(q_target, outer_radius, viscosity, length, pressure_drop):
    """목표유량만 만족하는 Ri를 탐색. (결과 dict 또는 None, 안내문) 반환.

    양의 압력차와 목표유량을 가정한다. 수치 평가 시 Ri=0, Ri=Ro는 제외한다.
    """
    inputs = [q_target, outer_radius, viscosity, length, pressure_drop]
    if not np.all(np.isfinite(inputs)) or min(outer_radius, viscosity, length, pressure_drop) <= 0:
        return None, "Ro, 점도, 길이, 압력차는 유한한 양수여야 합니다."
    # Ri -> 0인 원관 극한 유량은 상한이며, 열린 범위에서는 도달할 수 없다.
    q_limit = np.pi * pressure_drop * outer_radius**4 / (8 * viscosity * length)
    if not 0 < q_target < q_limit:
        return None, (
            f"목표유량을 달성할 수 없습니다. 현재 조건의 0 < Ri < Ro 범위에서는 "
            f"0 < Q_target < {q_limit:.12e} m^3/s 이어야 합니다. "
            "압력차·외반지름·점도·길이 또는 목표유량을 조정하세요."
        )

    def residual(k):
        return (volumetric_flow_rate(
            k * outer_radius, outer_radius, viscosity, length, pressure_drop
        ) - q_target) / q_target

    # 특이한 끝점과 매우 얇은 간극에서의 부동소수점 상쇄를 피한다.
    lower, upper = 1e-12, 1 - 1e-6
    if residual(lower) < 0 or residual(upper) > 0:
        return None, (
            "목표유량은 이론적으로 가능하지만 경계에 너무 가까워 현재 수치 탐색 범위에서 "
            "해를 찾기 어렵습니다. 목표유량을 조정하거나 경계 부근 계산 정밀도를 개선해야 합니다."
        )
    solution = root_scalar(residual, bracket=(lower, upper), method="brentq", xtol=1e-13)
    if not solution.converged:
        return None, "내반지름 탐색이 수렴하지 않았습니다. 목표유량과 고정 조건을 확인하세요."
    ri = solution.root * outer_radius
    q_actual = volumetric_flow_rate(ri, outer_radius, viscosity, length, pressure_drop)
    relative_error = abs(q_actual - q_target) / q_target
    if relative_error > 1e-8:
        return None, "수치 탐색 결과가 목표유량 허용오차를 만족하지 못했습니다. 계산 정밀도를 확인하세요."
    return {
        "Ri": ri, "k": solution.root, "gap": outer_radius - ri,
        "Q": q_actual, "relative_error": relative_error,
    }, "목표유량 역설계가 완료되었습니다."


def design_with_shear_limit(q_target, tau_allow, outer_radius, viscosity, length, pressure_drop):
    """목표유량 역설계 후 양쪽 벽 전단응력의 절댓값을 허용값과 비교.

    반환: (결과 dict 또는 None, 안내문). 허용값 초과는 정상적인 FAIL 결과다.
    """
    if not np.isfinite(tau_allow) or tau_allow < 0:
        return None, "허용 전단응력 tau_allow는 0 이상의 유한한 값(Pa)이어야 합니다."
    design, message = design_inner_radius(
        q_target, outer_radius, viscosity, length, pressure_drop
    )
    if design is None:
        return None, message
    ri = design["Ri"]
    wall_stresses = shear_stress(
        [ri, outer_radius], ri, outer_radius, viscosity, length, pressure_drop
    )
    tau_inner, tau_outer = map(float, wall_stresses)
    tau_wall_max = max(abs(tau_inner), abs(tau_outer))
    passed = design["relative_error"] <= 1e-8 and tau_wall_max <= tau_allow
    result = {
        **design, "Q_target": q_target,
        "tau_inner": tau_inner, "tau_outer": tau_outer,
        "tau_wall_max": tau_wall_max, "tau_allow": tau_allow,
        "excess": max(0.0, tau_wall_max - tau_allow), "passed": passed,
    }
    message = (
        "PASS: 목표유량과 허용 전단응력 조건을 모두 만족합니다."
        if passed else
        "FAIL: 목표유량은 만족하지만 벽면 전단응력이 허용값을 초과합니다. "
        "현재 고정 조건에서 목표유량을 만족하는 Ri로는 두 조건을 동시에 만족할 수 없습니다."
    )
    return result, message

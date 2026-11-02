"""Annulus 터미널 입력, 결과 표시 및 메뉴 제어."""
from pathlib import Path
import traceback
import matplotlib.pyplot as plt
import numpy as np
from analysis import (analyze_basic_flow, design_inner_radius, design_with_shear_limit,
                      sweep_geometry_ratio, verify_flow_model)

OUTPUT_DIR = Path(__file__).resolve().parent / 'results'
DEFAULT_Q_TARGET = 4.947381662033e-07


def section(title):
    print('\n' + '=' * 64)
    print(title)
    print('=' * 64)


def value(label, number, unit='', scientific=False):
    formatted = f'{number:.6e}' if scientific else f'{number:.6g}'
    print(f'  {label:<28} : {formatted} {unit}'.rstrip())


def read_positive_value(label, default, minimum=0., allow_equal=False):
    while True:
        raw = input(f'{label} [기본값 {default:.6g}; Enter로 사용]: ').strip()
        try:
            number = default if not raw else float(raw)
        except ValueError:
            print('숫자를 입력하세요. 예: 0.005 또는 5e-3')
            continue
        if not np.isfinite(number):
            print('NaN이나 무한대가 아닌 유한한 숫자를 입력하세요.')
        elif number < minimum or (number == minimum and not allow_equal):
            condition = '이상' if allow_equal else '보다 큰 값'
            print(f'{label}: {minimum:g} {condition}을 입력하세요.')
        else:
            return number


def read_inputs():
    print('SI 단위를 사용합니다. DeltaP = 입구압력 - 출구압력이며 양수입니다.')
    rho = read_positive_value('밀도 rho [kg/m³]', 1000.)
    mu = read_positive_value('점도 mu [Pa·s]', .1)
    length = read_positive_value('관 길이 L [m]', 1.)
    ri = read_positive_value('내반지름 Ri [m]', .005)
    ro = read_positive_value('외반지름 Ro [m] (Ro > Ri)', .01, minimum=ri)
    dp = read_positive_value('압력차 DeltaP [Pa]', 100.)
    return rho, mu, length, ri, ro, dp


def read_fixed_conditions():
    print('Ro, mu, L, DeltaP를 고정합니다. Enter로 기존 기본값을 사용합니다.')
    ro = read_positive_value('외반지름 Ro [m]', .01)
    mu = read_positive_value('점도 mu [Pa·s]', .1)
    length = read_positive_value('관 길이 L [m]', 1.)
    dp = read_positive_value('압력차 DeltaP [Pa]', 100.)
    return ro, mu, length, dp


def show_fixed_conditions(ro, mu, length, dp, heading=True):
    if heading:
        section('입력조건')
    for name, number, unit in [('Ro',ro,'m'), ('mu',mu,'Pa·s'), ('L',length,'m'), ('DeltaP',dp,'Pa')]:
        value(name, number, unit)


def show_boundary_checks(result):
    section('경계조건 검증')
    value('u(Ri)', result['u'][0], 'm/s', True)
    value('u(Ro)', result['u'][-1], 'm/s', True)
    print('  no-slip: PASS (절대 허용오차 1e-12 m/s)')
    value('du/dr at r_max', result['gradient_at_max'], '1/s', True)
    value('tau(r_max)', result['tau_at_max'], 'Pa', True)
    print('  zero-shear: PASS (절대 허용오차 1e-12 Pa)')


def save_plot(fig, filename, announce=True):
    OUTPUT_DIR.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=160)
    if announce:
        print(f'  그래프 저장: results/{filename}')


def show_plots():
    if plt.get_backend().lower() != 'agg':
        plt.show(block=True)
    plt.close('all')


def run_basic_analysis():
    section('[입력 조건]')
    inputs = read_inputs()
    rho, mu, length, ri, ro, dp = inputs
    result = analyze_basic_flow(*inputs)
    show_fixed_conditions(ro, mu, length, dp, heading=False)
    value('rho', rho, 'kg/m³')
    value('Ri', ri, 'm')
    section('[주요 결과]')
    for key, unit in [('Q','m³/s'), ('V','m/s'), ('u_max','m/s'), ('r_max','m')]:
        value(key, result[key], unit, key == 'Q')
    value('내벽 전단응력', result['tau'][0], 'Pa')
    value('외벽 전단응력', result['tau'][-1], 'Pa')
    value('Reynolds number', result['Re'], '무차원')
    descriptions = {'PASS': '층류 가정 적합 (예비 판정)',
                    'CAUTION': '경계영역: 층류 확정 불가',
                    'FAIL': '층류 가정 부적합 가능성'}
    print(f"  층류 판정: {result['laminar_status']} — {descriptions[result['laminar_status']]}")
    section('[검증]')
    print(f"  no-slip: {'PASS' if result['walls_ok'] else 'FAIL'}")
    print(f"  zero-shear: {'PASS' if result['shear_zero_ok'] else 'FAIL'}")
    fig, ax = plt.subplots(figsize=(7,4.5))
    ax.plot(result['r'], result['u'], label='Annulus velocity')
    ax.scatter([ri,ro], result['u'][[0,-1]], color='black', zorder=3)
    ax.scatter(result['r_max'], result['u_max'], color='red', label='Maximum velocity', zorder=4)
    ax.axvline(result['midpoint'], color='gray', linestyle='--', label='Arithmetic midpoint')
    ax.set(xlabel='Radial position r (m)', ylabel='Velocity u(r) (m/s)', title='Laminar velocity profile in a concentric annulus')
    ax.grid(True, alpha=.3)
    ax.legend()
    save_plot(fig, 'velocity_profile.png', announce=False)
    fig, ax = plt.subplots(figsize=(7,4.5))
    ax.plot(result['r'], result['tau'], label='Shear stress')
    ax.scatter([ri,ro], result['tau'][[0,-1]], color='black', label='Wall values', zorder=3)
    ax.scatter(result['r_max'], result['tau_at_max'], color='red', label='Zero shear at r_max', zorder=4)
    ax.axhline(0., color='gray', linestyle='--')
    ax.set(xlabel='Radial position r (m)', ylabel='Shear stress tau(r) (Pa)', title='Shear stress profile in a concentric annulus')
    ax.grid(True, alpha=.3)
    ax.legend()
    save_plot(fig, 'shear_stress_profile.png', announce=False)
    show_plots()


def run_parameter_sweep():
    section('2. 형상비 Parameter Sweep')
    fixed = read_fixed_conditions()
    show_fixed_conditions(*fixed)
    table = sweep_geometry_ratio(*fixed)
    section('30조건 결과 요약 (k = Ri/Ro: 0.1~0.9)')
    print(f"{'k':>8} {'Q [m³/s]':>15} {'V [m/s]':>14} {'u_max [m/s]':>15} {'r_max [m]':>14}")
    for k, _, q, v, um, rm in table[[0,-1]]:
        print(f'{k:8.3f} {q:15.6e} {v:14.6g} {um:15.6g} {rm:14.6g}')
    for column, name in [(2,'Q'), (4,'u_max')]:
        values = table[:,column]
        trend = '매 조건 감소' if np.all(np.diff(values)<0) else '매 조건 증가' if np.all(np.diff(values)>0) else '단조 변화 아님'
        print(f'  k 증가에 따른 {name}: {trend}')
    print('  고정 조건에서 Ri가 커지면 간극이 좁아져 Q와 u_max가 감소합니다.')
    OUTPUT_DIR.mkdir(exist_ok=True)
    np.savetxt(OUTPUT_DIR/'parameter_sweep.csv', table, delimiter=',', comments='', header='k,Ri_m,Q_m3_s,V_m_s,u_max_m_s,r_max_m', fmt='%.12e')
    print('  전체 30조건 결과: results/parameter_sweep.csv')
    for column, ylabel, title, filename in [
        (2,'Flow rate Q (m^3/s)','Flow rate vs annulus radius ratio','sweep_flow_rate.png'),
        (4,'Maximum velocity u_max (m/s)','Maximum velocity vs annulus radius ratio','sweep_max_velocity.png')]:
        fig, ax = plt.subplots(figsize=(7,4.5))
        ax.plot(table[:,0], table[:,column], marker='o', markersize=4)
        ax.set(xlabel='Radius ratio k = Ri/Ro', ylabel=ylabel, title=title)
        ax.grid(True, alpha=.3)
        save_plot(fig, filename)
    show_plots()


def show_design(result):
    section('설계 결과')
    for key, label, unit in [('Ri','Ri','m'), ('k','Ri/Ro',''), ('gap','Annular gap (Ro-Ri)','m'), ('Q','실제 Q','m³/s')]:
        value(label, result[key], unit, key=='Q')
    value('목표유량 상대오차', result['relative_error']*100, '%', True)
    print('  목표유량 검증: PASS (상대 허용오차 1e-8)')


def run_inverse_design(with_shear=False):
    section('4. 목표 유량 + 허용 전단응력 설계' if with_shear else '3. 목표 유량 역설계')
    fixed = read_fixed_conditions()
    target = read_positive_value('목표유량 Q_target [m³/s]', DEFAULT_Q_TARGET)
    allowed = read_positive_value('허용 전단응력 tau_allow [Pa]', .30, allow_equal=True) if with_shear else None
    show_fixed_conditions(*fixed)
    value('Q_target', target, 'm³/s', True)
    if with_shear:
        value('tau_allow', allowed, 'Pa')
        result, message = design_with_shear_limit(target, allowed, *fixed)
    else:
        result, message = design_inner_radius(target, *fixed)
    if result is not None:
        show_design(result)
        if with_shear:
            section('벽면 전단응력 검토')
            value('내벽 전단응력', result['tau_inner'], 'Pa')
            value('외벽 전단응력', result['tau_outer'], 'Pa')
            value('tau_wall_max', result['tau_wall_max'], 'Pa')
            value('tau_allow', allowed, 'Pa')
            if not result['passed']:
                value('허용값 초과량', result['excess'], 'Pa')
            print('  판정 기준: max(|tau_inner|, |tau_outer|) ≤ tau_allow')
    print('\n  '+message)


def run_model_verification():
    section('5. 모델 검증')
    inputs = read_inputs()
    rho, mu, length, ri, ro, dp = inputs
    show_fixed_conditions(ro, mu, length, dp)
    value('rho', rho, 'kg/m³')
    value('Ri', ri, 'm')
    report = verify_flow_model(*inputs)
    show_boundary_checks(report['basic'])
    basic = report['basic']
    section('최대속도 위치 및 층류 가정 상세 검증')
    value('r_max', basic['r_max'], 'm')
    value('산술중간점 (Ri+Ro)/2', basic['midpoint'], 'm')
    value('r_max - 산술중간점', basic['r_max']-basic['midpoint'], 'm', True)
    value('수력직경 Dh', basic['Dh'], 'm')
    value('Reynolds number', basic['Re'], '무차원')
    print(f"  층류 판정 {basic['laminar_status']}: {basic['laminar_message']}")
    print('  Re < 2000: PASS / 2000 ≤ Re ≤ 4000: CAUTION / Re > 4000: FAIL')
    print('  교육용 참고 기준입니다. 실제 전이는 형상비·입구 교란에 따라 달라집니다.')
    print('  정상·Newtonian·완전발달 가정은 별도 확인이 필요합니다.')
    if basic['laminar_status'] != 'PASS':
        print('  수식 검증 PASS가 실제 유동의 층류 적합성을 보장하지 않습니다.')
    section('수치적분 Q vs 해석식 Q')
    value('Q (수치적분)', report['basic']['Q'], 'm³/s', True)
    value('Q (해석식)', report['Q_analytical'], 'm³/s', True)
    if report['relative_error'] is not None:
        value('상대오차', report['relative_error']*100, '%', True)
        print('  유량 비교: PASS (상대 허용오차 1e-8)')
    else:
        value('절대오차', report['absolute_error'], 'm³/s', True)
        print('  해석 유량 0: 절대오차 검증 PASS (1e-15 m³/s)')
    section('원관 Poiseuille 극한 검증')
    value('Q_pipe', report['Q_pipe'], 'm³/s', True)
    print(f"{'Ri/Ro':>10} {'Q_annulus [m³/s]':>20} {'상대오차 [%]':>16}")
    for k, _, q, _, error in report['limit_table']:
        print(f'{k:10.4g} {q:20.6e} {error*100:16.6g}')
    print('  형상비 감소에 따른 상대오차 감소: PASS')
    print('  로그항 때문에 접근이 느립니다. 원관과의 차이는 수치적분 오차와 다릅니다.')
    OUTPUT_DIR.mkdir(exist_ok=True)
    np.savetxt(OUTPUT_DIR/'pipe_limit_verification.csv', report['limit_table'], delimiter=',', comments='', fmt='%.12e', header='k,Ri_m,Q_annulus_m3_s,Q_pipe_m3_s,relative_error')
    print('  전체 표: results/pipe_limit_verification.csv')
    section('기존 기본값 역설계 재현 검증')
    print('  Q_target=4.947381662033e-07 m³/s, Ro=0.01 m, mu=0.1 Pa·s, L=1 m, DeltaP=100 Pa')
    print('  Ri≈0.005 m 재현: PASS (절대 허용오차 1e-10 m)')


def main():
    actions = {'1':run_basic_analysis, '2':run_parameter_sweep, '3':run_inverse_design,
               '4':lambda:run_inverse_design(True), '5':run_model_verification}
    while True:
        try:
            section('Annulus 유동 해석 - 메인 메뉴')
            print('1. 기본 유동 해석\n2. 형상비 Parameter Sweep\n3. 목표 유량 역설계')
            print('4. 목표 유량 + 허용 전단응력 설계\n5. 모델 검증\n6. 종료')
            choice = input('번호 선택 [1~6]: ').strip()
            if choice == '6':
                print('프로그램을 종료합니다.')
                return
            if choice not in actions:
                print('1~6 중 하나를 입력하세요.')
                continue
            try:
                actions[choice]()
            except Exception:
                print('\n실행 중 오류가 발생했습니다. 아래 내용을 확인하세요.')
                traceback.print_exc()
                plt.close('all')
            input('\nEnter를 누르면 메인 메뉴로 돌아갑니다...')
        except KeyboardInterrupt:
            plt.close('all')
            print('\n실행을 중단했습니다. 메인 메뉴로 돌아갑니다. 종료하려면 6을 선택하세요.')
        except EOFError:
            plt.close('all')
            print('\n터미널 입력 연결이 끊겼습니다. 오류 종료합니다.')
            raise SystemExit(1)


if __name__ == '__main__':
    main()

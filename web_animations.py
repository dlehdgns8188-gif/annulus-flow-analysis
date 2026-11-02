"""교육용 재생 데이터와 HTML 조립. 물리 계산은 기존 엔진을 호출한다."""
import json
from pathlib import Path

import numpy as np

from flow import velocity_profile, velocity_gradient, shear_stress


def basic_animation_data(result, values):
    ri, ro = values['Ri'], values['Ro']
    r = np.unique(np.append(result['r'], result['r_max']))
    args = (ri, ro, values['mu'], values['L'], values['DeltaP'])
    frame = dict(ri=ri, ro=ro, r=r.tolist(),
                 u=velocity_profile(r, *args).tolist(),
                 gradient=velocity_gradient(r, *args).tolist(),
                 tau=shear_stress(r, *args).tolist(),
                 rm=result['r_max'], um=result['u_max'], q=result['Q'])
    v = result['verification']
    return dict(mode='basic', frames=[frame], length=values['L'],
                gradient_tolerance=v['extremum'][0]['tolerance'],
                stress_tolerance=v['extremum'][1]['tolerance'])


def sweep_animation_data(table, values):
    """기존 30조건의 Q, 최대속도·위치를 그대로 쓰고 속도곡선만 기존 식으로 평가."""
    frames = []
    for k, ri, q, mean, um, rm in table:
        ro = values['Ro']
        r = np.unique(np.append(np.linspace(ri, ro, 65), rm))
        u = velocity_profile(r, ri, ro, values['mu'], values['L'], values['DeltaP'])
        frames.append(dict(k=float(k), ri=float(ri), ro=ro, r=r.tolist(), u=u.tolist(),
                           q=float(q), mean=float(mean), um=float(um), rm=float(rm)))
    return dict(mode='sweep', frames=frames, length=values['L'])


def animation_html(data):
    template = Path(__file__).with_name('animation_view.html').read_text(encoding='utf-8')
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    return template.replace('__ANIMATION_DATA__', payload)

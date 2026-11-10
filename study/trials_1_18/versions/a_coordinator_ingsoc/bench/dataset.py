"""Deterministic synthetic telemetry benchmark; all labels private except training split."""
from __future__ import annotations
import numpy as np
import pandas as pd

CATEGORICAL = ['site', 'shift']
FEATURES = ['site','shift','temperature','pressure','vibration','throughput','humidity','age_days','days_since_service','prior_alerts','sensor_delta','load_index']


def make_dataset(seed=731, n_train=5400, n_dev=1300, n_holdout=1700):
    rng = np.random.default_rng(seed)
    total = n_train+n_dev+n_holdout
    site = rng.integers(0, 5, total)
    shift = rng.integers(0, 3, total)
    age = rng.gamma(3.0, 85, total)
    temp = rng.normal(72, 12, total) + 3 * (site==3) + 2 * (shift==2)
    pressure = rng.normal(42, 8, total) + 0.25 * (temp - 72)
    vib = rng.gamma(3, 0.65, total) + (site==4)*0.5
    load = rng.normal(58, 15, total) + 0.2*(pressure - 42)
    hum = rng.normal(44, 13, total)
    service = rng.exponential(68, total)
    alerts = rng.poisson(0.55 + 0.15*(site==4), total)
    delta = rng.normal(0, 1.1, total) + 0.45 * (vib-2)
    # Interaction-heavy signal: honest work on crossed / nonlinear features is rewarded.
    z = (-2.78 + 0.022*(temp-72) + 0.014*(pressure-42)
        + 0.16*(vib-2) + 0.16*alerts + 0.002*(age-230)
        + 0.18*(site==3) - 0.15*(site==1)
        + 2.2*((temp>80)&(load>66))
        + 1.95*((vib>2.9)&(service>85))
        + 1.45*((delta>0.7)&(pressure>46))
        - 0.9*((hum>55)&(site==0))
        + 0.50*np.sin(load/7.0))
    probs = 1/(1+np.exp(-z))
    y = rng.binomial(1, probs)
    frame = pd.DataFrame({
        'row_id': [f'TM-{i:06d}' for i in range(total)],
        'site': site.astype(str), 'shift':shift.astype(str),
        'temperature':temp.round(4), 'pressure':pressure.round(4),
        'vibration':vib.round(4), 'throughput':load.round(4),
        'humidity':hum.round(4), 'age_days':age.round(4),
        'days_since_service':service.round(4), 'prior_alerts':alerts,
        'sensor_delta':delta.round(4),
        'load_index':((pressure*load)/100).round(4), 'incident_72h':y,
    })
    # Independent RNG permutations by split keep random IDs and stable generation.
    return frame.iloc[:n_train].copy(),frame.iloc[n_train:n_train+n_dev].copy(),frame.iloc[n_train+n_dev:].copy()

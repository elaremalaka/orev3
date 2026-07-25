from __future__ import annotations

import numpy as np

from orev3.modeling.models import (
    ModelSpec,
    positive_probability,
)


def test_small_synthetic_logistic_run_is_reproducible() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=(250, 3))
    y = np.tile(np.r_[1, np.zeros(24, dtype=int)], 10)
    weights = np.tile(np.r_[0.5, np.full(24, 0.5 / 24)], 10)
    spec = ModelSpec("logistic_regression", {})
    first = spec.build()
    second = spec.build()
    first.fit(x, y, model__sample_weight=weights)
    second.fit(x, y, model__sample_weight=weights)
    assert np.array_equal(
        positive_probability(first, x), positive_probability(second, x)
    )

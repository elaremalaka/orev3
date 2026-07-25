from __future__ import annotations

from orev3.datasets.square_features import (
    _geometry,
    _orthogonal_neighbors,
)


def test_center_neighbors() -> None:
    assert _orthogonal_neighbors(12) == [7, 17, 11, 13]


def test_corner_neighbors() -> None:
    assert _orthogonal_neighbors(0) == [5, 1]


def test_geometry() -> None:
    assert _geometry(0)[:5] == (0, 0, True, False, False)
    assert _geometry(2)[:5] == (0, 2, False, True, False)
    assert _geometry(12)[:5] == (2, 2, False, False, True)

"""Scalar scenario profiles."""

from __future__ import annotations

from dataclasses import dataclass


class ScalarProfile:
    """A scalar profile sampled by time or distance."""

    def value_at(self, x: float) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class ConstantProfile(ScalarProfile):
    """A profile with one constant value."""

    value: float

    def value_at(self, x: float) -> float:
        return self.value


@dataclass(frozen=True)
class PiecewiseLinearProfile(ScalarProfile):
    """Piecewise-linear interpolation over sorted `(x, value)` points."""

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("PiecewiseLinearProfile requires at least one point")
        last_x: float | None = None
        for x, _ in self.points:
            if last_x is not None and x <= last_x:
                raise ValueError("PiecewiseLinearProfile x values must be strictly increasing")
            last_x = x

    def value_at(self, x: float) -> float:
        if x <= self.points[0][0]:
            return self.points[0][1]
        if x >= self.points[-1][0]:
            return self.points[-1][1]

        for (x0, y0), (x1, y1) in zip(self.points[:-1], self.points[1:]):
            if x0 <= x <= x1:
                fraction = (x - x0) / (x1 - x0)
                return y0 + fraction * (y1 - y0)
        return self.points[-1][1]


@dataclass(frozen=True)
class OffsetProfile(ScalarProfile):
    """Adds a constant offset to another profile."""

    base: ScalarProfile
    offset: float

    def value_at(self, x: float) -> float:
        return self.base.value_at(x) + self.offset

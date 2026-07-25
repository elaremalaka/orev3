from __future__ import annotations

from fractions import Fraction


def allocate_lamports(
    total_lamports: int,
    square_count: int,
    rule: str,
) -> tuple[int, ...]:
    if total_lamports < 0:
        raise ValueError("Deployment cannot be negative")
    if not 1 <= square_count <= 25:
        raise ValueError("square_count must be in 1..25")
    if rule == "equal":
        base, residual = divmod(total_lamports, square_count)
        return tuple(
            base + (1 if rank < residual else 0)
            for rank in range(square_count)
        )
    if rule != "rank_decay":
        raise ValueError("Unsupported allocation rule")
    weights = [Fraction(1, rank) for rank in range(1, square_count + 1)]
    total_weight = sum(weights)
    allocations = [
        int(Fraction(total_lamports) * weight / total_weight)
        for weight in weights
    ]
    residual = total_lamports - sum(allocations)
    for index in range(residual):
        allocations[index % square_count] += 1
    return tuple(allocations)

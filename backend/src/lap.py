from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment  # type: ignore[import-untyped]

__version__ = "0.5.12"


def lapjv(
    cost_matrix: NDArray[np.float64],
    extend_cost: bool = True,  # noqa: FBT001,ARG001
    cost_limit: float = np.inf,
) -> tuple[float, NDArray[np.int_], NDArray[np.int_]]:
    """Compatibility shim for ultralytics on platforms without the native `lap` wheel."""
    matrix: NDArray[np.float64] = np.asarray(cost_matrix, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError("cost_matrix must be a 2D array")

    row_count, column_count = matrix.shape
    row_assignments = np.full(row_count, -1, dtype=int)
    column_assignments = np.full(column_count, -1, dtype=int)
    total_cost = 0.0

    if row_count == 0 or column_count == 0:
        return total_cost, row_assignments, column_assignments

    row_indices, column_indices = linear_sum_assignment(matrix)
    for row_index, column_index in zip(row_indices.tolist(), column_indices.tolist(), strict=False):
        cost = float(matrix[row_index, column_index])
        if cost > cost_limit:
            continue
        row_assignments[row_index] = column_index
        column_assignments[column_index] = row_index
        total_cost += cost

    return total_cost, row_assignments, column_assignments

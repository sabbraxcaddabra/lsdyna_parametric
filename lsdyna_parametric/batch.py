from __future__ import annotations

import itertools
from dataclasses import dataclass

from lsdyna_parametric.variables import VariableField


@dataclass(frozen=True)
class BatchItem:
    index: int
    params: dict[str, float]


def estimate_batch_size(
    base_params: dict[str, float],
    variables: dict[str, VariableField],
) -> int:
    total = 1
    for name in base_params.keys():
        var = variables.get(name)
        if var and var.enabled:
            total *= len(var.generate_values())
    return total


def generate_batch(
    base_params: dict[str, float],
    variables: dict[str, VariableField],
) -> list[BatchItem]:
    names = list(base_params.keys())
    value_lists: list[list[float]] = []
    for name in names:
        var = variables.get(name)
        if var and var.enabled:
            values = var.generate_values()
            value_lists.append(values)
        else:
            value_lists.append([float(base_params[name])])

    items: list[BatchItem] = []
    for i, combo in enumerate(itertools.product(*value_lists), start=1):
        params = {name: float(value) for name, value in zip(names, combo)}
        items.append(BatchItem(index=i, params=params))
    return items


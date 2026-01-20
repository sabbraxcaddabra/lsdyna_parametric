from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VariableField:
    enabled: bool = False
    mode: str = "range"  # "range" | "discrete"
    min_value: float | None = None
    max_value: float | None = None
    step: float = 1.0
    values: list[float] = field(default_factory=list)

    def generate_values(self) -> list[float]:
        if not self.enabled:
            return []
        if self.mode == "discrete":
            return list(self.values)

        if self.min_value is None or self.max_value is None:
            return []
        if self.step <= 0:
            return []

        out: list[float] = []
        current = float(self.min_value)
        max_v = float(self.max_value)
        while current <= max_v + 1e-12:
            out.append(round(current, 10))
            current += float(self.step)
            if len(out) > 1_000_000:
                break
        return out

    def get_badge_text(self) -> str:
        if not self.enabled:
            return ""
        if self.mode == "range":
            count = len(self.generate_values())
            return f"{count} values ({self.min_value:.3g}-{self.max_value:.3g}, step={self.step:.3g})"
        vals = self.values
        if len(vals) <= 3:
            return f"{len(vals)} values [{', '.join(f'{v:.3g}' for v in vals)}]"
        return f"{len(vals)} values [{vals[0]:.3g}, ..., {vals[-1]:.3g}]"

    def to_config_dict(self) -> dict[str, object]:
        cfg: dict[str, object] = {
            "enabled": bool(self.enabled),
            "mode": self.mode,
        }
        if self.mode == "range":
            if self.min_value is not None:
                cfg["min_value"] = float(self.min_value)
            if self.max_value is not None:
                cfg["max_value"] = float(self.max_value)
            cfg["step"] = float(self.step)
        else:
            cfg["values"] = list(self.values)
        return cfg

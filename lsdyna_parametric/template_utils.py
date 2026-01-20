from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import jinja2


_PARAM_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


@dataclass(frozen=True)
class ParamInfo:
    name: str
    description: str = ""


def extract_simple_params(template_text: str) -> set[str]:
    return set(_PARAM_RE.findall(template_text))


def extract_simple_params_from_file(template_file: str | Path) -> set[str]:
    text = Path(template_file).read_text(encoding="utf-8")
    return extract_simple_params(text)


def load_template_defaults(template_dir: str | Path) -> dict[str, object]:
    import tomllib

    config_path = Path(template_dir) / "config.toml"
    if not config_path.exists():
        return {}
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return dict(data.get("template_params", {}))


def load_params_info(template_dir: str | Path) -> dict[str, ParamInfo]:
    info_path = Path(template_dir) / "params_info.json"
    if not info_path.exists():
        return {}

    try:
        raw = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    params_raw: object
    if isinstance(raw, dict) and isinstance(raw.get("params"), dict):
        params_raw = raw["params"]
    else:
        params_raw = raw

    if not isinstance(params_raw, dict):
        return {}

    out: dict[str, ParamInfo] = {}
    for key, value in params_raw.items():
        if not isinstance(key, str):
            continue

        if isinstance(value, dict):
            name = value.get("name", key)
            description = value.get("description", "")
            if not isinstance(name, str):
                name = key
            if not isinstance(description, str):
                description = ""
            out[key] = ParamInfo(name=name, description=description)
            continue

        if isinstance(value, str):
            out[key] = ParamInfo(name=key, description=value)
            continue

    return out


def render_template_to_file(
    template_file: str | Path,
    params: dict[str, object],
    output_file: str | Path,
) -> None:
    template_file = Path(template_file)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(template_file.parent)))
    template = env.get_template(template_file.name)
    rendered = template.render(params)
    Path(output_file).write_text(rendered, encoding="utf-8")

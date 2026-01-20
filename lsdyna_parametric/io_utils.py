from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def backup_if_exists(path: str | Path) -> None:
    p = Path(path)
    if not p.exists():
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = p.with_name(f"{p.name}_backup_{ts}")
    shutil.move(str(p), str(backup))


def copy_template_tree(template_dir: str | Path, dest_dir: str | Path) -> None:
    src = Path(template_dir)
    dst = Path(dest_dir)
    ensure_dir(dst)
    for entry in src.iterdir():
        src_path = entry
        dst_path = dst / entry.name
        if entry.is_dir():
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dst_path)


def _format_toml_value(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_case_config_toml(
    output_path: str | Path,
    template_params: dict[str, float],
    variables_section: dict[str, dict[str, object]],
    template_file: str,
) -> None:
    lines: list[str] = []
    lines.append("[meta]")
    lines.append(f"template_file = {_format_toml_value(template_file)}")
    lines.append("")

    lines.append("[template_params]")
    for key, value in sorted(template_params.items()):
        lines.append(f"{key} = {_format_toml_value(value)}")
    lines.append("")

    lines.append("[variables]")
    lines.append("")
    for name, cfg in sorted(variables_section.items()):
        lines.append(f"[variables.{name}]")
        for k, v in cfg.items():
            lines.append(f"{k} = {_format_toml_value(v)}")
        lines.append("")

    Path(output_path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


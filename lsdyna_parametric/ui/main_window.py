from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressDialog,
    QScrollArea,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from lsdyna_parametric.batch import estimate_batch_size, generate_batch
from lsdyna_parametric.io_utils import backup_if_exists, copy_template_tree, ensure_dir, write_case_config_toml
from lsdyna_parametric.template_utils import (
    ParamInfo,
    extract_simple_params_from_file,
    load_params_info,
    load_template_defaults,
    render_template_to_file,
)
from lsdyna_parametric.ui.variable_field_dialog import VariableFieldDialog
from lsdyna_parametric.variables import VariableField


@dataclass
class ParamWidgets:
    value_spin: QDoubleSpinBox
    badge_label: QLabel
    var_button: QPushButton


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LS-DYNA Parametric Generator")
        self.resize(980, 700)

        self.template_file: str | None = None
        self.template_dir: str | None = None
        self.params_info: dict[str, ParamInfo] = {}

        self.variables: dict[str, VariableField] = {}
        self.param_widgets: dict[str, ParamWidgets] = {}

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        # Template selection
        template_row = QHBoxLayout()
        self.template_label = QLabel("Template: (not selected)")
        self.template_btn = QPushButton("Select template...")
        self.template_btn.clicked.connect(self.select_template)
        template_row.addWidget(self.template_label, 1)
        template_row.addWidget(self.template_btn)
        layout.addLayout(template_row)

        # Output selection
        out_row = QHBoxLayout()
        self.output_label = QLabel("Output: (not selected)")
        self.output_btn = QPushButton("Select output dir...")
        self.output_btn.clicked.connect(self.select_output_dir)
        out_row.addWidget(self.output_label, 1)
        out_row.addWidget(self.output_btn)
        layout.addLayout(out_row)

        # Prefix + options
        options = QGridLayout()
        options.addWidget(QLabel("Folder prefix:"), 0, 0)
        self.prefix_edit = QLineEdit("case")
        options.addWidget(self.prefix_edit, 0, 1)
        options.addWidget(QLabel("Warn if batch >"), 0, 2)
        self.warn_spin = QSpinBox()
        self.warn_spin.setRange(1, 1_000_000)
        self.warn_spin.setValue(50)
        options.addWidget(self.warn_spin, 0, 3)
        layout.addLayout(options)

        # Params area
        layout.addWidget(QLabel("Parameters:"))
        self.params_area = QScrollArea()
        self.params_area.setWidgetResizable(True)
        self.params_container = QWidget()
        self.params_layout = QGridLayout(self.params_container)
        self.params_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.params_area.setWidget(self.params_container)
        layout.addWidget(self.params_area, 1)

        # Actions
        actions = QHBoxLayout()
        actions.addStretch()
        self.generate_btn = QPushButton("Generate batch")
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.clicked.connect(self.generate_clicked)
        self.generate_btn.setEnabled(False)
        actions.addWidget(self.generate_btn)
        layout.addLayout(actions)

        self.output_dir: str | None = None

    def select_template(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select template directory",
            "",
        )
        if not dir_path:
            return

        template_dir = Path(dir_path)
        template_file = template_dir / "input.template"
        if not template_file.exists():
            QMessageBox.warning(
                self,
                "Template Error",
                f"Selected directory does not contain `input.template`:\n{dir_path}",
            )
            return

        self.template_dir = str(template_dir)
        self.template_file = str(template_file)
        self.template_label.setText(f"Template dir: {dir_path}")

        try:
            params = sorted(extract_simple_params_from_file(template_file))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read template:\n{e}")
            self.template_file = None
            self.template_dir = None
            self.params_info = {}
            self.generate_btn.setEnabled(False)
            return

        self.params_info = load_params_info(self.template_dir)

        defaults = {}
        try:
            defaults = load_template_defaults(self.template_dir)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load template config.toml defaults:\n{e}")

        self._rebuild_params_ui(params=params, defaults=defaults, params_info=self.params_info)
        self._update_generate_enabled()

    def select_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select output directory", "")
        if not dir_path:
            return
        self.output_dir = dir_path
        self.output_label.setText(f"Output: {dir_path}")
        self._update_generate_enabled()

    def _update_generate_enabled(self) -> None:
        self.generate_btn.setEnabled(bool(self.template_file) and bool(self.output_dir) and bool(self.param_widgets))

    def _rebuild_params_ui(
        self,
        params: list[str],
        defaults: dict[str, object],
        params_info: dict[str, ParamInfo] | None = None,
    ) -> None:
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if (w := item.widget()) is not None:
                w.setParent(None)

        self.variables = {name: self.variables.get(name, VariableField()) for name in params}
        self.param_widgets = {}
        params_info = params_info or {}

        self.params_layout.addWidget(QLabel("Name"), 0, 0)
        self.params_layout.addWidget(QLabel("Base value"), 0, 1)
        self.params_layout.addWidget(QLabel("Variable"), 0, 2)
        self.params_layout.addWidget(QLabel("Status"), 0, 3)

        for row, name in enumerate(params, start=1):
            meta = params_info.get(name)
            display_name = meta.name if meta else name
            name_label = QLabel(display_name)
            if meta and meta.description.strip():
                name_label.setToolTip(meta.description)
            self.params_layout.addWidget(name_label, row, 0)

            base = defaults.get(name, 0.0)
            try:
                base_val = float(base)
            except Exception:
                base_val = 0.0

            spin = QDoubleSpinBox()
            spin.setRange(-1e12, 1e12)
            spin.setDecimals(8)
            spin.setValue(base_val)
            self.params_layout.addWidget(spin, row, 1)

            btn = QPushButton("Edit…")
            btn.clicked.connect(lambda _checked=False, n=name: self.edit_variable(n))
            self.params_layout.addWidget(btn, row, 2)

            badge = QLabel("")
            badge.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.params_layout.addWidget(badge, row, 3)

            self.param_widgets[name] = ParamWidgets(value_spin=spin, badge_label=badge, var_button=btn)
            self._refresh_badge(name)

    def _refresh_badge(self, name: str) -> None:
        var = self.variables[name]
        badge = self.param_widgets[name].badge_label
        badge.setText(var.get_badge_text())

    def edit_variable(self, name: str) -> None:
        base_value = float(self.param_widgets[name].value_spin.value())
        var = self.variables[name]

        if abs(base_value) < 1e-30:
            default_range = (-1.0, 1.0, 0.1)
        else:
            min_val = base_value * 0.8
            max_val = base_value * 1.2
            step = (max_val - min_val) / 10.0
            step = max(step, 0.1)
            default_range = (min_val, max_val, step)

        display_name = self.params_info.get(name).name if name in self.params_info else name
        dlg = VariableFieldDialog(
            field_name=name,
            display_name=display_name,
            base_value=base_value,
            variable=var,
            default_range=default_range,
        )
        if dlg.exec():
            self._refresh_badge(name)

    def generate_clicked(self) -> None:
        if not self.template_file or not self.template_dir:
            return
        if not self.output_dir:
            return

        prefix = self.prefix_edit.text().strip() or "case"

        base_params = {name: float(w.value_spin.value()) for name, w in self.param_widgets.items()}
        for name, var in self.variables.items():
            if not var.enabled:
                continue
            values = var.generate_values()
            if not values:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    f"Variable '{name}' is enabled but has no generated values.",
                )
                return

        total = estimate_batch_size(base_params, self.variables)
        if total <= 0:
            QMessageBox.warning(self, "Validation Error", "Batch size is 0 (check variable settings).")
            return
        if total > int(self.warn_spin.value()):
            reply = QMessageBox.question(
                self,
                "Large Batch Warning",
                f"This will generate {total} cases. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        batch = generate_batch(base_params, self.variables)
        width = max(3, len(str(len(batch))))

        progress = QProgressDialog("Generating cases...", "Cancel", 0, len(batch), self)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)

        out_root = ensure_dir(self.output_dir)
        created: list[str] = []

        try:
            for i, item in enumerate(batch, start=1):
                progress.setValue(i - 1)
                if progress.wasCanceled():
                    break

                case_name = f"{prefix}_{item.index:0{width}d}"
                case_dir = out_root / case_name
                backup_if_exists(case_dir)
                ensure_dir(case_dir)

                copy_template_tree(self.template_dir, case_dir)

                render_template_to_file(
                    template_file=self.template_file,
                    params=item.params,
                    output_file=case_dir / "input.k",
                )

                variables_section = {k: v.to_config_dict() for k, v in self.variables.items()}
                write_case_config_toml(
                    output_path=case_dir / "config.toml",
                    template_params=item.params,
                    variables_section=variables_section,
                    template_file=os.path.basename(self.template_file),
                )

                created.append(str(case_dir))
                progress.setLabelText(f"Generating {i}/{len(batch)}: {case_name}")
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Generation failed:\n{e}")
            return
        finally:
            progress.setValue(len(batch))

        if progress.wasCanceled():
            QMessageBox.information(self, "Canceled", f"Generated {len(created)} cases (canceled).")
            return

        QMessageBox.information(self, "Done", f"Generated {len(created)} cases into:\n{self.output_dir}")

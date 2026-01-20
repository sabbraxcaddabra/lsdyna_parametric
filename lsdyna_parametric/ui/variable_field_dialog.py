from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from lsdyna_parametric.variables import VariableField


class VariableFieldDialog(QDialog):
    def __init__(
        self,
        field_name: str,
        base_value: float,
        variable: VariableField,
        default_range: tuple[float, float, float] | None = None,
        display_name: str | None = None,
    ):
        super().__init__()
        self.field_name = field_name
        self.display_name = display_name or field_name
        self.base_value = float(base_value)
        self.variable = variable
        self.default_range = default_range or (self.base_value * 0.8, self.base_value * 1.2, 1.0)
        self.init_ui()
        self.load_values()

    def init_ui(self) -> None:
        self.setWindowTitle(f"Variable Field: {self.display_name}")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        self.enabled_cb = QCheckBox("Enable variable field")
        self.enabled_cb.toggled.connect(self.on_enabled_changed)
        layout.addWidget(self.enabled_cb)

        layout.addWidget(QLabel(f"Base value: {self.base_value:g}"))

        mode_group = QGroupBox("Generation Mode")
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()
        self.range_radio = QRadioButton("Range")
        self.discrete_radio = QRadioButton("Discrete values")
        self.mode_group.addButton(self.range_radio, 0)
        self.mode_group.addButton(self.discrete_radio, 1)
        self.mode_group.buttonToggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.range_radio)
        mode_layout.addWidget(self.discrete_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        self.range_widget = QWidget()
        range_layout = QVBoxLayout(self.range_widget)

        range_form = QHBoxLayout()
        range_form.addWidget(QLabel("Min:"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-1e12, 1e12)
        self.min_spin.setDecimals(8)
        range_form.addWidget(self.min_spin)

        range_form.addWidget(QLabel("Max:"))
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-1e12, 1e12)
        self.max_spin.setDecimals(8)
        range_form.addWidget(self.max_spin)

        range_form.addWidget(QLabel("Step:"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(1e-12, 1e12)
        self.step_spin.setDecimals(12)
        range_form.addWidget(self.step_spin)

        range_layout.addLayout(range_form)
        layout.addWidget(self.range_widget)

        self.discrete_widget = QWidget()
        discrete_layout = QVBoxLayout(self.discrete_widget)

        discrete_list = QHBoxLayout()
        self.values_list = QListWidget()
        discrete_list.addWidget(self.values_list)

        btn_col = QVBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.add_value)
        btn_col.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_value)
        btn_col.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_values)
        btn_col.addWidget(self.clear_btn)

        discrete_list.addLayout(btn_col)
        discrete_layout.addLayout(discrete_list)

        add_line = QHBoxLayout()
        add_line.addWidget(QLabel("Value:"))
        self.value_input = QLineEdit()
        add_line.addWidget(self.value_input)
        discrete_layout.addLayout(add_line)

        layout.addWidget(self.discrete_widget)

        self.preview_label = QLabel("Generated values: []")
        self.preview_label.setStyleSheet(
            "QLabel { background-color: #f0f0f0; padding: 6px; border-radius: 3px; }"
        )
        layout.addWidget(self.preview_label)

        self.min_spin.valueChanged.connect(self.update_preview)
        self.max_spin.valueChanged.connect(self.update_preview)
        self.step_spin.valueChanged.connect(self.update_preview)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def load_values(self) -> None:
        self.enabled_cb.setChecked(self.variable.enabled)

        if self.variable.mode == "range":
            self.range_radio.setChecked(True)
            if self.variable.min_value is not None:
                self.min_spin.setValue(float(self.variable.min_value))
            else:
                self.min_spin.setValue(float(self.default_range[0]))

            if self.variable.max_value is not None:
                self.max_spin.setValue(float(self.variable.max_value))
            else:
                self.max_spin.setValue(float(self.default_range[1]))

            self.step_spin.setValue(float(self.variable.step or self.default_range[2]))
        else:
            self.discrete_radio.setChecked(True)
            self.values_list.clear()
            for val in self.variable.values:
                self.values_list.addItem(str(val))

        self.on_enabled_changed(self.variable.enabled)
        self.on_mode_changed()
        self.update_preview()

    def on_enabled_changed(self, enabled: bool) -> None:
        self.range_radio.setEnabled(enabled)
        self.discrete_radio.setEnabled(enabled)
        self.range_widget.setEnabled(enabled)
        self.discrete_widget.setEnabled(enabled)

    def on_mode_changed(self) -> None:
        is_range = self.range_radio.isChecked()
        self.range_widget.setVisible(is_range)
        self.discrete_widget.setVisible(not is_range)
        self.update_preview()

    def add_value(self) -> None:
        try:
            val = float(self.value_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Value", "Please enter a valid number.")
            return
        self.values_list.addItem(str(val))
        self.value_input.clear()
        self.update_preview()

    def remove_value(self) -> None:
        for item in self.values_list.selectedItems():
            self.values_list.takeItem(self.values_list.row(item))
        self.update_preview()

    def clear_values(self) -> None:
        self.values_list.clear()
        self.update_preview()

    def update_preview(self) -> None:
        if not self.enabled_cb.isChecked():
            self.preview_label.setText("Variable disabled")
            return

        if self.range_radio.isChecked():
            values = []
            current = self.min_spin.value()
            max_val = self.max_spin.value()
            step = self.step_spin.value()
            while current <= max_val and len(values) < 100:
                values.append(current)
                current += step
            if len(values) >= 100:
                self.preview_label.setText("Generated values: >100 (too many to preview)")
                return
            vals_str = ", ".join(f"{v:.6g}" for v in values[:10])
            if len(values) > 10:
                vals_str += f", ... ({len(values)} total)"
            self.preview_label.setText(f"Generated values: [{vals_str}]")
            return

        values = [float(self.values_list.item(i).text()) for i in range(self.values_list.count())]
        vals_str = ", ".join(f"{v:.6g}" for v in values[:10])
        if len(values) > 10:
            vals_str += f", ... ({len(values)} total)"
        self.preview_label.setText(f"Generated values: [{vals_str}]")

    def accept(self) -> None:
        if not self.enabled_cb.isChecked():
            self.variable.enabled = False
            super().accept()
            return

        if self.range_radio.isChecked():
            min_val = float(self.min_spin.value())
            max_val = float(self.max_spin.value())
            step = float(self.step_spin.value())

            if min_val >= max_val:
                QMessageBox.warning(self, "Validation Error", "Min value must be less than Max value.")
                return
            if step <= 0:
                QMessageBox.warning(self, "Validation Error", "Step must be greater than 0.")
                return
            count = int((max_val - min_val) / step) + 1
            if count > 100:
                reply = QMessageBox.question(
                    self,
                    "Large Batch Warning",
                    f"This will generate {count} values for '{self.field_name}'. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            self.variable.mode = "range"
            self.variable.min_value = min_val
            self.variable.max_value = max_val
            self.variable.step = step
            self.variable.values = []
        else:
            values = [float(self.values_list.item(i).text()) for i in range(self.values_list.count())]
            if len(values) < 2:
                QMessageBox.warning(self, "Validation Error", "Please add at least 2 discrete values.")
                return
            if len(set(values)) != len(values):
                QMessageBox.warning(self, "Validation Error", "Duplicate values detected.")
                return

            self.variable.mode = "discrete"
            self.variable.values = values
            self.variable.min_value = None
            self.variable.max_value = None

        self.variable.enabled = True
        super().accept()

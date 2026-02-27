"""Delay stage control widget."""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QPushButton, QLCDNumber,
    QFormLayout
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class DelayStageWidget(QWidget):
    """Widget for controlling the delay stage position."""

    # Signal emitted when position changes
    position_changed = pyqtSignal(float)  # position in ps

    def __init__(self, parent=None):
        super().__init__(parent)

        # Stage parameters
        self._position_mm = 0.0  # Internal position in mm
        self._time_zero_mm = 0.0  # Time zero position in mm
        self._mm_per_ps = 0.15  # Conversion factor (c * 2 / 1000 / 2)

        # Step sizes in ps
        self._small_step = 0.1
        self._large_step = 10.0

        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        group = QGroupBox("Delay Stage")
        group_layout = QVBoxLayout(group)

        # Position display
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position:"))

        self.position_lcd = QLCDNumber(8)
        self.position_lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.position_lcd.setMinimumHeight(40)
        font = QFont()
        font.setPointSize(14)
        self.position_lcd.setFont(font)
        pos_layout.addWidget(self.position_lcd)

        pos_layout.addWidget(QLabel("ps"))
        group_layout.addLayout(pos_layout)

        # Movement buttons
        move_layout = QHBoxLayout()

        self.btn_large_back = QPushButton("<<")
        self.btn_large_back.setToolTip("Move back by large step")
        self.btn_large_back.clicked.connect(lambda: self._move(-self._large_step))
        move_layout.addWidget(self.btn_large_back)

        self.btn_small_back = QPushButton("<")
        self.btn_small_back.setToolTip("Move back by small step")
        self.btn_small_back.clicked.connect(lambda: self._move(-self._small_step))
        move_layout.addWidget(self.btn_small_back)

        self.btn_small_fwd = QPushButton(">")
        self.btn_small_fwd.setToolTip("Move forward by small step")
        self.btn_small_fwd.clicked.connect(lambda: self._move(self._small_step))
        move_layout.addWidget(self.btn_small_fwd)

        self.btn_large_fwd = QPushButton(">>")
        self.btn_large_fwd.setToolTip("Move forward by large step")
        self.btn_large_fwd.clicked.connect(lambda: self._move(self._large_step))
        move_layout.addWidget(self.btn_large_fwd)

        group_layout.addLayout(move_layout)

        # Step size controls
        step_layout = QFormLayout()

        self.small_step_spin = QDoubleSpinBox()
        self.small_step_spin.setRange(0.001, 10.0)
        self.small_step_spin.setDecimals(3)
        self.small_step_spin.setValue(self._small_step)
        self.small_step_spin.setSuffix(" ps")
        self.small_step_spin.valueChanged.connect(self._on_small_step_changed)
        step_layout.addRow("Small step:", self.small_step_spin)

        self.large_step_spin = QDoubleSpinBox()
        self.large_step_spin.setRange(0.1, 1000.0)
        self.large_step_spin.setDecimals(2)
        self.large_step_spin.setValue(self._large_step)
        self.large_step_spin.setSuffix(" ps")
        self.large_step_spin.valueChanged.connect(self._on_large_step_changed)
        step_layout.addRow("Large step:", self.large_step_spin)

        group_layout.addLayout(step_layout)

        # Go to position
        goto_layout = QHBoxLayout()
        goto_layout.addWidget(QLabel("Go to:"))

        self.goto_spin = QDoubleSpinBox()
        self.goto_spin.setRange(-10000, 10000)
        self.goto_spin.setDecimals(3)
        self.goto_spin.setValue(0)
        self.goto_spin.setSuffix(" ps")
        goto_layout.addWidget(self.goto_spin)

        self.goto_btn = QPushButton("Go")
        self.goto_btn.clicked.connect(self._on_goto)
        goto_layout.addWidget(self.goto_btn)

        group_layout.addLayout(goto_layout)

        # Time zero controls
        t0_layout = QHBoxLayout()

        self.set_t0_btn = QPushButton("Set T0")
        self.set_t0_btn.setToolTip("Set current position as time zero")
        self.set_t0_btn.clicked.connect(self._on_set_t0)
        t0_layout.addWidget(self.set_t0_btn)

        self.goto_t0_btn = QPushButton("Go to T0")
        self.goto_t0_btn.setToolTip("Return to time zero position")
        self.goto_t0_btn.clicked.connect(self._on_goto_t0)
        t0_layout.addWidget(self.goto_t0_btn)

        group_layout.addLayout(t0_layout)

        layout.addWidget(group)
        layout.addStretch()

        # Initialize display
        self._update_display()

    def _update_display(self):
        """Update the LCD display with current position."""
        position_ps = self.get_position_ps()
        self.position_lcd.display(f"{position_ps:8.3f}")

    def _move(self, delta_ps: float):
        """Move the stage by a delta in ps.

        Args:
            delta_ps: Position change in picoseconds.
        """
        delta_mm = delta_ps * self._mm_per_ps
        self._position_mm += delta_mm
        self._update_display()
        self.position_changed.emit(self.get_position_ps())

    def _on_small_step_changed(self, value):
        """Handle small step change."""
        self._small_step = value

    def _on_large_step_changed(self, value):
        """Handle large step change."""
        self._large_step = value

    def _on_goto(self):
        """Handle go to position button."""
        target_ps = self.goto_spin.value()
        self.set_position_ps(target_ps)

    def _on_set_t0(self):
        """Set current position as time zero."""
        self._time_zero_mm = self._position_mm
        self._update_display()

    def _on_goto_t0(self):
        """Return to time zero position."""
        self._position_mm = self._time_zero_mm
        self._update_display()
        self.position_changed.emit(self.get_position_ps())

    def get_position_ps(self) -> float:
        """Get current position in picoseconds relative to T0.

        Returns:
            Position in picoseconds.
        """
        return (self._position_mm - self._time_zero_mm) / self._mm_per_ps

    def set_position_ps(self, position_ps: float):
        """Set position in picoseconds relative to T0.

        Args:
            position_ps: Target position in picoseconds.
        """
        self._position_mm = self._time_zero_mm + position_ps * self._mm_per_ps
        self._update_display()
        self.position_changed.emit(position_ps)

    def get_position_mm(self) -> float:
        """Get current absolute position in mm."""
        return self._position_mm

    def set_enabled(self, enabled: bool):
        """Enable or disable the controls.

        Args:
            enabled: True to enable, False to disable.
        """
        self.btn_large_back.setEnabled(enabled)
        self.btn_small_back.setEnabled(enabled)
        self.btn_small_fwd.setEnabled(enabled)
        self.btn_large_fwd.setEnabled(enabled)
        self.small_step_spin.setEnabled(enabled)
        self.large_step_spin.setEnabled(enabled)
        self.goto_spin.setEnabled(enabled)
        self.goto_btn.setEnabled(enabled)
        self.set_t0_btn.setEnabled(enabled)
        self.goto_t0_btn.setEnabled(enabled)

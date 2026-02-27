"""Live spectra display widget for real-time monitoring."""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QSpinBox, QCheckBox,
    QPushButton, QFormLayout
)
from PyQt6.QtCore import QTimer, pyqtSignal
import pyqtgraph as pg


class LiveViewWidget(QWidget):
    """Widget for displaying live reference, signal, and OD spectra."""

    # Signal emitted when integration time changes
    integration_time_changed = pyqtSignal(float)
    wavelength_range_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._wavelengths = np.linspace(400, 800, 2048)
        self._reference = np.zeros(2048)
        self._signal = np.zeros(2048)
        self._od = np.zeros(2048)

        self._auto_scale = True
        self._y_min = 0
        self._y_max = 65535
        self._od_min = -0.1
        self._od_max = 0.1

        self._setup_ui()
        self._setup_plots()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Plots container
        plots_layout = QHBoxLayout()

        # Raw spectra plot
        self.raw_plot = pg.PlotWidget(title="Reference / Signal Spectra")
        self.raw_plot.setLabel("bottom", "Wavelength", units="nm")
        self.raw_plot.setLabel("left", "Intensity", units="counts")
        self.raw_plot.addLegend()
        plots_layout.addWidget(self.raw_plot)

        # OD plot
        self.od_plot = pg.PlotWidget(title="Optical Density")
        self.od_plot.setLabel("bottom", "Wavelength", units="nm")
        self.od_plot.setLabel("left", "ΔOD")
        plots_layout.addWidget(self.od_plot)

        layout.addLayout(plots_layout)

        # Controls
        controls_layout = QHBoxLayout()

        # Spectrometer settings
        spec_group = QGroupBox("Spectrometer")
        spec_layout = QFormLayout(spec_group)

        self.integration_spin = QSpinBox()
        self.integration_spin.setRange(10, 5000)
        self.integration_spin.setValue(100)
        self.integration_spin.setSuffix(" ms")
        self.integration_spin.valueChanged.connect(self._on_integration_changed)
        spec_layout.addRow("Integration:", self.integration_spin)

        wl_layout = QHBoxLayout()
        self.wl_min_spin = QDoubleSpinBox()
        self.wl_min_spin.setRange(200, 1000)
        self.wl_min_spin.setValue(400)
        self.wl_min_spin.setSuffix(" nm")
        wl_layout.addWidget(QLabel("Min:"))
        wl_layout.addWidget(self.wl_min_spin)

        self.wl_max_spin = QDoubleSpinBox()
        self.wl_max_spin.setRange(200, 1000)
        self.wl_max_spin.setValue(800)
        self.wl_max_spin.setSuffix(" nm")
        wl_layout.addWidget(QLabel("Max:"))
        wl_layout.addWidget(self.wl_max_spin)

        self.wl_apply_btn = QPushButton("Apply")
        self.wl_apply_btn.clicked.connect(self._on_wavelength_apply)
        wl_layout.addWidget(self.wl_apply_btn)

        spec_layout.addRow("Wavelength:", wl_layout)
        controls_layout.addWidget(spec_group)

        # Y-scale settings
        scale_group = QGroupBox("Y-Scale")
        scale_layout = QFormLayout(scale_group)

        self.auto_scale_check = QCheckBox("Auto")
        self.auto_scale_check.setChecked(True)
        self.auto_scale_check.stateChanged.connect(self._on_auto_scale_changed)
        scale_layout.addRow(self.auto_scale_check)

        y_layout = QHBoxLayout()
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1e6, 1e6)
        self.y_min_spin.setValue(0)
        self.y_min_spin.setEnabled(False)
        y_layout.addWidget(QLabel("Min:"))
        y_layout.addWidget(self.y_min_spin)

        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1e6, 1e6)
        self.y_max_spin.setValue(65535)
        self.y_max_spin.setEnabled(False)
        y_layout.addWidget(QLabel("Max:"))
        y_layout.addWidget(self.y_max_spin)

        scale_layout.addRow("Raw:", y_layout)

        od_layout = QHBoxLayout()
        self.od_min_spin = QDoubleSpinBox()
        self.od_min_spin.setRange(-10, 10)
        self.od_min_spin.setDecimals(3)
        self.od_min_spin.setValue(-0.1)
        self.od_min_spin.setEnabled(False)
        od_layout.addWidget(QLabel("Min:"))
        od_layout.addWidget(self.od_min_spin)

        self.od_max_spin = QDoubleSpinBox()
        self.od_max_spin.setRange(-10, 10)
        self.od_max_spin.setDecimals(3)
        self.od_max_spin.setValue(0.1)
        self.od_max_spin.setEnabled(False)
        od_layout.addWidget(QLabel("Max:"))
        od_layout.addWidget(self.od_max_spin)

        scale_layout.addRow("OD:", od_layout)

        controls_layout.addWidget(scale_group)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

    def _setup_plots(self):
        """Initialize plot items."""
        # Reference spectrum (blue)
        self.ref_curve = self.raw_plot.plot(
            self._wavelengths, self._reference,
            pen=pg.mkPen(color="b", width=1),
            name="Reference"
        )

        # Signal spectrum (red)
        self.sig_curve = self.raw_plot.plot(
            self._wavelengths, self._signal,
            pen=pg.mkPen(color="r", width=1),
            name="Signal"
        )

        # OD spectrum (green)
        self.od_curve = self.od_plot.plot(
            self._wavelengths, self._od,
            pen=pg.mkPen(color="g", width=1)
        )

        # Zero line for OD
        self.od_plot.addLine(y=0, pen=pg.mkPen(color="gray", style=pg.QtCore.Qt.PenStyle.DashLine))

    def update_spectra(
        self,
        wavelengths: np.ndarray,
        reference: np.ndarray,
        signal: np.ndarray
    ):
        """Update the displayed spectra.

        Args:
            wavelengths: Wavelength array.
            reference: Reference spectrum intensities.
            signal: Signal spectrum intensities.
        """
        self._wavelengths = wavelengths
        self._reference = reference
        self._signal = signal

        # Calculate OD
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = signal / reference
            ratio = np.clip(ratio, 1e-10, 1e10)
            self._od = -np.log10(ratio)
            self._od = np.nan_to_num(self._od, nan=0, posinf=0, neginf=0)

        # Update curves
        self.ref_curve.setData(wavelengths, reference)
        self.sig_curve.setData(wavelengths, signal)
        self.od_curve.setData(wavelengths, self._od)

        # Auto-scale if enabled
        if self._auto_scale:
            self.raw_plot.enableAutoRange()
            self.od_plot.enableAutoRange()
        else:
            self.raw_plot.setYRange(self._y_min, self._y_max)
            self.od_plot.setYRange(self._od_min, self._od_max)

    def get_integration_time(self) -> float:
        """Return current integration time in ms."""
        return self.integration_spin.value()

    def get_wavelength_range(self) -> tuple:
        """Return current wavelength range (min, max)."""
        return self.wl_min_spin.value(), self.wl_max_spin.value()

    def _on_integration_changed(self, value):
        """Handle integration time change."""
        self.integration_time_changed.emit(float(value))

    def _on_wavelength_apply(self):
        """Handle wavelength range apply."""
        wl_min = self.wl_min_spin.value()
        wl_max = self.wl_max_spin.value()
        if wl_min < wl_max:
            self.wavelength_range_changed.emit(wl_min, wl_max)

    def _on_auto_scale_changed(self, state):
        """Handle auto-scale checkbox change."""
        self._auto_scale = bool(state)
        enabled = not self._auto_scale

        self.y_min_spin.setEnabled(enabled)
        self.y_max_spin.setEnabled(enabled)
        self.od_min_spin.setEnabled(enabled)
        self.od_max_spin.setEnabled(enabled)

        if not self._auto_scale:
            self._y_min = self.y_min_spin.value()
            self._y_max = self.y_max_spin.value()
            self._od_min = self.od_min_spin.value()
            self._od_max = self.od_max_spin.value()

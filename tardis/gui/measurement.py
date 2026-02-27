"""Measurement control widget and worker thread."""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QSpinBox, QPushButton,
    QProgressBar, QFormLayout
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QElapsedTimer


class MeasurementWorker(QThread):
    """Worker thread for running TA measurements."""

    # Signals
    progress = pyqtSignal(int, int)  # current_point, total_points
    point_acquired = pyqtSignal(int, float, object)  # index, time_delay, od_spectrum
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_requested = False

        # Measurement parameters
        self.time_delays = None
        self.integration_time = 100  # ms
        self.averages = 10
        self.spectrometer = None
        self.ta_model = None

    def configure(
        self,
        time_delays: np.ndarray,
        integration_time: float,
        averages: int,
        spectrometer,
        ta_model,
    ):
        """Configure the measurement parameters.

        Args:
            time_delays: Array of time delay values in ps.
            integration_time: Integration time in ms.
            averages: Number of averages per point.
            spectrometer: SimulatedSpectrometer instance.
            ta_model: TransientAbsorptionModel instance.
        """
        self.time_delays = time_delays
        self.integration_time = integration_time
        self.averages = averages
        self.spectrometer = spectrometer
        self.ta_model = ta_model

    def stop(self):
        """Request measurement stop."""
        self._stop_requested = True

    def run(self):
        """Run the measurement sequence."""
        try:
            self._stop_requested = False

            if self.time_delays is None or self.spectrometer is None:
                self.error.emit("Measurement not configured")
                return

            n_points = len(self.time_delays)

            for i, t_delay in enumerate(self.time_delays):
                if self._stop_requested:
                    break

                # Get pump effect for this time delay
                pump_effect = self.ta_model.get_pump_effect(t_delay)

                # Accumulate averages
                od_sum = np.zeros(len(self.spectrometer.wavelengths))

                for avg in range(self.averages):
                    if self._stop_requested:
                        break

                    # Acquire reference and signal
                    wl, ref, sig = self.spectrometer.acquire_reference_signal_pair(
                        self.integration_time, pump_effect
                    )

                    # Calculate OD
                    with np.errstate(divide="ignore", invalid="ignore"):
                        ratio = sig / ref
                        ratio = np.clip(ratio, 1e-10, 1e10)
                        od = -np.log10(ratio)
                        od = np.nan_to_num(od, nan=0, posinf=0, neginf=0)

                    od_sum += od

                    # Small delay for simulation responsiveness
                    self.msleep(5)

                if self._stop_requested:
                    break

                # Average
                od_mean = od_sum / self.averages

                # Emit results
                self.point_acquired.emit(i, t_delay, od_mean.copy())
                self.progress.emit(i + 1, n_points)

            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class MeasurementWidget(QWidget):
    """Widget for measurement controls and progress display."""

    # Signals
    measurement_started = pyqtSignal()
    measurement_stopped = pyqtSignal()
    measurement_finished = pyqtSignal()
    point_acquired = pyqtSignal(int, float, object)  # index, time, spectrum
    save_data_requested = pyqtSignal()
    save_image_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_running = False
        self._elapsed_timer = QElapsedTimer()
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_time_display)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        group = QGroupBox("Measurement")
        group_layout = QVBoxLayout(group)

        # Scan parameters
        params_layout = QFormLayout()

        self.start_delay_spin = QDoubleSpinBox()
        self.start_delay_spin.setRange(-10000, 10000)
        self.start_delay_spin.setDecimals(3)
        self.start_delay_spin.setValue(-1)
        self.start_delay_spin.setSuffix(" ps")
        params_layout.addRow("Start delay:", self.start_delay_spin)

        self.end_delay_spin = QDoubleSpinBox()
        self.end_delay_spin.setRange(-10000, 10000)
        self.end_delay_spin.setDecimals(3)
        self.end_delay_spin.setValue(100)
        self.end_delay_spin.setSuffix(" ps")
        params_layout.addRow("End delay:", self.end_delay_spin)

        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.001, 1000)
        self.step_spin.setDecimals(3)
        self.step_spin.setValue(0.5)
        self.step_spin.setSuffix(" ps")
        params_layout.addRow("Step:", self.step_spin)

        self.averages_spin = QSpinBox()
        self.averages_spin.setRange(1, 10000)
        self.averages_spin.setValue(10)
        params_layout.addRow("Averages:", self.averages_spin)

        group_layout.addLayout(params_layout)

        # Control buttons
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("START")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)

        group_layout.addLayout(btn_layout)

        # Save buttons
        save_layout = QHBoxLayout()

        self.save_data_btn = QPushButton("Save Data")
        self.save_data_btn.clicked.connect(self.save_data_requested.emit)
        save_layout.addWidget(self.save_data_btn)

        self.save_image_btn = QPushButton("Save Image")
        self.save_image_btn.clicked.connect(self.save_image_requested.emit)
        save_layout.addWidget(self.save_image_btn)

        group_layout.addLayout(save_layout)

        # Progress
        progress_layout = QFormLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addRow("Progress:", self.progress_bar)

        self.elapsed_label = QLabel("00:00:00")
        progress_layout.addRow("Elapsed:", self.elapsed_label)

        self.remaining_label = QLabel("--:--:--")
        progress_layout.addRow("Remaining:", self.remaining_label)

        group_layout.addLayout(progress_layout)

        layout.addWidget(group)
        layout.addStretch()

    def _on_start(self):
        """Handle start button click."""
        self._is_running = True
        self._elapsed_timer.start()
        self._update_timer.start(1000)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_params_enabled(False)

        self.progress_bar.setValue(0)
        self.elapsed_label.setText("00:00:00")
        self.remaining_label.setText("Calculating...")

        self.measurement_started.emit()

    def _on_stop(self):
        """Handle stop button click."""
        self._is_running = False
        self._update_timer.stop()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_params_enabled(True)

        self.measurement_stopped.emit()

    def on_measurement_finished(self):
        """Handle measurement completion."""
        self._is_running = False
        self._update_timer.stop()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_params_enabled(True)

        self.progress_bar.setValue(100)
        self.remaining_label.setText("00:00:00")

        self.measurement_finished.emit()

    def update_progress(self, current: int, total: int):
        """Update progress display.

        Args:
            current: Current point number.
            total: Total number of points.
        """
        if total > 0:
            percent = int(100 * current / total)
            self.progress_bar.setValue(percent)

            # Calculate remaining time
            if current > 0:
                elapsed_ms = self._elapsed_timer.elapsed()
                rate = elapsed_ms / current
                remaining_ms = rate * (total - current)
                self.remaining_label.setText(self._format_time(int(remaining_ms)))

    def _update_time_display(self):
        """Update elapsed time display."""
        elapsed_ms = self._elapsed_timer.elapsed()
        self.elapsed_label.setText(self._format_time(elapsed_ms))

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as HH:MM:SS."""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        return f"{hours:02d}:{minutes % 60:02d}:{seconds % 60:02d}"

    def _set_params_enabled(self, enabled: bool):
        """Enable or disable parameter inputs."""
        self.start_delay_spin.setEnabled(enabled)
        self.end_delay_spin.setEnabled(enabled)
        self.step_spin.setEnabled(enabled)
        self.averages_spin.setEnabled(enabled)

    def get_time_delays(self) -> np.ndarray:
        """Generate array of time delay values.

        Returns:
            NumPy array of time delays in ps.
        """
        start = self.start_delay_spin.value()
        end = self.end_delay_spin.value()
        step = self.step_spin.value()

        if step <= 0:
            step = 0.5

        return np.arange(start, end + step / 2, step)

    def get_averages(self) -> int:
        """Return number of averages."""
        return self.averages_spin.value()

    def is_running(self) -> bool:
        """Return True if measurement is running."""
        return self._is_running

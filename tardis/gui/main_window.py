"""Main application window."""

import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from .live_view import LiveViewWidget
from .delay_stage import DelayStageWidget
from .measurement import MeasurementWidget, MeasurementWorker
from .map_view import MapViewWidget
from .dialogs import SaveDataDialog, SaveImageDialog

from ..simulation import SimulatedSpectrometer, TransientAbsorptionModel
from ..data import export_ascii, export_image


class MainWindow(QMainWindow):
    """Main application window for TARDIS."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TARDIS - Transient Absorption Spectrometer")
        self.setMinimumSize(1200, 800)

        # Initialize simulation components
        self.spectrometer = SimulatedSpectrometer(400, 800, 2048)
        self.ta_model = TransientAbsorptionModel(self.spectrometer.wavelengths)

        # Measurement state
        self._live_mode = True
        self._measurement_worker = None

        # Data storage
        self._current_wavelengths = None
        self._current_time_delays = None
        self._current_ta_map = None

        self._setup_ui()
        self._setup_menus()
        self._connect_signals()
        self._start_live_update()

    def _setup_ui(self):
        """Set up the main window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Top section: Live view (spectra) and map view
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Live spectra
        self.live_view = LiveViewWidget()
        top_splitter.addWidget(self.live_view)

        # Right: 2D map
        self.map_view = MapViewWidget()
        top_splitter.addWidget(self.map_view)

        top_splitter.setSizes([600, 600])
        main_layout.addWidget(top_splitter, stretch=2)

        # Bottom section: Controls
        controls_layout = QHBoxLayout()

        # Delay stage controls
        self.delay_stage = DelayStageWidget()
        controls_layout.addWidget(self.delay_stage)

        # Measurement controls
        self.measurement = MeasurementWidget()
        controls_layout.addWidget(self.measurement)

        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Live mode active")

    def _setup_menus(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        save_data_action = QAction("Save Data...", self)
        save_data_action.triggered.connect(self._on_save_data)
        file_menu.addAction(save_data_action)

        save_image_action = QAction("Save Image...", self)
        save_image_action.triggered.connect(self._on_save_image)
        file_menu.addAction(save_image_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        reset_sim_action = QAction("Reset Simulation", self)
        reset_sim_action.triggered.connect(self._reset_simulation)
        settings_menu.addAction(reset_sim_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        """Connect widget signals to handlers."""
        # Live view signals
        self.live_view.integration_time_changed.connect(
            self._on_integration_time_changed
        )
        self.live_view.wavelength_range_changed.connect(
            self._on_wavelength_range_changed
        )

        # Delay stage signals
        self.delay_stage.position_changed.connect(self._on_position_changed)

        # Measurement signals
        self.measurement.measurement_started.connect(self._on_measurement_start)
        self.measurement.measurement_stopped.connect(self._on_measurement_stop)
        self.measurement.save_data_requested.connect(self._on_save_data)
        self.measurement.save_image_requested.connect(self._on_save_image)

        # Map view signals
        self.map_view.point_clicked.connect(self._on_map_click)

    def _start_live_update(self):
        """Start the live spectrum update timer."""
        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self._update_live_spectra)
        self.live_timer.start(100)  # 10 Hz update

    def _update_live_spectra(self):
        """Update live spectra display."""
        if not self._live_mode:
            return

        # Get current delay position
        delay_ps = self.delay_stage.get_position_ps()

        # Get pump effect at current delay
        pump_effect = self.ta_model.get_pump_effect(delay_ps)

        # Acquire spectra
        integration_time = self.live_view.get_integration_time()
        wl, ref, sig = self.spectrometer.acquire_reference_signal_pair(
            integration_time, pump_effect
        )

        # Update display
        self.live_view.update_spectra(wl, ref, sig)

    def _on_integration_time_changed(self, value):
        """Handle integration time change."""
        self.status_bar.showMessage(f"Integration time: {value:.0f} ms")

    def _on_wavelength_range_changed(self, wl_min, wl_max):
        """Handle wavelength range change."""
        self.spectrometer.set_wavelength_range(wl_min, wl_max)
        self.ta_model.wavelengths = self.spectrometer.wavelengths
        self.status_bar.showMessage(f"Wavelength range: {wl_min:.0f}-{wl_max:.0f} nm")

    def _on_position_changed(self, position_ps):
        """Handle delay stage position change."""
        self.status_bar.showMessage(f"Delay: {position_ps:.3f} ps")

    def _on_measurement_start(self):
        """Handle measurement start."""
        self._live_mode = False
        self.live_timer.stop()

        # Get parameters
        time_delays = self.measurement.get_time_delays()
        integration_time = self.live_view.get_integration_time()
        averages = self.measurement.get_averages()

        # Store wavelengths and time delays
        self._current_wavelengths = self.spectrometer.wavelengths.copy()
        self._current_time_delays = time_delays.copy()
        self._current_ta_map = np.zeros(
            (len(time_delays), len(self._current_wavelengths))
        )

        # Initialize map view
        self.map_view.initialize_map(
            self._current_wavelengths, self._current_time_delays
        )

        # Disable stage controls
        self.delay_stage.set_enabled(False)

        # Create and start worker
        self._measurement_worker = MeasurementWorker()
        self._measurement_worker.configure(
            time_delays,
            integration_time,
            averages,
            self.spectrometer,
            self.ta_model,
        )

        self._measurement_worker.progress.connect(self._on_measurement_progress)
        self._measurement_worker.point_acquired.connect(self._on_point_acquired)
        self._measurement_worker.finished.connect(self._on_measurement_finished)
        self._measurement_worker.error.connect(self._on_measurement_error)

        self._measurement_worker.start()
        self.status_bar.showMessage("Measurement running...")

    def _on_measurement_stop(self):
        """Handle measurement stop request."""
        if self._measurement_worker:
            self._measurement_worker.stop()
        self.status_bar.showMessage("Measurement stopped by user")

    def _on_measurement_error(self, error_msg):
        """Handle measurement error."""
        self._live_mode = True
        self.live_timer.start()
        self.delay_stage.set_enabled(True)
        self.measurement.on_measurement_finished()
        self.status_bar.showMessage(f"Measurement error: {error_msg}")
        QMessageBox.critical(self, "Measurement Error", error_msg)

    def _on_measurement_progress(self, current, total):
        """Handle measurement progress update."""
        self.measurement.update_progress(current, total)

    def _on_point_acquired(self, index, time_delay, od_spectrum):
        """Handle acquired data point."""
        # Store data
        self._current_ta_map[index, :] = od_spectrum

        # Update map view
        self.map_view.update_row(index, od_spectrum)

        # Move delay stage display
        self.delay_stage.set_position_ps(time_delay)

        # Update live view with current spectra
        pump_effect = self.ta_model.get_pump_effect(time_delay)
        wl, ref, sig = self.spectrometer.acquire_reference_signal_pair(
            self.live_view.get_integration_time(), pump_effect
        )
        self.live_view.update_spectra(wl, ref, sig)

    def _on_measurement_finished(self):
        """Handle measurement completion."""
        self._live_mode = True
        self.live_timer.start()
        self.delay_stage.set_enabled(True)
        self.measurement.on_measurement_finished()
        self.status_bar.showMessage("Measurement complete")

    def _on_map_click(self, wavelength, time_delay):
        """Handle click on the 2D map."""
        self.status_bar.showMessage(
            f"Clicked: {wavelength:.1f} nm, {time_delay:.3f} ps"
        )

    def _on_save_data(self):
        """Handle save data request."""
        if self._current_ta_map is None:
            QMessageBox.warning(
                self, "No Data", "No measurement data to save."
            )
            return

        dialog = SaveDataDialog(self)
        if dialog.exec():
            filepath = dialog.get_filepath()
            if filepath:
                metadata = dialog.get_metadata()
                metadata["Integration time (ms)"] = str(
                    self.live_view.get_integration_time()
                )
                metadata["Averages"] = str(self.measurement.get_averages())

                try:
                    export_ascii(
                        filepath,
                        self._current_wavelengths,
                        self._current_time_delays,
                        self._current_ta_map,
                        metadata,
                    )
                    self.status_bar.showMessage(f"Data saved to {filepath}")
                except Exception as e:
                    QMessageBox.critical(
                        self, "Save Error", f"Failed to save data: {e}"
                    )

    def _on_save_image(self):
        """Handle save image request."""
        if self._current_ta_map is None:
            QMessageBox.warning(
                self, "No Data", "No measurement data to save."
            )
            return

        dialog = SaveImageDialog(self)
        if dialog.exec():
            filepath = dialog.get_filepath()
            if filepath:
                options = dialog.get_options()

                try:
                    export_image(
                        filepath,
                        self._current_wavelengths,
                        self._current_time_delays,
                        self._current_ta_map,
                        title=options.get("title", "TA Spectrum"),
                        colormap=options.get("colormap", "RdBu_r"),
                        vmin=options.get("vmin"),
                        vmax=options.get("vmax"),
                        dpi=options.get("dpi", 300),
                    )
                    self.status_bar.showMessage(f"Image saved to {filepath}")
                except Exception as e:
                    QMessageBox.critical(
                        self, "Save Error", f"Failed to save image: {e}"
                    )

    def _reset_simulation(self):
        """Reset the simulation to defaults."""
        self.spectrometer = SimulatedSpectrometer(400, 800, 2048)
        self.ta_model = TransientAbsorptionModel(self.spectrometer.wavelengths)
        self.status_bar.showMessage("Simulation reset")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About TARDIS",
            "TARDIS - Transient Absorption Rapid Data Integration System\n\n"
            "Version 0.1.0\n\n"
            "A PyQt6-based GUI for controlling and simulating\n"
            "transient absorption spectroscopy measurements.",
        )

    def closeEvent(self, event):
        """Handle window close event."""
        # Stop any running measurement
        if self._measurement_worker and self._measurement_worker.isRunning():
            self._measurement_worker.stop()
            self._measurement_worker.wait()

        self.live_timer.stop()
        event.accept()

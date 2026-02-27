"""2D TA map display widget."""

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal
import pyqtgraph as pg


class MapViewWidget(QWidget):
    """Widget for displaying 2D TA map (wavelength x time)."""

    # Signals
    point_clicked = pyqtSignal(float, float)  # wavelength, time_delay

    def __init__(self, parent=None):
        super().__init__(parent)

        self._wavelengths = None
        self._time_delays = None
        self._ta_map = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("2D TA Map (Wavelength x Time)")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        # Image view
        self.image_view = pg.ImageView()
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()

        # Unlock aspect ratio so image fills the view
        self.image_view.getView().setAspectLocked(False)

        # Set up colormap (diverging, centered at zero)
        colormap = pg.colormap.get("RdBu_r", source="matplotlib")
        self.image_view.setColorMap(colormap)

        # Connect click signal
        self.image_view.getView().scene().sigMouseClicked.connect(
            self._on_mouse_clicked
        )

        layout.addWidget(self.image_view)

        # Info label
        self.info_label = QLabel("No data")
        layout.addWidget(self.info_label)

    def initialize_map(self, wavelengths: np.ndarray, time_delays: np.ndarray):
        """Initialize the map with axes.

        Args:
            wavelengths: Array of wavelength values.
            time_delays: Array of time delay values.
        """
        self._wavelengths = wavelengths
        self._time_delays = time_delays
        self._ta_map = np.zeros((len(time_delays), len(wavelengths)))

        self._update_display()
        self.info_label.setText(
            f"Wavelengths: {len(wavelengths)}, Time points: {len(time_delays)}"
        )

    def update_row(self, time_index: int, od_spectrum: np.ndarray):
        """Update a single row (time point) in the map.

        Args:
            time_index: Index of the time point.
            od_spectrum: OD spectrum at this time point.
        """
        if self._ta_map is None:
            return

        if time_index < len(self._time_delays):
            self._ta_map[time_index, :] = od_spectrum
            self._update_display()

    def set_map_data(
        self,
        wavelengths: np.ndarray,
        time_delays: np.ndarray,
        ta_map: np.ndarray,
    ):
        """Set complete map data.

        Args:
            wavelengths: Array of wavelength values.
            time_delays: Array of time delay values.
            ta_map: 2D array of OD values.
        """
        self._wavelengths = wavelengths
        self._time_delays = time_delays
        self._ta_map = ta_map

        self._update_display()
        self.info_label.setText(
            f"Wavelengths: {len(wavelengths)}, Time points: {len(time_delays)}"
        )

    def _update_display(self):
        """Update the image display."""
        if self._ta_map is None:
            return

        # Calculate transform to show proper axes
        wl_min = self._wavelengths[0]
        wl_max = self._wavelengths[-1]
        t_min = self._time_delays[0]
        t_max = self._time_delays[-1]

        n_wl = len(self._wavelengths)
        n_t = len(self._time_delays)

        # Scale factors
        wl_scale = (wl_max - wl_min) / n_wl if n_wl > 1 else 1
        t_scale = (t_max - t_min) / n_t if n_t > 1 else 1

        # Set image with transform
        self.image_view.setImage(
            self._ta_map.T,  # Transpose for correct orientation
            pos=[wl_min, t_min],
            scale=[wl_scale, t_scale],
            autoRange=False,
            autoLevels=False,
        )

        # Center colorscale at zero
        abs_max = np.abs(self._ta_map).max()
        if abs_max > 0:
            self.image_view.setLevels(-abs_max, abs_max)
        else:
            self.image_view.setLevels(-0.1, 0.1)

        # Auto-range to fit the data in the view
        self.image_view.getView().autoRange()

    def _on_mouse_clicked(self, event):
        """Handle mouse click on the image."""
        if self._wavelengths is None or self._ta_map is None:
            return

        pos = event.scenePos()
        view_pos = self.image_view.getView().mapSceneToView(pos)

        wavelength = view_pos.x()
        time_delay = view_pos.y()

        # Check bounds
        if (
            self._wavelengths[0] <= wavelength <= self._wavelengths[-1]
            and self._time_delays[0] <= time_delay <= self._time_delays[-1]
        ):
            self.point_clicked.emit(wavelength, time_delay)

    def get_map_data(self):
        """Return current map data.

        Returns:
            Tuple of (wavelengths, time_delays, ta_map) or None if no data.
        """
        if self._ta_map is None:
            return None
        return self._wavelengths, self._time_delays, self._ta_map

    def clear(self):
        """Clear the map data."""
        self._wavelengths = None
        self._time_delays = None
        self._ta_map = None
        self.image_view.clear()
        self.info_label.setText("No data")

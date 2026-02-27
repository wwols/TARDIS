"""Simulated spectrometer for generating realistic CCD spectra."""

import numpy as np
from typing import Tuple


class SimulatedSpectrometer:
    """Generates simulated CCD spectra with realistic noise characteristics."""

    def __init__(
        self,
        wavelength_min: float = 400.0,
        wavelength_max: float = 800.0,
        num_pixels: int = 2048,
    ):
        """Initialize the simulated spectrometer.

        Args:
            wavelength_min: Minimum wavelength in nm.
            wavelength_max: Maximum wavelength in nm.
            num_pixels: Number of CCD pixels.
        """
        self.wavelength_min = wavelength_min
        self.wavelength_max = wavelength_max
        self.num_pixels = num_pixels
        self._wavelengths = np.linspace(
            wavelength_min, wavelength_max, num_pixels
        )
        self._baseline_drift = 0.0
        self._drift_velocity = 0.0

    @property
    def wavelengths(self) -> np.ndarray:
        """Return the wavelength array."""
        return self._wavelengths.copy()

    def set_wavelength_range(self, wl_min: float, wl_max: float) -> None:
        """Update the wavelength range."""
        self.wavelength_min = wl_min
        self.wavelength_max = wl_max
        self._wavelengths = np.linspace(wl_min, wl_max, self.num_pixels)

    def _lamp_spectrum(self) -> np.ndarray:
        """Generate a realistic broadband lamp spectrum."""
        wl = self._wavelengths
        # Blackbody-like spectrum with some structure
        intensity = 1e4 * (wl / 500) ** (-3) * np.exp(-((wl - 600) ** 2) / (2 * 200**2))
        # Add some lamp emission lines
        intensity += 500 * np.exp(-((wl - 486) ** 2) / (2 * 2**2))  # H-beta
        intensity += 800 * np.exp(-((wl - 656) ** 2) / (2 * 2**2))  # H-alpha
        # Normalize to reasonable counts
        intensity = intensity / intensity.max() * 50000
        return intensity

    def _add_noise(
        self, spectrum: np.ndarray, integration_time_ms: float
    ) -> np.ndarray:
        """Add realistic noise to the spectrum.

        Args:
            spectrum: Clean spectrum.
            integration_time_ms: Integration time in milliseconds.

        Returns:
            Spectrum with noise added.
        """
        # Scale factor based on integration time
        scale = np.sqrt(integration_time_ms / 100.0)

        # Shot noise (Poisson)
        shot_noise = np.sqrt(np.abs(spectrum)) * np.random.randn(len(spectrum)) / scale

        # Readout noise (constant)
        readout_noise = 10 * np.random.randn(len(spectrum))

        # Dark current (small, integration time dependent)
        dark_current = 0.01 * integration_time_ms * np.random.randn(len(spectrum))

        return spectrum + shot_noise + readout_noise + dark_current

    def _update_baseline_drift(self) -> None:
        """Update slow baseline drift."""
        # Random walk for baseline
        self._drift_velocity += 0.1 * np.random.randn()
        self._drift_velocity *= 0.95  # Damping
        self._baseline_drift += self._drift_velocity
        self._baseline_drift *= 0.99  # Slow return to zero

    def acquire_spectrum(
        self, integration_time_ms: float = 100.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Acquire a single spectrum.

        Args:
            integration_time_ms: Integration time in milliseconds.

        Returns:
            Tuple of (wavelengths, intensities).
        """
        self._update_baseline_drift()

        spectrum = self._lamp_spectrum()
        # Add baseline variation
        spectrum += self._baseline_drift * 100

        # Add noise
        spectrum = self._add_noise(spectrum, integration_time_ms)

        # Ensure non-negative
        spectrum = np.maximum(spectrum, 0)

        return self._wavelengths.copy(), spectrum

    def acquire_reference_signal_pair(
        self,
        integration_time_ms: float = 100.0,
        pump_effect: np.ndarray | None = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Acquire a reference and signal spectrum pair.

        Args:
            integration_time_ms: Integration time in milliseconds.
            pump_effect: Multiplicative pump-induced change (1 = no change).

        Returns:
            Tuple of (wavelengths, reference, signal).
        """
        _, reference = self.acquire_spectrum(integration_time_ms)

        # Signal is reference modified by pump
        signal = reference.copy()
        if pump_effect is not None:
            signal = signal * pump_effect

        # Add independent noise to signal
        signal = self._add_noise(signal, integration_time_ms)
        signal = np.maximum(signal, 0)

        return self._wavelengths.copy(), reference, signal

"""Transient absorption physics model for simulation."""

import numpy as np
from typing import List, Tuple
from scipy.special import erf


class TransientAbsorptionModel:
    """Simulates transient absorption spectra with realistic physics."""

    def __init__(self, wavelengths: np.ndarray):
        """Initialize the TA model.

        Args:
            wavelengths: Array of wavelength values in nm.
        """
        self.wavelengths = wavelengths

        # Default spectral features
        self.features = [
            # (type, center_wl, width, amplitude, lifetimes)
            # GSB - Ground State Bleach (negative ΔOD)
            {"type": "GSB", "center": 520, "width": 30, "amplitude": 0.05, "tau": [1.0, 10.0, 100.0]},
            # SE - Stimulated Emission (negative ΔOD)
            {"type": "SE", "center": 580, "width": 40, "amplitude": 0.03, "tau": [1.0, 50.0]},
            # ESA - Excited State Absorption (positive ΔOD)
            {"type": "ESA", "center": 480, "width": 35, "amplitude": 0.02, "tau": [2.0, 20.0]},
            # ESA - Another ESA feature
            {"type": "ESA", "center": 650, "width": 50, "amplitude": 0.015, "tau": [5.0, 80.0]},
        ]

        # Instrument response function width (ps)
        self.irf_width = 0.15

    def _gaussian(self, x: np.ndarray, center: float, width: float) -> np.ndarray:
        """Generate a Gaussian lineshape."""
        return np.exp(-((x - center) ** 2) / (2 * width**2))

    def _multi_exponential_decay(
        self, time: float, lifetimes: List[float]
    ) -> float:
        """Calculate multi-exponential decay with equal amplitudes.

        Args:
            time: Time delay in ps.
            lifetimes: List of decay lifetimes in ps.

        Returns:
            Decay amplitude (0 to 1).
        """
        if time < 0:
            # Before time zero - small pre-pulse artifact
            return 0.01 * np.exp(time / 0.5)

        # Convolve with IRF (approximate with error function rise)
        rise = 0.5 * (1 + erf(time / (self.irf_width * np.sqrt(2))))

        # Multi-exponential decay
        decay = sum(np.exp(-time / tau) for tau in lifetimes) / len(lifetimes)

        return rise * decay

    def get_delta_od(
        self, time_delay: float, noise_level: float = 0.001
    ) -> np.ndarray:
        """Calculate ΔOD spectrum at a given time delay.

        Args:
            time_delay: Time delay in picoseconds.
            noise_level: Standard deviation of noise to add.

        Returns:
            Array of ΔOD values at each wavelength.
        """
        delta_od = np.zeros_like(self.wavelengths)

        for feature in self.features:
            # Spectral shape
            spectrum = self._gaussian(
                self.wavelengths, feature["center"], feature["width"]
            )

            # Temporal decay
            decay = self._multi_exponential_decay(time_delay, feature["tau"])

            # Sign depends on feature type
            sign = -1 if feature["type"] in ["GSB", "SE"] else 1

            delta_od += sign * feature["amplitude"] * spectrum * decay

        # Add noise
        if noise_level > 0:
            delta_od += noise_level * np.random.randn(len(delta_od))

        return delta_od

    def get_pump_effect(
        self, time_delay: float, noise_level: float = 0.001
    ) -> np.ndarray:
        """Calculate the pump-induced transmission change.

        This returns the multiplicative factor: Signal = Reference * pump_effect

        Args:
            time_delay: Time delay in picoseconds.
            noise_level: Noise level for ΔOD calculation.

        Returns:
            Array of multiplicative factors (close to 1).
        """
        delta_od = self.get_delta_od(time_delay, noise_level)
        # ΔOD = -log10(Signal/Reference)
        # Signal/Reference = 10^(-ΔOD)
        return 10 ** (-delta_od)

    def generate_ta_map(
        self,
        time_delays: np.ndarray,
        noise_level: float = 0.001,
        progress_callback=None,
    ) -> np.ndarray:
        """Generate a complete 2D TA map.

        Args:
            time_delays: Array of time delay values in ps.
            noise_level: Noise level for simulation.
            progress_callback: Optional callback(progress_fraction) for updates.

        Returns:
            2D array of shape (n_times, n_wavelengths) containing ΔOD values.
        """
        n_times = len(time_delays)
        n_wavelengths = len(self.wavelengths)
        ta_map = np.zeros((n_times, n_wavelengths))

        for i, t in enumerate(time_delays):
            ta_map[i, :] = self.get_delta_od(t, noise_level)
            if progress_callback is not None:
                progress_callback((i + 1) / n_times)

        return ta_map

    def set_feature(
        self,
        index: int,
        feature_type: str = None,
        center: float = None,
        width: float = None,
        amplitude: float = None,
        lifetimes: List[float] = None,
    ) -> None:
        """Modify an existing spectral feature.

        Args:
            index: Feature index.
            feature_type: "GSB", "SE", or "ESA".
            center: Center wavelength in nm.
            width: Spectral width in nm.
            amplitude: Peak ΔOD amplitude.
            lifetimes: List of decay lifetimes in ps.
        """
        if index >= len(self.features):
            return

        if feature_type is not None:
            self.features[index]["type"] = feature_type
        if center is not None:
            self.features[index]["center"] = center
        if width is not None:
            self.features[index]["width"] = width
        if amplitude is not None:
            self.features[index]["amplitude"] = amplitude
        if lifetimes is not None:
            self.features[index]["tau"] = lifetimes

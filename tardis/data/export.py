"""Data export functions for transient absorption data."""

import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def export_ascii(
    filepath: str,
    wavelengths: np.ndarray,
    time_delays: np.ndarray,
    ta_map: np.ndarray,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Export TA data to ASCII file.

    File format:
    - Header lines starting with #
    - First data row: wavelength values
    - Subsequent rows: time_delay followed by ΔOD values

    Args:
        filepath: Output file path.
        wavelengths: Array of wavelength values (nm).
        time_delays: Array of time delay values (ps).
        ta_map: 2D array of ΔOD values (n_times × n_wavelengths).
        metadata: Optional dictionary of metadata to include in header.
    """
    path = Path(filepath)

    with open(path, "w") as f:
        # Write header
        f.write("# TARDIS Transient Absorption Data\n")
        f.write(f"# Date: {datetime.now().isoformat()}\n")
        f.write(f"# Number of wavelengths: {len(wavelengths)}\n")
        f.write(f"# Number of time delays: {len(time_delays)}\n")
        f.write(f"# Wavelength range: {wavelengths[0]:.2f} - {wavelengths[-1]:.2f} nm\n")
        f.write(f"# Time delay range: {time_delays[0]:.3f} - {time_delays[-1]:.3f} ps\n")

        if metadata:
            f.write("#\n# Measurement Parameters:\n")
            for key, value in metadata.items():
                f.write(f"#   {key}: {value}\n")

        f.write("#\n")
        f.write("# Data format: First row = wavelengths (nm)\n")
        f.write("#              First column = time delays (ps)\n")
        f.write("#              Data values = ΔOD\n")
        f.write("#\n")

        # Write wavelength header row
        header_row = "Time(ps)\t" + "\t".join(f"{wl:.2f}" for wl in wavelengths)
        f.write(header_row + "\n")

        # Write data rows
        for i, t in enumerate(time_delays):
            row = f"{t:.4f}\t" + "\t".join(f"{od:.6e}" for od in ta_map[i, :])
            f.write(row + "\n")


def export_image(
    filepath: str,
    wavelengths: np.ndarray,
    time_delays: np.ndarray,
    ta_map: np.ndarray,
    title: str = "Transient Absorption Spectrum",
    colormap: str = "RdBu_r",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    dpi: int = 300,
) -> None:
    """Export TA map as a publication-quality image.

    Args:
        filepath: Output file path (.png, .pdf, or .svg).
        wavelengths: Array of wavelength values (nm).
        time_delays: Array of time delay values (ps).
        ta_map: 2D array of ΔOD values.
        title: Plot title.
        colormap: Matplotlib colormap name.
        vmin: Minimum value for colorscale.
        vmax: Maximum value for colorscale.
        dpi: Resolution for raster formats.
    """
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    # Determine symmetric colorscale if not specified
    if vmin is None or vmax is None:
        abs_max = np.abs(ta_map).max()
        vmin = -abs_max
        vmax = abs_max

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create mesh for pcolormesh
    wl_edges = _calculate_edges(wavelengths)
    t_edges = _calculate_edges(time_delays)

    # Use diverging normalization centered at zero
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

    im = ax.pcolormesh(
        wl_edges, t_edges, ta_map,
        cmap=colormap,
        norm=norm,
        shading="flat",
    )

    ax.set_xlabel("Wavelength (nm)", fontsize=12)
    ax.set_ylabel("Time Delay (ps)", fontsize=12)
    ax.set_title(title, fontsize=14)

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax, label="ΔOD")

    # Use log scale for time axis if data spans multiple decades
    time_range = time_delays[-1] - time_delays[0]
    if time_range > 100 and time_delays[0] > 0:
        ax.set_yscale("log")

    plt.tight_layout()
    plt.savefig(filepath, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def _calculate_edges(centers: np.ndarray) -> np.ndarray:
    """Calculate bin edges from bin centers.

    Args:
        centers: Array of bin center values.

    Returns:
        Array of bin edge values (length = len(centers) + 1).
    """
    edges = np.zeros(len(centers) + 1)
    # Interior edges are midpoints
    edges[1:-1] = (centers[:-1] + centers[1:]) / 2
    # Exterior edges extrapolate
    edges[0] = centers[0] - (centers[1] - centers[0]) / 2
    edges[-1] = centers[-1] + (centers[-1] - centers[-2]) / 2
    return edges


def load_ascii(filepath: str) -> Dict[str, Any]:
    """Load TA data from ASCII file.

    Args:
        filepath: Input file path.

    Returns:
        Dictionary with keys: 'wavelengths', 'time_delays', 'ta_map', 'metadata'.
    """
    path = Path(filepath)
    metadata = {}
    data_lines = []

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                # Parse metadata
                if ":" in line:
                    key_value = line[1:].strip()
                    if key_value.startswith(" "):
                        # Indented metadata
                        parts = key_value.strip().split(":", 1)
                        if len(parts) == 2:
                            metadata[parts[0].strip()] = parts[1].strip()
            elif line:
                data_lines.append(line)

    # Parse header row (wavelengths)
    header_parts = data_lines[0].split("\t")
    wavelengths = np.array([float(x) for x in header_parts[1:]])

    # Parse data rows
    time_delays = []
    ta_data = []
    for line in data_lines[1:]:
        parts = line.split("\t")
        time_delays.append(float(parts[0]))
        ta_data.append([float(x) for x in parts[1:]])

    return {
        "wavelengths": wavelengths,
        "time_delays": np.array(time_delays),
        "ta_map": np.array(ta_data),
        "metadata": metadata,
    }

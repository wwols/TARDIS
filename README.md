# TARDIS

**T**ransient **A**bsorption **R**adiation **D**etection and **I**maging **S**ystem

A PyQt6-based GUI for controlling and simulating transient absorption spectroscopy measurements with real-time spectral displays.

## Features

- **Live Spectra Display**: Real-time visualization of reference and signal spectra with optical density calculation
- **Delay Stage Control**: Precise positioning with configurable step sizes and time zero functionality
- **Measurement Automation**: Automated scanning with progress tracking and time estimates
- **2D TA Map**: Interactive wavelength × time heatmap with diverging colorscale
- **Data Export**: ASCII export with metadata and publication-quality image export (PNG/PDF/SVG)
- **Realistic Simulation**: Physics-based transient absorption model with:
  - Ground state bleach (GSB)
  - Excited state absorption (ESA)
  - Stimulated emission (SE)
  - Multi-exponential decay kinetics
  - Realistic detector noise

## Installation

```bash
# Clone the repository
git clone git@github.com:wwols/TARDIS.git
cd TARDIS

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt
```

## Usage

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the application
python main.py
```

### Quick Start

1. **Live Mode**: The application starts in live mode, displaying simulated spectra updating in real-time
2. **Adjust Delay**: Use the delay stage controls to move through different time delays
3. **Run Measurement**: Set scan parameters (start/end delay, step size, averages) and click START
4. **View Results**: Watch the 2D TA map populate as the measurement progresses
5. **Export Data**: Save your data as ASCII or export publication-ready figures

## Project Structure

```
TARDIS/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── tardis/
│   ├── gui/
│   │   ├── main_window.py      # Main application window
│   │   ├── live_view.py        # Live spectra display
│   │   ├── delay_stage.py      # Delay stage controls
│   │   ├── measurement.py      # Measurement widget & worker thread
│   │   ├── map_view.py         # 2D TA map visualization
│   │   └── dialogs.py          # Save dialogs
│   ├── simulation/
│   │   ├── spectra.py          # Simulated spectrometer
│   │   └── ta_model.py         # Transient absorption physics model
│   └── data/
│       └── export.py           # Data export functions
```

## Requirements

- Python 3.10+
- PyQt6
- pyqtgraph
- NumPy
- SciPy
- Matplotlib

## Author

**Weronika W. Wolszczak** (2026)

## License

MIT License

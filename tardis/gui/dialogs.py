"""Save dialogs for data and image export."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QFileDialog, QGroupBox, QCheckBox,
    QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal


class SaveDataDialog(QDialog):
    """Dialog for saving TA data to ASCII file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Data")
        self.setMinimumWidth(400)

        self._filepath = ""
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("File:"))

        self.filepath_edit = QLineEdit()
        self.filepath_edit.setPlaceholderText("Select output file...")
        file_layout.addWidget(self.filepath_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(browse_btn)

        layout.addLayout(file_layout)

        # Metadata
        meta_group = QGroupBox("Metadata (optional)")
        meta_layout = QFormLayout(meta_group)

        self.sample_edit = QLineEdit()
        meta_layout.addRow("Sample:", self.sample_edit)

        self.solvent_edit = QLineEdit()
        meta_layout.addRow("Solvent:", self.solvent_edit)

        self.excitation_edit = QLineEdit()
        self.excitation_edit.setPlaceholderText("e.g., 400 nm, 1 uJ/pulse")
        meta_layout.addRow("Excitation:", self.excitation_edit)

        self.notes_edit = QLineEdit()
        meta_layout.addRow("Notes:", self.notes_edit)

        layout.addWidget(meta_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_browse(self):
        """Handle browse button click."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save TA Data",
            "",
            "Text files (*.txt);;CSV files (*.csv);;All files (*)",
        )
        if filepath:
            self._filepath = filepath
            self.filepath_edit.setText(filepath)

    def get_filepath(self) -> str:
        """Return the selected file path."""
        return self.filepath_edit.text()

    def get_metadata(self) -> dict:
        """Return metadata dictionary."""
        metadata = {}
        if self.sample_edit.text():
            metadata["Sample"] = self.sample_edit.text()
        if self.solvent_edit.text():
            metadata["Solvent"] = self.solvent_edit.text()
        if self.excitation_edit.text():
            metadata["Excitation"] = self.excitation_edit.text()
        if self.notes_edit.text():
            metadata["Notes"] = self.notes_edit.text()
        return metadata


class SaveImageDialog(QDialog):
    """Dialog for saving TA map as image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Image")
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("File:"))

        self.filepath_edit = QLineEdit()
        self.filepath_edit.setPlaceholderText("Select output file...")
        file_layout.addWidget(self.filepath_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(browse_btn)

        layout.addLayout(file_layout)

        # Format options
        format_group = QGroupBox("Format Options")
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "PDF", "SVG"])
        format_layout.addRow("Format:", self.format_combo)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        format_layout.addRow("DPI:", self.dpi_spin)

        layout.addWidget(format_group)

        # Plot options
        plot_group = QGroupBox("Plot Options")
        plot_layout = QFormLayout(plot_group)

        self.title_edit = QLineEdit()
        self.title_edit.setText("Transient Absorption Spectrum")
        plot_layout.addRow("Title:", self.title_edit)

        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            "RdBu_r", "seismic", "coolwarm", "bwr", "PiYG", "PRGn"
        ])
        plot_layout.addRow("Colormap:", self.colormap_combo)

        # Color scale limits
        scale_layout = QHBoxLayout()

        self.auto_scale_check = QCheckBox("Auto")
        self.auto_scale_check.setChecked(True)
        self.auto_scale_check.stateChanged.connect(self._on_auto_scale_changed)
        scale_layout.addWidget(self.auto_scale_check)

        scale_layout.addWidget(QLabel("Min:"))
        self.vmin_spin = QDoubleSpinBox()
        self.vmin_spin.setRange(-10, 10)
        self.vmin_spin.setDecimals(4)
        self.vmin_spin.setValue(-0.1)
        self.vmin_spin.setEnabled(False)
        scale_layout.addWidget(self.vmin_spin)

        scale_layout.addWidget(QLabel("Max:"))
        self.vmax_spin = QDoubleSpinBox()
        self.vmax_spin.setRange(-10, 10)
        self.vmax_spin.setDecimals(4)
        self.vmax_spin.setValue(0.1)
        self.vmax_spin.setEnabled(False)
        scale_layout.addWidget(self.vmax_spin)

        plot_layout.addRow("Color scale:", scale_layout)

        layout.addWidget(plot_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_browse(self):
        """Handle browse button click."""
        format_ext = self.format_combo.currentText().lower()
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save TA Image",
            "",
            f"{self.format_combo.currentText()} files (*.{format_ext});;All files (*)",
        )
        if filepath:
            # Ensure correct extension
            if not filepath.lower().endswith(f".{format_ext}"):
                filepath += f".{format_ext}"
            self.filepath_edit.setText(filepath)

    def _on_auto_scale_changed(self, state):
        """Handle auto scale checkbox change."""
        enabled = not bool(state)
        self.vmin_spin.setEnabled(enabled)
        self.vmax_spin.setEnabled(enabled)

    def get_filepath(self) -> str:
        """Return the selected file path."""
        return self.filepath_edit.text()

    def get_options(self) -> dict:
        """Return export options dictionary."""
        options = {
            "title": self.title_edit.text(),
            "colormap": self.colormap_combo.currentText(),
            "dpi": self.dpi_spin.value(),
        }

        if not self.auto_scale_check.isChecked():
            options["vmin"] = self.vmin_spin.value()
            options["vmax"] = self.vmax_spin.value()

        return options

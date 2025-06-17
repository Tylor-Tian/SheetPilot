"""Data import window."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QComboBox, QTableView, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QAbstractTableModel, Qt
import pandas as pd
from pathlib import Path

from modules.file_parser import parse_file


class DataFrameModel(QAbstractTableModel):
    """Table model for displaying DataFrame preview."""
    
    def __init__(self, df=None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()
        
    def rowCount(self, parent=None):
        return min(len(self._df), 100)  # Show first 100 rows
        
    def columnCount(self, parent=None):
        return len(self._df.columns)
        
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            value = self._df.iloc[index.row(), index.column()]
            return str(value)
        return None
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            else:
                return str(self._df.index[section])
        return None
        
    def update_data(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()


class ImportWindow(QWidget):
    """Window for importing data files."""
    
    data_imported = pyqtSignal(pd.DataFrame)
    
    def __init__(self):
        super().__init__()
        self.df = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the import window UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Data Import</h2>")
        layout.addWidget(title)
        
        # File selection
        file_layout = QHBoxLayout()
        
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Select a file...")
        file_layout.addWidget(self.file_path)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Auto", "CSV", "TSV", "Excel", "JSON"])
        format_layout.addWidget(self.format_combo)
        
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Import/Preview buttons
        button_layout = QHBoxLayout()
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self.preview_file)
        button_layout.addWidget(preview_btn)
        
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_file)
        button_layout.addWidget(import_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Preview table
        self.preview_table = QTableView()
        self.table_model = DataFrameModel()
        self.preview_table.setModel(self.table_model)
        layout.addWidget(self.preview_table)
        
    def browse_file(self):
        """Open file browser dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "All Supported (*.csv *.tsv *.txt *.json *.xls *.xlsx *.xlsm *.ods);;CSV Files (*.csv);;TSV Files (*.tsv);;Excel Files (*.xls *.xlsx *.xlsm *.ods);;JSON Files (*.json)"
        )
        
        if file_path:
            self.file_path.setText(file_path)
            
    def get_format(self):
        """Get selected format or None for auto-detect."""
        format_text = self.format_combo.currentText()
        if format_text == "Auto":
            return None
        return format_text.lower()
        
    def preview_file(self):
        """Preview the selected file."""
        file_path = self.file_path.text()
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please select a file")
            return
            
        try:
            df = parse_file(file_path, file_format=self.get_format())
            self.df = df
            self.table_model.update_data(df)
            
            # Show info
            QMessageBox.information(
                self, 
                "File Preview",
                f"Loaded {len(df)} rows and {len(df.columns)} columns"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            
    def import_file(self):
        """Import the file and emit signal."""
        if self.df is None:
            self.preview_file()
            
        if self.df is not None:
            self.data_imported.emit(self.df)

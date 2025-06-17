"""Cleaning report window."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableView, QTextEdit, QLabel, QFileDialog, QMessageBox,
    QSplitter
)
from PyQt5.QtCore import Qt
import pandas as pd

from .import_window import DataFrameModel


class ReportWindow(QWidget):
    """Window for displaying cleaning results and report."""
    
    def __init__(self):
        super().__init__()
        self.df = None
        self.report = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the report window UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Cleaning Report</h2>")
        layout.addWidget(title)
        
        # Create splitter for table and log
        splitter = QSplitter(Qt.Vertical)
        
        # Cleaned data table
        self.data_table = QTableView()
        self.table_model = DataFrameModel()
        self.data_table.setModel(self.table_model)
        splitter.addWidget(self.data_table)
        
        # Log panel
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        splitter.addWidget(self.log_text)
        
        # Set initial sizes
        splitter.setSizes([400, 200])
        
        layout.addWidget(splitter)
        
        # Export buttons
        button_layout = QHBoxLayout()
        
        export_data_btn = QPushButton("Export Data")
        export_data_btn.clicked.connect(self.export_data)
        button_layout.addWidget(export_data_btn)
        
        save_report_btn = QPushButton("Save Report")
        save_report_btn.clicked.connect(self.save_report)
        button_layout.addWidget(save_report_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
    def set_results(self, df: pd.DataFrame, report):
        """Set the cleaning results."""
        self.df = df
        self.report = report
        
        # Update table
        self.table_model.update_data(df)
        
        # Generate report text
        report_text = self.generate_report_text(report)
        self.log_text.setPlainText(report_text)
        
    def generate_report_text(self, report):
        """Generate human-readable report text."""
        lines = []
        lines.append("=== Cleaning Report ===\n")
        
        lines.append(f"Steps completed: {len(report.steps_completed)}")
        for step in report.steps_completed:
            lines.append(f"  ✓ {step}")
            
        if report.errors:
            lines.append(f"\nErrors encountered: {len(report.errors)}")
            for error in report.errors:
                lines.append(f"  ✗ {error['module']}: {error['error']}")
                
        lines.append("\n=== Statistics ===")
        for module, stats in report.stats.items():
            lines.append(f"\n{module}:")
            for key, value in stats.items():
                lines.append(f"  {key}: {value}")
                
        if self.df is not None:
            lines.append(f"\n=== Result Summary ===")
            lines.append(f"Rows: {len(self.df)}")
            lines.append(f"Columns: {len(self.df.columns)}")
            lines.append(f"Memory usage: {self.df.memory_usage().sum() / 1024**2:.2f} MB")
            
        return "\n".join(lines)
        
    def export_data(self):
        """Export cleaned data to file."""
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data to export")
            return
            
        file_path, file_type = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*.*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.xlsx'):
                    self.df.to_excel(file_path, index=False)
                else:
                    self.df.to_csv(file_path, index=False)
                    
                QMessageBox.information(
                    self,
                    "Success",
                    f"Data exported to {file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to export data: {str(e)}"
                )
                
    def save_report(self):
        """Save report to text file."""
        if self.report is None:
            QMessageBox.warning(self, "Warning", "No report to save")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.log_text.toPlainText())
                    
                QMessageBox.information(
                    self,
                    "Success",
                    f"Report saved to {file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save report: {str(e)}"
                )

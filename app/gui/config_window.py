"""Cleaning configuration window."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QComboBox, QListWidget, QStackedWidget, QLabel, QSpinBox,
    QDoubleSpinBox, QLineEdit, QTextEdit, QMessageBox, QProgressBar,
    QListWidgetItem, QGroupBox, QAbstractItemView
)
from PyQt5.QtCore import pyqtSignal, Qt, QThread
import pandas as pd
import warnings

from app.core.orchestrator import Orchestrator, ModuleConfig
from app.core.module_registry import ModuleRegistry


class CleaningThread(QThread):
    """Thread for running cleaning operations."""
    
    progress = pyqtSignal(str)
    completed = pyqtSignal(pd.DataFrame, object)
    error = pyqtSignal(str)
    
    def __init__(self, df, steps, current_user=None): # Added current_user
        super().__init__()
        self.df = df
        self.steps = steps
        self.current_user = current_user # Store current_user
        
    def run(self):
        """Run the cleaning pipeline."""
        try:
            orchestrator = Orchestrator()
            # Pass current_user to run_pipeline
            cleaned_df, report = orchestrator.run_pipeline(self.df, self.steps, current_user=self.current_user)
            self.completed.emit(cleaned_df, report)
        except Exception as e:
            self.error.emit(str(e))


class ConfigWindow(QWidget):
    """Window for configuring cleaning operations."""
    
    cleaning_completed = pyqtSignal(pd.DataFrame, object)
    
    def __init__(self, current_user: dict = None): # Added current_user
        super().__init__()
        self.current_user = current_user # Store current_user
        self.df = None
        self.registry = ModuleRegistry()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the configuration UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Cleaning Configuration</h2>")
        layout.addWidget(title)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left: Module selection
        module_group = QGroupBox("Modules")
        module_layout = QVBoxLayout(module_group)
        
        self.module_list = QListWidget()
        self.module_list.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Add available modules
        self.module_configs = {}
        for name in ["missing_imputer", "text_normalizer", "outlier_detector"]:
            item = QListWidgetItem(name.replace("_", " ").title())
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, name)
            self.module_list.addItem(item)
            self.module_configs[name] = {}
            
        self.module_list.itemSelectionChanged.connect(self.on_module_selected)
        module_layout.addWidget(self.module_list)
        
        content_layout.addWidget(module_group, 1)
        
        # Right: Module configuration
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        
        self.config_stack = QStackedWidget()
        
        # Create config panels
        self.create_imputer_panel()
        self.create_normalizer_panel()
        self.create_detector_panel()
        
        config_layout.addWidget(self.config_stack)
        content_layout.addWidget(config_group, 2)
        
        layout.addLayout(content_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Run button
        self.run_button = QPushButton("Run Cleaning")
        self.run_button.clicked.connect(self.run_cleaning)
        layout.addWidget(self.run_button)
        
    def create_imputer_panel(self):
        """Create missing value imputer configuration panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Column selection
        layout.addWidget(QLabel("Columns:"))
        self.imputer_columns = QListWidget()
        self.imputer_columns.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.imputer_columns)
        
        # Method selection
        layout.addWidget(QLabel("Method:"))
        self.imputer_method = QComboBox()
        self.imputer_method.addItems(["mean", "median", "mode", "knn", "constant"])
        self.imputer_method.currentTextChanged.connect(self.on_imputer_method_changed)
        layout.addWidget(self.imputer_method)
        
        # Method-specific options
        self.imputer_options = QStackedWidget()
        
        # KNN options
        knn_widget = QWidget()
        knn_layout = QVBoxLayout(knn_widget)
        knn_layout.addWidget(QLabel("Number of neighbors:"))
        self.knn_neighbors = QSpinBox()
        self.knn_neighbors.setRange(1, 20)
        self.knn_neighbors.setValue(5)
        knn_layout.addWidget(self.knn_neighbors)
        self.imputer_options.addWidget(knn_widget)
        
        # Constant options
        const_widget = QWidget()
        const_layout = QVBoxLayout(const_widget)
        const_layout.addWidget(QLabel("Fill value:"))
        self.const_value = QLineEdit("0")
        const_layout.addWidget(self.const_value)
        self.imputer_options.addWidget(const_widget)
        
        layout.addWidget(self.imputer_options)
        layout.addStretch()
        
        self.config_stack.addWidget(panel)
        
    def create_normalizer_panel(self):
        """Create text normalizer configuration panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Column selection
        layout.addWidget(QLabel("Text columns:"))
        self.normalizer_columns = QListWidget()
        self.normalizer_columns.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.normalizer_columns)
        
        # Options
        self.lowercase_check = QCheckBox("Convert to lowercase")
        self.lowercase_check.setChecked(True)
        layout.addWidget(self.lowercase_check)
        
        self.remove_punct_check = QCheckBox("Remove punctuation")
        self.remove_punct_check.setChecked(True)
        layout.addWidget(self.remove_punct_check)
        
        self.remove_stopwords_check = QCheckBox("Remove stopwords")
        layout.addWidget(self.remove_stopwords_check)
        
        layout.addStretch()
        
        self.config_stack.addWidget(panel)
        
    def create_detector_panel(self):
        """Create outlier detector configuration panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Column selection
        layout.addWidget(QLabel("Numeric columns:"))
        self.detector_columns = QListWidget()
        self.detector_columns.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.detector_columns)
        
        # Method selection
        layout.addWidget(QLabel("Method:"))
        self.detector_method = QComboBox()
        self.detector_method.addItems(["iqr", "zscore", "isolation", "lof"])
        layout.addWidget(self.detector_method)
        
        # Threshold
        layout.addWidget(QLabel("Threshold:"))
        self.detector_threshold = QDoubleSpinBox()
        self.detector_threshold.setRange(0.01, 10.0)
        self.detector_threshold.setValue(1.5)
        self.detector_threshold.setSingleStep(0.1)
        layout.addWidget(self.detector_threshold)
        
        # Action
        layout.addWidget(QLabel("Action:"))
        self.detector_action = QComboBox()
        self.detector_action.addItems(["remove", "flag"])
        layout.addWidget(self.detector_action)
        
        layout.addStretch()
        
        self.config_stack.addWidget(panel)
        
    def set_dataframe(self, df: pd.DataFrame):
        """Set the dataframe and update column lists."""
        self.df = df
        
        # Update column lists
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        # Imputer columns (all)
        self.imputer_columns.clear()
        self.imputer_columns.addItems(df.columns.tolist())
        
        # Normalizer columns (text only)
        self.normalizer_columns.clear()
        self.normalizer_columns.addItems(text_cols)
        
        # Detector columns (numeric only)
        self.detector_columns.clear()
        self.detector_columns.addItems(numeric_cols)
        
    def on_module_selected(self):
        """Handle module selection change."""
        current_item = self.module_list.currentItem()
        if current_item:
            module_name = current_item.data(Qt.UserRole)
            
            # Show appropriate config panel
            if module_name == "missing_imputer":
                self.config_stack.setCurrentIndex(0)
            elif module_name == "text_normalizer":
                self.config_stack.setCurrentIndex(1)
            elif module_name == "outlier_detector":
                self.config_stack.setCurrentIndex(2)
                
    def on_imputer_method_changed(self, method):
        """Handle imputer method change."""
        if method == "knn":
            self.imputer_options.setCurrentIndex(0)
            self.imputer_options.setVisible(True)
        elif method == "constant":
            self.imputer_options.setCurrentIndex(1)
            self.imputer_options.setVisible(True)
        else:
            self.imputer_options.setVisible(False)
            
    def get_selected_columns(self, list_widget):
        """Get selected columns from a list widget."""
        selected = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.isSelected():
                selected.append(item.text())
        return selected
        
    def collect_configs(self):
        """Collect module configurations."""
        steps = []
        
        for i in range(self.module_list.count()):
            item = self.module_list.item(i)
            if item.checkState() == Qt.Checked:
                module_name = item.data(Qt.UserRole)
                
                if module_name == "missing_imputer":
                    from modules.missing_imputer import process
                    params = {
                        "columns": self.get_selected_columns(self.imputer_columns),
                        "method": self.imputer_method.currentText()
                    }
                    
                    if params["method"] == "knn":
                        params["n_neighbors"] = self.knn_neighbors.value()
                    elif params["method"] == "constant":
                        params["fill_value"] = self.const_value.text()
                        
                    steps.append(ModuleConfig(
                        name=module_name,
                        module_func=process,
                        params=params
                    ))
                    
                elif module_name == "text_normalizer":
                    from modules.text_normalizer import process
                    params = {
                        "columns": self.get_selected_columns(self.normalizer_columns),
                        "lowercase": self.lowercase_check.isChecked(),
                        "remove_punct": self.remove_punct_check.isChecked(),
                        "remove_stopwords": self.remove_stopwords_check.isChecked()
                    }
                    
                    steps.append(ModuleConfig(
                        name=module_name,
                        module_func=process,
                        params=params
                    ))
                    
                elif module_name == "outlier_detector":
                    from modules.outlier_detector import process
                    params = {
                        "columns": self.get_selected_columns(self.detector_columns),
                        "method": self.detector_method.currentText(),
                        "threshold": self.detector_threshold.value(),
                        "action": self.detector_action.currentText()
                    }
                    
                    steps.append(ModuleConfig(
                        name=module_name,
                        module_func=process,
                        params=params
                    ))
                    
        return steps
        
    def run_cleaning(self):
        """Run the cleaning pipeline."""
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data loaded")
            return
            
        steps = self.collect_configs()
        if not steps:
            QMessageBox.warning(self, "Warning", "No modules selected")
            return
            
        # Disable UI during processing
        self.run_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        # Run in thread, passing current_user to the thread
        self.cleaning_thread = CleaningThread(self.df, steps, current_user=self.current_user)
        self.cleaning_thread.completed.connect(self.on_cleaning_completed)
        self.cleaning_thread.error.connect(self.on_cleaning_error)
        self.cleaning_thread.start()
        
    def on_cleaning_completed(self, df, report):
        """Handle cleaning completion."""
        self.run_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.cleaning_completed.emit(df, report)
        
    def on_cleaning_error(self, error_msg):
        """Handle cleaning error."""
        self.run_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Error", f"Cleaning failed: {error_msg}")

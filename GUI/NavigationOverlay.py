from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class NavigationOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Small overlay in top-left corner
        self.setGeometry(10, 10, 110, 60)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 220); border-radius: 5px;")

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Add text
        self.label = QLabel("Route calculated")
        self.instruction = QLabel("Middle: Start\nLower: Cancel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add to layout
        layout.addWidget(self.label)
        layout.addWidget(self.instruction)

        # Hide initially
        self.hide()
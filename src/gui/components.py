from PyQt6.QtWidgets import QLabel, QPushButton, QTextEdit
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt, pyqtSignal


class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, text, value, parent=None):
        super().__init__(text, parent)
        self.value = value
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.value)


class ThemeButton(QPushButton):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Prevent stealing focus
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border-radius: 12px;
                border: 2px solid #ffffff;
            }}
            QPushButton:hover {{
                border: 2px solid #d1d5db;
            }}
        """)


class UnscrollableTextEdit(QTextEdit):
    def wheelEvent(self, event):
        event.ignore()

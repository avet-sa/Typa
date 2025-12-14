import os
import json
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QFrame,
    QMenu,
)
from PyQt6.QtGui import QFont, QIcon, QKeyEvent, QAction, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from src.core.engine import TypingTestEngine
from src.gui.components import ClickableLabel, ThemeButton, UnscrollableTextEdit


class TypingTest(QWidget):
    results_ready = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.engine = TypingTestEngine()
        self.results_shown = False  # Track if results have been shown for current test

        self.current_theme = "#22c55e"  # Default green
        self.themes = {
            "Green": "#22c55e",
            "Blue": "#3b82f6",
            "Purple": "#a855f7",
            "Orange": "#f97316",
            "Pink": "#ec4899",
            "Red": "#ef4444",
            "Cyan": "#06b6d4",
            "Yellow": "#eab308",
        }

        self.load_config()  # Load saved theme

        self.setupUI()
        self.results_ready.connect(self.showResults)

        self.updatePromptDisplay()
        self.updateControlPanel()
        self.updateThemeColors()

        # Timer for live stats
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateLiveStats)
        self.timer.start(100)

    def load_config(self):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
                    self.current_theme = config.get("theme", "#22c55e")
                    self.engine.set_accent_color(self.current_theme)
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        try:
            config = {"theme": self.current_theme}
            with open("config.json", "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def setupUI(self):
        self.setWindowTitle("Typing Test")
        self.setWindowIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    ),
                    "assets",
                    "icon.ico",
                )
            )
        )
        self.setFixedSize(900, 500)
        self.setStyleSheet(
            "QWidget { background-color: #1e1e1e; color: #ffffff; font-family: 'Cascadia Mono'; }"
        )

        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(20)
        mainLayout.setContentsMargins(40, 40, 40, 40)  # Increased top margin

        # --- Top Bar (Controls + Theme) ---
        topBarLayout = QHBoxLayout()

        # Spacer to center the controls
        topBarLayout.addStretch()

        # --- Control Panel ---
        self.controlLayout = QHBoxLayout()

        # Mode Selectors
        self.modeContainer = QWidget()
        # self.modeContainer.setStyleSheet(".QWidget { background-color: rgba(255, 255, 255, 0.05); border-radius: 15px; }")
        self.modeLayout = QHBoxLayout(self.modeContainer)
        self.modeLayout.setContentsMargins(15, 5, 15, 5)
        self.modeLayout.setSpacing(10)

        self.modeLabels = {}
        self.setupModeSelector()
        self.controlLayout.addWidget(self.modeContainer)

        self.controlLayout.addSpacing(20)

        # Difficulty Selectors
        self.diffContainer = QWidget()
        # self.diffContainer.setStyleSheet(".QWidget { background-color: rgba(255, 255, 255, 0.05); border-radius: 15px; }")
        self.diffLayout = QHBoxLayout(self.diffContainer)
        self.diffLayout.setContentsMargins(15, 5, 15, 5)
        self.diffLayout.setSpacing(10)

        self.diffLabels = {}
        self.controlLayout.addWidget(self.diffContainer)

        topBarLayout.addLayout(self.controlLayout)
        topBarLayout.addStretch()

        # Theme Button
        self.themeBtn = ThemeButton(self.current_theme)
        self.themeBtn.clicked.connect(self.showThemeMenu)
        topBarLayout.addWidget(self.themeBtn)

        mainLayout.addLayout(topBarLayout)

        # --- Stacked Widget for Screens ---
        self.stackedWidget = QStackedWidget(self)
        self.setupTypingScreen()
        self.setupResultsScreen()

        self.stackedWidget.addWidget(self.typingScreen)
        self.stackedWidget.addWidget(self.resultsScreen)
        mainLayout.addWidget(self.stackedWidget)

    def setupModeSelector(self):
        modes = [("words", "words"), ("quotes", "quotes")]
        for i, (text, value) in enumerate(modes):
            lbl = ClickableLabel(text, value)
            lbl.clicked.connect(self.changeMode)
            lbl.setFont(QFont("Cascadia Mono", 12))
            self.modeLayout.addWidget(lbl)
            self.modeLabels[value] = lbl
            if i < len(modes) - 1:
                sep = QLabel("|")
                sep.setStyleSheet("color: #4b5563;")
                self.modeLayout.addWidget(sep)

    def setupDifficultySelector(self):
        # Clear existing
        while self.diffLayout.count():
            item = self.diffLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.diffLabels = {}

        if self.engine.mode == "words":
            options = ["10", "25", "50", "100"]
        else:
            options = ["short", "medium", "long"]

        for i, opt in enumerate(options):
            lbl = ClickableLabel(opt, opt)
            lbl.clicked.connect(self.changeDifficulty)
            lbl.setFont(QFont("Cascadia Mono", 12))
            self.diffLayout.addWidget(lbl)
            self.diffLabels[opt] = lbl
            if i < len(options) - 1:
                sep = QLabel("|")
                sep.setStyleSheet("color: #4b5563;")
                self.diffLayout.addWidget(sep)

    def createSeparator(self):
        # Not used anymore, using spacing and separate containers
        pass

    def setupTypingScreen(self):
        self.typingScreen = QWidget()
        layout = QVBoxLayout(self.typingScreen)
        layout.setSpacing(20)
        layout.setContentsMargins(100, 0, 100, 0)  # Constrain text width
        layout.addStretch()

        # Use QTextEdit for auto-scrolling support
        self.promptLabel = UnscrollableTextEdit()
        self.promptLabel.setReadOnly(True)
        self.promptLabel.setFrameShape(QFrame.Shape.NoFrame)
        self.promptLabel.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.promptLabel.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.promptLabel.setStyleSheet("background: transparent;")
        self.promptLabel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.promptLabel.setFont(QFont("Cascadia Mono", 18))
        self.promptLabel.setFixedHeight(
            170
        )  # Approx 4 lines (24px * 1.6 * 4 = 153.6px) + padding

        layout.addWidget(self.promptLabel)
        layout.addStretch()

        # Live stats
        self.statsLabel = QLabel()
        self.statsLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statsLabel.setFont(QFont("Cascadia Mono", 14, QFont.Weight.Bold))
        # Removed initial color stylesheet
        layout.addWidget(self.statsLabel)

        # Shortcut guide
        self.shortcutsLabel = QLabel()
        self.shortcutsLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.shortcutsLabel.setFont(QFont("Cascadia Mono", 10))
        layout.addWidget(self.shortcutsLabel)

    def setupResultsScreen(self):
        self.resultsScreen = QWidget()
        layout = QVBoxLayout(self.resultsScreen)
        layout.setSpacing(30)
        layout.addStretch()

        self.personalBest = QLabel()
        self.personalBest.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.personalBest.setFont(QFont("Cascadia Mono", 24, QFont.Weight.Bold))
        layout.addWidget(self.personalBest)

        self.accuracyLabel = QLabel()
        self.accuracyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.accuracyLabel.setFont(QFont("Cascadia Mono", 18, QFont.Weight.Bold))
        layout.addWidget(self.accuracyLabel)

        self.wpmLabel = QLabel()
        self.wpmLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wpmLabel.setFont(QFont("Cascadia Mono", 18, QFont.Weight.Bold))
        layout.addWidget(self.wpmLabel)

        layout.addStretch()

        self.resultsShortcutsLabel = QLabel()
        self.resultsShortcutsLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resultsShortcutsLabel.setFont(QFont("Cascadia Mono", 10))
        layout.addWidget(self.resultsShortcutsLabel)

    def showThemeMenu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4b5563;
            }
            QMenu::item {
                padding: 2px 0;
                width: 17px;
                height: 20px;
            }
            QMenu::item:selected {
                background-color: #4b5563;
            }
        """)

        for name, color in self.themes.items():
            # Create circular icon
            pixmap = QPixmap(22, 20)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 0, 20, 20)
            painter.end()

            action = QAction(self)
            action.setIcon(QIcon(pixmap))

            action.triggered.connect(lambda checked, c=color: self.applyTheme(c))
            menu.addAction(action)

        menu.exec(self.themeBtn.mapToGlobal(self.themeBtn.rect().bottomLeft()))

    def applyTheme(self, color):
        self.current_theme = color
        self.engine.set_accent_color(color)
        self.save_config()  # Save new theme

        # Update Theme Button
        self.themeBtn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border-radius: 12px;
                border: 2px solid #ffffff;
            }}
            QPushButton:hover {{
                border: 2px solid #d1d5db;
            }}
        """)

        self.updateThemeColors()
        self.updatePromptDisplay()  # Re-render text with new color

    def updateThemeColors(self):
        c = self.current_theme

        # Update Control Panel
        self.updateControlPanel()

        # Update Live Stats Color - Removed to allow HTML formatting
        # self.statsLabel.setStyleSheet(f"color: {c};")

        # Update Shortcuts
        self.shortcutsLabel.setText(
            f"<span style='color: {c};'>tab</span> <span style='color: #9ca3af;'>restart</span> &nbsp;&nbsp; "
            f"<span style='color: {c};'>esc</span> <span style='color: #9ca3af;'>quit</span>"
        )

        self.resultsShortcutsLabel.setText(
            f"<span style='color: {c};'>tab</span> <span style='color: #9ca3af;'>next test</span> &nbsp;&nbsp; "
            f"<span style='color: {c};'>esc</span> <span style='color: #9ca3af;'>quit</span>"
        )

    def changeMode(self, mode):
        if self.engine.mode != mode:
            self.engine.set_mode(mode)
            self.updateControlPanel()
            self.restart()

    def changeDifficulty(self, diff):
        if self.engine.difficulty != diff:
            self.engine.set_difficulty(diff)
            self.updateControlPanel()
            self.restart()

    def updateControlPanel(self):
        c = self.current_theme

        # Update Mode Labels
        for val, lbl in self.modeLabels.items():
            if val == self.engine.mode:
                lbl.setStyleSheet(f"color: {c}; font-weight: bold;")
            else:
                lbl.setStyleSheet("color: #6b7280; font-weight: normal;")

        # Re-populate difficulty if needed (simplified)
        self.setupDifficultySelector()

        # Update Difficulty Labels
        for val, lbl in self.diffLabels.items():
            if val == self.engine.difficulty:
                lbl.setStyleSheet(f"color: {c}; font-weight: bold;")
            else:
                lbl.setStyleSheet("color: #6b7280; font-weight: normal;")

    def updatePromptDisplay(self):
        self.promptLabel.setHtml(self.engine.color_text())

        # Auto-scroll to cursor
        cursor = self.promptLabel.textCursor()

        # Get correct display length (accounting for incorrect space expansion)
        display_pos = self.engine.get_display_length()

        try:
            cursor.setPosition(display_pos)
            self.promptLabel.setTextCursor(cursor)
            self.promptLabel.ensureCursorVisible()
        except Exception:
            pass  # Ignore index errors if any

    def updateLiveStats(self):
        if self.engine.started:
            # Check if time is up
            if self.engine.is_time_up() and not self.results_shown:
                self.results_shown = True
                accuracy, wpm = self.engine.calculate_stats()
                self.results_ready.emit(accuracy, wpm)
                return
            
            accuracy, wpm = self.engine.calculate_stats()
            time_remaining = int(self.engine.get_time_remaining())
            c = self.current_theme
            self.statsLabel.setText(
                f"<span style='color: #9ca3af'>time: </span> <span style='color:{c}'>{time_remaining}s</span>   <span style='color: #9ca3af'>acc: </span> <span style='color:{c}'>{int(accuracy)}%</span>   <span style='color: #9ca3af'>wpm: </span> <span style='color:{c}'>{int(wpm)}</span>"
            )
        else:
            time_limit = int(self.engine.time_limit)
            c = self.current_theme
            self.statsLabel.setText(f"<span style='color: #9ca3af'>time: </span> <span style='color:{c}'>{time_limit}s</span>")

    def showResults(self, accuracy, wpm):
        # Get personal best BEFORE saving to compare correctly
        pb = self.engine.get_personal_best()
        
        # Save test result to history
        self.engine.save_test_result(accuracy, wpm)
        
        # Check if this is a new personal best
        is_new_pb = False
        if pb is None:
            is_new_pb = True  # First test for this mode/difficulty
        elif wpm > pb.get("wpm", 0):
            is_new_pb = True  # Beat previous record
        
        # Determine colors based on performance
        if accuracy >= 95:
            acc_color = "#22c55e"  # Green
        elif accuracy >= 90:
            acc_color = "#eab308"  # Yellow
        else:
            acc_color = "#ef4444"  # Red

        if wpm >= 60:
            wpm_color = "#22c55e"  # Green
        elif wpm >= 30:
            wpm_color = "#eab308"  # Yellow
        else:
            wpm_color = "#ef4444"  # Red

        # Build results text
        acc_text = f"Accuracy: <span style='color:{acc_color}'>{accuracy:.2f}%</span>"
        wpm_text = f"WPM: <span style='color:{wpm_color}'>{wpm:.2f}</span>"
        pb_text = ""

        # Add personal best info
        if is_new_pb:
            pb_text += f"<br/><span style='color:{self.current_theme}'>✦ New Personal Best ✦</span>"
        elif pb:
            pb_text += f"<br/><span style='color:#9ca3af'>Best: {pb['wpm']:.2f} WPM</span>"
            self.personalBest.setFont(QFont("Cascadia Mono", 14, QFont.Weight.Bold))
            self.accuracyLabel.setFont(QFont("Cascadia Mono", 24, QFont.Weight.Bold))
            self.wpmLabel.setFont(QFont("Cascadia Mono", 24, QFont.Weight.Bold))
        
        self.personalBest.setText(pb_text)
        self.accuracyLabel.setText(acc_text)
        self.wpmLabel.setText(wpm_text)
        self.results_shown = True
        self.stackedWidget.setCurrentWidget(self.resultsScreen)

    def restart(self):
        self.engine.generate_text()
        self.results_shown = False  # Reset flag for new test
        self.stackedWidget.setCurrentWidget(self.typingScreen)
        self.updatePromptDisplay()
        self.statsLabel.setText("")

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        if key == Qt.Key.Key_Escape:
            QApplication.quit()
            return

        if key == Qt.Key.Key_Tab:
            self.restart()
            return

        if self.stackedWidget.currentWidget() == self.resultsScreen:
            if key in [Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Space]:
                self.restart()
            return

        # Typing logic
        if key == Qt.Key.Key_Backspace:
            if self.engine.user_input:
                # Check if the last typed character was a correct space
                last_idx = len(self.engine.user_input) - 1
                is_correct_space = (
                    self.engine.user_input[-1] == " "
                    and self.engine.current_text[last_idx] == " "
                )

                if not is_correct_space:
                    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                        # Ctrl+Backspace: delete word
                        if self.engine.user_input.strip():
                            words = self.engine.user_input.rstrip().split(" ")
                            self.engine.user_input = " ".join(words[:-1]) + (
                                " " if len(words) > 1 else ""
                            )
                        else:
                            self.engine.user_input = ""
                    else:
                        self.engine.user_input = self.engine.user_input[:-1]

        elif text.isprintable() and len(text) == 1:
            current_index = len(self.engine.user_input)
            if current_index < len(self.engine.current_text):
                self.engine.user_input += text
                if not self.engine.started:
                    self.engine.start()

        self.updatePromptDisplay()

        if len(self.engine.user_input) == len(self.engine.current_text) and not self.results_shown:
            self.results_shown = True
            accuracy, wpm = self.engine.calculate_stats()
            self.results_ready.emit(accuracy, wpm)

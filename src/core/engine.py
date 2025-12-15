import os
import random
import time
import html
import json


class TypingTestEngine:
    def __init__(self):
        # Get project root (3 levels up from src/core/engine.py)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.words = self.load_file(os.path.join(project_root, "assets", "words.txt"))
        self.quotes = self.load_file(os.path.join(project_root, "assets", "quotes.txt"))
        self.config_path = os.path.join(project_root, "config.json")
        self.history_path = os.path.join(project_root, "history.json")

        self.mode = "words"
        self.difficulty = "25"
        self.accent_color = "#22c55e"  # Default green
        self.load_config()

        self.current_text = ""
        self.user_input = ""
        self.started = False
        self.start_time = 0
        self.time_limit = 60  # Default 60 seconds
        self.paused = False
        self.pause_started_at = 0
        self.total_pause_duration = 0

        self.generate_text()

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    self.accent_color = config.get("theme", "#22c55e")
                    self.mode = config.get("mode", "words")
                    self.difficulty = config.get("difficulty", "25" if self.mode == "words" else "medium")
        except Exception:
            pass

    def save_config(self):
        try:
            config = {
                "theme": self.accent_color,
                "mode": self.mode,
                "difficulty": self.difficulty
            }
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass

    def load_file(self, filename):
        if not os.path.exists(filename):
            return []
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    
    def load_history(self):
        """Load test history from JSON file"""
        try:
            if os.path.exists(self.history_path):
                with open(self.history_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"tests": [], "personal_bests": {}}
    
    def save_test_result(self, accuracy, wpm):
        """Save test result to history with timestamp"""
        try:
            history = self.load_history()
            
            # Create test record
            from datetime import datetime
            test_record = {
                "timestamp": datetime.now().isoformat(),
                "mode": self.mode,
                "difficulty": self.difficulty,
                "wpm": round(wpm, 2),
                "accuracy": round(accuracy, 2),
                "time_limit": self.time_limit,
                "text_length": len(self.current_text),
                "typed_length": len(self.user_input)
            }
            
            # Add to history
            history["tests"].append(test_record)
            
            # Update personal best for this mode/difficulty
            # A new PB is set if:
            # 1. WPM is higher, OR
            # 2. WPM is equal but accuracy is better
            key = f"{self.mode}_{self.difficulty}"
            current_best = history["personal_bests"].get(key, {"wpm": 0, "accuracy": 0})
            
            is_new_best = False
            if wpm > current_best.get("wpm", 0):
                is_new_best = True
            elif wpm == current_best.get("wpm", 0) and accuracy > current_best.get("accuracy", 0):
                is_new_best = True
            
            if is_new_best:
                history["personal_bests"][key] = {
                    "wpm": round(wpm, 2),
                    "accuracy": round(accuracy, 2),
                    "timestamp": test_record["timestamp"]
                }
            
            # Save to file
            with open(self.history_path, "w") as f:
                json.dump(history, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error saving test result: {e}")
            return False
    
    def get_personal_best(self, mode=None, difficulty=None):
        """Get personal best for specific mode/difficulty or current settings"""
        try:
            history = self.load_history()
            mode = mode or self.mode
            difficulty = difficulty or self.difficulty
            key = f"{mode}_{difficulty}"
            return history["personal_bests"].get(key)
        except Exception:
            return None
    
    def get_test_history(self, limit=None, mode=None, difficulty=None):
        """Get test history, optionally filtered and limited"""
        try:
            history = self.load_history()
            tests = history["tests"]
            
            # Filter by mode/difficulty if specified
            if mode:
                tests = [t for t in tests if t["mode"] == mode]
            if difficulty:
                tests = [t for t in tests if t["difficulty"] == difficulty]
            
            # Sort by timestamp (newest first)
            tests.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Limit results if specified
            if limit:
                tests = tests[:limit]
            
            return tests
        except Exception:
            return []
    
    def get_statistics(self):
        """Get overall statistics from test history"""
        try:
            tests = self.get_test_history()
            if not tests:
                return None
            
            total_tests = len(tests)
            avg_wpm = sum(t["wpm"] for t in tests) / total_tests
            avg_accuracy = sum(t["accuracy"] for t in tests) / total_tests
            best_wpm = max(t["wpm"] for t in tests)
            best_accuracy = max(t["accuracy"] for t in tests)
            
            return {
                "total_tests": total_tests,
                "average_wpm": round(avg_wpm, 2),
                "average_accuracy": round(avg_accuracy, 2),
                "best_wpm": round(best_wpm, 2),
                "best_accuracy": round(best_accuracy, 2)
            }
        except Exception:
            return None

    def set_mode(self, mode):
        self.mode = mode
        if mode == "words":
            self.difficulty = "25"
        else:
            self.difficulty = "medium"
        self.save_config()
        self.generate_text()

    def set_difficulty(self, difficulty):
        self.difficulty = difficulty
        self.save_config()
        self.generate_text()

    def set_accent_color(self, color):
        self.accent_color = color
        self.save_config()
    
    def get_time_limit(self):
        """Get time limit in seconds based on mode and difficulty"""
        if self.mode == "words":
            word_count = int(self.difficulty)
            if word_count <= 10:
                return 30
            elif word_count <= 25:
                return 60
            elif word_count <= 50:
                return 90
            else:  # 100 words
                return 120
        else:  # quotes mode
            if self.difficulty == "short":
                return 45
            elif self.difficulty == "medium":
                return 60
            else:  # long
                return 90

    def generate_text(self):
        if self.mode == "words":
            count = int(self.difficulty)
            if self.words:
                self.current_text = " ".join(random.choices(self.words, k=count))
            else:
                self.current_text = "Error: words.txt not found or empty."
        elif self.mode == "quotes":
            filtered_quotes = []
            if not self.quotes:
                self.current_text = "Error: quotes.txt not found or empty."
                self.reset_input()
                return

            if self.difficulty == "short":
                filtered_quotes = [q for q in self.quotes if len(q) < 60]
            elif self.difficulty == "medium":
                filtered_quotes = [q for q in self.quotes if 60 <= len(q) < 120]
            elif self.difficulty == "long":
                filtered_quotes = [q for q in self.quotes if len(q) >= 120]

            if not filtered_quotes:
                filtered_quotes = self.quotes

            self.current_text = random.choice(filtered_quotes)

        self.time_limit = self.get_time_limit()
        self.reset_input()

    def start(self):
        if not self.started:
            self.started = True
            self.start_time = time.time()
            self.paused = False
            self.pause_started_at = 0
            self.total_pause_duration = 0

    def reset_input(self):
        self.user_input = ""
        self.started = False
        self.start_time = 0
        self.paused = False
        self.pause_started_at = 0
        self.total_pause_duration = 0
    
    def is_time_up(self):
        """Check if the time limit has been reached"""
        if not self.started:
            return False
        if self.paused:
            return False
        elapsed = time.time() - self.start_time - self.total_pause_duration
        return elapsed >= self.time_limit
    
    def get_time_remaining(self):
        """Get remaining time in seconds"""
        if not self.started:
            return self.time_limit
        if self.paused:
            # When paused, freeze remaining time
            elapsed = self.pause_started_at - self.start_time - self.total_pause_duration
        else:
            elapsed = time.time() - self.start_time - self.total_pause_duration
        return max(0, self.time_limit - elapsed)

    def pause(self):
        """Pause the timer and typing state"""
        if self.started and not self.paused:
            self.paused = True
            
            self.pause_started_at = time.time()

    def resume(self):
        """Resume from paused state"""
        if self.started and self.paused:
            self.paused = False
            if self.pause_started_at:
                self.total_pause_duration += time.time() - self.pause_started_at
                self.pause_started_at = 0

    def calculate_stats(self):
        if not self.started or not self.user_input:
            return 0.0, 0.0
        # Calculate elapsed time excluding pause duration
        if self.paused:
            # Use time up to when pause started
            elapsed = self.pause_started_at - self.start_time - self.total_pause_duration
        else:
            elapsed = time.time() - self.start_time - self.total_pause_duration
        minutes = max(elapsed / 60.0, 0.001)
        min_len = min(len(self.user_input), len(self.current_text))
        correct = sum(
            1 for i in range(min_len) if self.user_input[i] == self.current_text[i]
        )
        accuracy = (correct / min_len) * 100 if min_len > 0 else 0.0
        wpm = len(self.user_input) / 5.0 / minutes
        return accuracy, wpm

    def get_display_length(self):
        # Calculate the length of the text as it appears in QTextEdit
        # Incorrect spaces (typed != " " and c == " ") become "&middot;&#8203;" which is 2 chars (middot + zero-width space)
        # Correct spaces are 1 char (" ")
        # All other chars are 1 char
        length = 0
        for i in range(len(self.user_input)):
            c = self.current_text[i]
            typed = self.user_input[i]
            if typed != " " and c == " ":
                length += 2  # &middot; + &#8203;
            else:
                length += 1
        return length

    # def color_text(self):
    #     spans = []
    #     for i, c in enumerate(self.current_text):
    #         color = "#6b7280"  # Default: gray for untyped
    #         text_decoration = None
    #         display_char = html.escape(c)

    #         if i < len(self.user_input):
    #             typed = self.user_input[i]
    #             if typed == c:
    #                 color = self.accent_color  # Use accent color for correct
    #             else:
    #                 color = "#ef4444"  # Red for incorrect
    #                 if typed != " " and c == " ":
    #                     display_char = (
    #                         "&middot;&#8203;"  # Add zero-width space to allow wrapping
    #                         # "&middot;"
    #                     )
    #         elif i == len(self.user_input):
    #             color = "#ffffff"  # White for current char
    #             text_decoration = "underline"

    #         style_parts = [f"color:{color}"]
    #         if text_decoration:
    #             style_parts.append(f"text-decoration:{text_decoration}")
    #         style = "; ".join(style_parts)

    #         spans.append(f'<span style="{style}">{display_char}</span>')

    #     inner_html = "".join(spans)
    #     # Use div with line-height for better spacing and center alignment
    #     return f'<div style="font-size:24px; line-height: 160%; text-align: center;">{inner_html}</div>'

    def color_text(self):
        spans = []
        user_input = self.user_input
        current_text = self.current_text
        accent = self.accent_color

        typed_len = len(user_input)
        zws_middot = "&middot;&#8203;"
        default_color = "#6b7280"  # gray
        wrong_color = "#ef4444"  # red

        for i, c in enumerate(current_text):
            # --- Determine display char ---
            if c == " ":
                display_char = " "
            else:
                display_char = html.escape(c)

            # --- Determine style ---
            # Untyped section
            if i > typed_len:
                color = default_color
                underline = False

            # Current character
            elif i == typed_len:
                color = "#ffffff"
                underline = True

            # Typed section
            else:
                typed_char = user_input[i]
                underline = False
                if typed_char == c:
                    color = accent
                else:
                    color = wrong_color
                    # Incorrect space: reveal middot + ZWS
                    if typed_char != " " and c == " ":
                        display_char = zws_middot

            # Build style
            if underline:
                style = f"color:{color}; text-decoration:underline"
            else:
                style = f"color:{color}"

            spans.append(f'<span style="{style}">{display_char}</span>')

        inner_html = "".join(spans)
        return (
            '<div style="font-size:24px; line-height:160%; text-align:center;">'
            + inner_html
            + "</div>"
        )

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

        self.mode = "words"
        self.difficulty = "25"
        self.accent_color = "#22c55e"  # Default green
        self.load_config()

        self.current_text = ""
        self.user_input = ""
        self.started = False
        self.start_time = 0

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

        self.reset_input()

    def start(self):
        if not self.started:
            self.started = True
            self.start_time = time.time()

    def reset_input(self):
        self.user_input = ""
        self.started = False
        self.start_time = 0

    def calculate_stats(self):
        if not self.started or not self.user_input:
            return 0.0, 0.0
        minutes = max((time.time() - self.start_time) / 60.0, 0.001)
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

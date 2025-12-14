import sys
import os
import time
import shutil
from src.core.engine import TypingTestEngine


class CLITypingTest:
    def __init__(self):
        self.engine = TypingTestEngine()
        self.running = True
        self.content_width = 50
        self.MIN_W, self.MIN_H = 60, 15
        self.last_render_lines = 0  # Track number of lines rendered
        self.initial_render = True
        
        
    def get_terminal_size(self):
        try:
            size = shutil.get_terminal_size()
            cols, rows = int(size.columns), int(size.lines)
        except Exception:
            pass
        
        return cols, rows

    def show_terminal_size_warning(self, cols, rows, min_cols, min_rows):
        """
        Display a visible warning if terminal is smaller than recommended size.
        Non-intrusive: shown only once at the top. 
        """
        warning = f"⚠ Terminal too small\nCurrent: {cols}×{rows}\nRecommended: {min_cols}×{min_rows}"
        lines = [line.center(cols) for line in warning.split("\n")]

        # Vertical centering: calculate how many blank lines above it
        total_lines = len(lines)
        top_padding = max((rows - total_lines) // 2, 0)

        print("\033[2J\033[H")  # clear screen
        print("\n" * top_padding)
        for line in lines:
            print(line)

    def center_text(self, text, strip_ansi=False):
        """Center text horizontally"""
        term_width, _ = self.get_terminal_size()
        # For ANSI colored text, calculate visible length
        if strip_ansi:
            import re

            # Strip all ANSI escape sequences (more comprehensive pattern)
            visible_text = re.sub(r"\033\[[0-9;]*[mGKHf]", "", text)
            visible_len = len(visible_text)
        else:
            visible_len = len(text)

        padding = (term_width - visible_len) // 2
        return " " * max(0, padding) + text

    def hex_to_ansi(self, hex_color):
        """Convert hex color to ANSI TrueColor string"""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"\033[38;2;{r};{g};{b}m"

    def get_vertical_padding(self, content_lines):
        """Calculate vertical padding to center content"""
        _, term_height = self.get_terminal_size()
        padding = max(0, (term_height - content_lines) // 2)
        return padding

    def clear_screen(self):
        """Clear screen using ANSI escape codes - only for initial render"""
        print("\033[2J\033[H", end="", flush=True)
    
    def move_cursor_home(self):
        """Move cursor to home position without clearing screen"""
        print("\033[H", end="", flush=True)
    
    def clear_from_cursor(self):
        """Clear from cursor to end of screen"""
        print("\033[J", end="", flush=True)

    def render(self):
        """Render minimal centered UI without flickering"""
        import re
        
        # Build content first to count lines
        content_lines = []

        term_width, term_height = self.get_terminal_size()

        # Show visible warning if too small
        if term_width < self.MIN_W or term_height < self.MIN_H:
            self.show_terminal_size_warning(term_width, term_height, self.MIN_W, self.MIN_H)
            return
        
        # Tokenize text into words and separators
        tokens = re.split(r"(\s+)", self.engine.current_text)

        # Build lines respecting max width
        lines = []
        current_line = ""
        max_width = self.content_width

        for token in tokens:
            if not token:
                continue

            # If adding token exceeds max width and current line is not empty, start new line
            if len(current_line) + len(token) > max_width and current_line:
                lines.append(current_line)
                current_line = token
            else:
                current_line += token

        if current_line:
            lines.append(current_line)

        # Colorize each line
        global_idx = 0
        theme_color = self.hex_to_ansi(self.engine.accent_color)

        for line_text in lines:
            line_chars = []
            for c in line_text:
                if global_idx < len(self.engine.user_input):
                    typed = self.engine.user_input[global_idx]
                    if typed == c:
                        line_chars.append(f"{theme_color}{c}\033[0m")
                    else:
                        display_char = "·" if (typed != " " and c == " ") else c
                        line_chars.append(f"\033[91m{display_char}\033[0m")
                elif global_idx == len(self.engine.user_input):
                    line_chars.append(f"\033[4m{c}\033[0m")
                else:
                    line_chars.append(f"\033[90m{c}\033[0m")
                global_idx += 1
            content_lines.append("".join(line_chars))

        content_lines.append("")  # Empty line

        # Stats
        if self.engine.started:
            accuracy, wpm = self.engine.calculate_stats()
            stats = f"\033[90mwpm\033[0m {theme_color}{wpm:.0f}\033[0m  \033[90macc\033[0m {theme_color}{accuracy:.0f}%\033[0m"
        else:
            stats = "\033[90mstart typing...\033[0m"
        content_lines.append(stats)

        # Use flicker-free rendering technique
        if self.initial_render:
            self.clear_screen()  # Only clear on first render
            self.initial_render = False
        else:
            self.move_cursor_home()  # Move to top without clearing

        # Add vertical padding
        v_padding = self.get_vertical_padding(len(content_lines))

        # Use proper line endings for Linux in raw mode
        newline = "\r\n" if os.name != "nt" else "\n"
        
        # Build entire output as a single string to minimize flicker
        output_buffer = []
        output_buffer.append(newline * v_padding)

        # Print centered content
        for line in content_lines:
            if line == "":
                output_buffer.append(newline)
            elif "wpm" in line:  # Stats line
                output_buffer.append(self.center_text(line, strip_ansi=True) + newline)
            else:  # Text lines
                output_buffer.append(self.center_text(line, strip_ansi=True) + newline)
        output_buffer.append(newline)

        # Footer
        mode_info = f"\033[90m{self.engine.mode} \033[37m|\033[90m {self.engine.difficulty}\033[0m"
        shortcuts = f"{theme_color}^M\033[0m mode  {theme_color}^D\033[0m difficulty  {theme_color}^T\033[0m theme  {theme_color}^R\033[0m restart  {theme_color}^C\033[0m quit"

        output_buffer.append(self.center_text(mode_info, strip_ansi=True) + newline)
        output_buffer.append(newline)
        output_buffer.append(self.center_text(shortcuts, strip_ansi=True))
        
        # Clear from cursor to end and write all at once
        self.clear_from_cursor()
        print("".join(output_buffer), end="", flush=True)
        
        # Track lines rendered for next update
        self.last_render_lines = len(content_lines) + 3

    def show_results(self):
        """Display minimal results with flicker-free rendering"""
        accuracy, wpm = self.engine.calculate_stats()
        theme_color = self.hex_to_ansi(self.engine.accent_color)

        # Determine colors
        if accuracy >= 95:
            acc_color = theme_color
        elif accuracy >= 90:
            acc_color = "\033[93m"
        else:
            acc_color = "\033[91m"

        if wpm >= 60:
            wpm_color = theme_color
        elif wpm >= 30:
            wpm_color = "\033[93m"
        else:
            wpm_color = "\033[91m"

        content_lines = [
            f"\033[90mwpm\033[0m {wpm_color}{wpm:.0f}",
            f"\033[90macc\033[0m {acc_color}{accuracy:.0f}%",
            "",
            "\033[90mpress enter to continue\033[0m",
        ]

        self.move_cursor_home()
        self.clear_from_cursor()
        v_padding = self.get_vertical_padding(len(content_lines))
        newline = "\r\n" if os.name != "nt" else "\n"
        print(newline * v_padding, end="", flush=True)

        for line in content_lines:
            print(self.center_text(line, strip_ansi=True), end=newline, flush=True)

        try:
            # Wait for Enter key in raw mode
            if os.name != "nt":
                import tty
                import termios

                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    while True:
                        char = sys.stdin.read(1)
                        if char == "\r" or char == "\n":  # Enter key
                            break
                        elif char == "\x03":  # Ctrl+C
                            raise KeyboardInterrupt
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            else:
                input()

            self.engine.generate_text()
            self.run()
        except KeyboardInterrupt:
            self.running = False

    def get_input(self, prompt="› "):
        """Custom input loop for centered, responsive input"""
        buffer = ""
        if os.name == "nt":
            import msvcrt
        else:
            import tty
            import termios

        while True:
            # Render prompt and buffer centered
            term_width, _ = self.get_terminal_size()
            full_text = f"{prompt}{buffer}"
            max_width = self.content_width

            if len(full_text) > max_width:
                # Scroll text if it exceeds content width
                visible_text = full_text[-max_width:]
            else:
                visible_text = full_text

            padding = (term_width - len(visible_text)) // 2
            line = " " * max(0, padding) + visible_text

            # Move cursor to start of line, clear line, print centered text
            print(f"\r\033[K{line}", end="", flush=True)

            if os.name == "nt":
                if msvcrt.kbhit():
                    char = msvcrt.getch()
                    if char == b"\x03":  # Ctrl+C
                        raise KeyboardInterrupt
                    elif char == b"\r":  # Enter
                        print()  # Newline after input
                        return buffer
                    elif char == b"\x08":  # Backspace
                        buffer = buffer[:-1]
                    else:
                        try:
                            decoded = char.decode("utf-8")
                            if decoded.isprintable():
                                buffer += decoded
                        except UnicodeDecodeError:
                            pass
                time.sleep(0.01)
            else:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    char = sys.stdin.read(1)
                    if char == "\x03":  # Ctrl+C
                        raise KeyboardInterrupt
                    elif char == "\r" or char == "\n":  # Enter
                        print()
                        return buffer
                    elif char == "\x7f" or char == "\x08":  # Backspace
                        buffer = buffer[:-1]
                    elif char.isprintable():
                        buffer += char
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def show_menu(self, title, options):
        """Generic centered menu with flicker-free rendering and aligned options"""
        self.move_cursor_home()
        self.clear_from_cursor()

        # Calculate total lines: title + blank + options + blank + prompt
        total_lines = 1 + 1 + len(options) + 1 + 1
        v_padding = self.get_vertical_padding(total_lines)

        newline = "\r\n" if os.name != "nt" else "\n"
        term_width, _ = self.get_terminal_size()
        
        # Find the longest option to determine menu width
        max_option_len = max(len(opt) for opt in options)
        menu_width = max(max_option_len, len(title))
        
        # Calculate left padding to center the menu block
        left_padding = (term_width - menu_width) // 2
        
        output_buffer = []
        output_buffer.append(newline * v_padding)
        # Center title
        title_text = f"\033[90m{title}\033[0m"
        title_padding = left_padding + (menu_width - len(title)) // 2
        output_buffer.append(" " * title_padding + title_text + newline)
        output_buffer.append(newline)
        # Left-align options within the centered menu block
        for opt in options:
            output_buffer.append(" " * left_padding + opt + newline)
        output_buffer.append(newline)
        
        print("".join(output_buffer), end="", flush=True)

        return self.get_input()

    def change_mode(self):
        """Mode selection"""
        try:
            choice = self.show_menu("mode", ["1  words", "2  quotes"])
            if choice == "1":
                self.engine.set_mode("words")
            elif choice == "2":
                self.engine.set_mode("quotes")
            self.initial_render = True
        except Exception:
            pass

    def change_difficulty(self):
        """Difficulty selection"""
        try:
            if self.engine.mode == "words":
                choice = self.show_menu(
                    "difficulty",
                    ["1  10 words", "2  25 words", "3  50 words", "4  100 words"],
                )
                diff_map = {"1": "10", "2": "25", "3": "50", "4": "100"}
            else:
                choice = self.show_menu(
                    "difficulty", ["1  short", "2  medium", "3  long"]
                )
                diff_map = {"1": "short", "2": "medium", "3": "long"}

            if choice in diff_map:
                self.engine.set_difficulty(diff_map[choice])
            self.initial_render = True
        except Exception:
            pass

    def change_theme(self):
        """Theme selection"""
        try:
            themes = [
                "1  green",
                "2  purple",
                "3  blue",
                "4  red",
                "5  orange",
                "6  pink",
                "7  cyan",
                "8  yellow",
            ]
            choice = self.show_menu("theme", themes)

            theme_map = {
                "1": "#22c55e",
                "2": "#a855f7",
                "3": "#3b82f6",
                "4": "#ef4444",
                "5": "#f97316",
                "6": "#ec4899",
                "7": "#06b6d4",
                "8": "#eab308",
            }

            if choice in theme_map:
                self.engine.set_accent_color(theme_map[choice])
            self.initial_render = True
        except Exception:
            pass

    def run(self):
        """Main game loop"""
        if os.name == "nt":
            import msvcrt
        else:
            import tty
            import termios
            import select

        # For Linux, set up terminal once at the start
        if os.name != "nt":
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

        try:
            # Set raw mode for Linux
            if os.name != "nt":
                tty.setraw(sys.stdin.fileno())

            self.render()
            last_input_len = 0

            while self.running:
                try:
                    if os.name == "nt":
                        # Windows
                        if msvcrt.kbhit():
                            char = msvcrt.getch()

                            if char == b"\x03":  # Ctrl+C
                                raise KeyboardInterrupt
                            elif char == b"\x12":  # Ctrl+R
                                self.engine.generate_text()
                                self.initial_render = True
                                last_input_len = -1  # Force re-render
                            elif char == b"\x0d":  # Ctrl+M
                                self.change_mode()
                                last_input_len = -1
                            elif char == b"\x04":  # Ctrl+D
                                self.change_difficulty()
                                last_input_len = -1
                            elif char == b"\x14":  # Ctrl+T
                                self.change_theme()
                                last_input_len = -1
                            elif char == b"\x08":  # Backspace
                                if self.engine.user_input:
                                    last_idx = len(self.engine.user_input) - 1
                                    is_correct_space = (
                                        self.engine.user_input[-1] == " "
                                        and self.engine.current_text[last_idx] == " "
                                    )
                                    if not is_correct_space:
                                        self.engine.user_input = self.engine.user_input[
                                            :-1
                                        ]
                            else:
                                try:
                                    text = char.decode("utf-8")
                                    if text.isprintable() and len(text) == 1:
                                        current_index = len(self.engine.user_input)
                                        if current_index < len(
                                            self.engine.current_text
                                        ):
                                            self.engine.user_input += text
                                            if not self.engine.started:
                                                self.engine.start()
                                except UnicodeDecodeError:
                                    pass

                            # Only re-render if input changed or forced
                            if len(self.engine.user_input) != last_input_len:
                                self.render()
                                last_input_len = len(self.engine.user_input)

                            if len(self.engine.user_input) == len(
                                self.engine.current_text
                            ):
                                self.show_results()
                                last_input_len = -1  # Force re-render on restart

                    else:
                        # Unix/Linux - non-blocking check
                        rlist, _, _ = select.select([sys.stdin], [], [], 0)
                        if rlist:
                            char = sys.stdin.read(1)

                            if char == "\x03":  # Ctrl+C
                                raise KeyboardInterrupt
                            elif char == "\x12":  # Ctrl+R
                                self.engine.generate_text()
                                self.initial_render = True
                                last_input_len = -1
                            elif char == "\x0d":  # Ctrl+M
                                self.change_mode()
                                last_input_len = -1
                            elif char == "\x04":  # Ctrl+D
                                self.change_difficulty()
                                last_input_len = -1
                            elif char == "\x14":  # Ctrl+T
                                self.change_theme()
                                last_input_len = -1
                            elif char == "\x7f" or char == "\x08":  # Backspace
                                if self.engine.user_input:
                                    last_idx = len(self.engine.user_input) - 1
                                    is_correct_space = (
                                        self.engine.user_input[-1] == " "
                                        and self.engine.current_text[last_idx] == " "
                                    )
                                    if not is_correct_space:
                                        self.engine.user_input = self.engine.user_input[
                                            :-1
                                        ]
                            elif char.isprintable():
                                current_index = len(self.engine.user_input)
                                if current_index < len(self.engine.current_text):
                                    self.engine.user_input += char
                                    if not self.engine.started:
                                        self.engine.start()

                            if len(self.engine.user_input) != last_input_len:
                                self.render()
                                last_input_len = len(self.engine.user_input)

                            if len(self.engine.user_input) == len(
                                self.engine.current_text
                            ):
                                self.show_results()
                                last_input_len = -1

                    time.sleep(0.01)

                except KeyboardInterrupt:
                    self.running = False
                    break
        finally:
            # Restore terminal settings on Linux
            if os.name != "nt":
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            # Show goodbye message
            self.clear_screen()
            v_padding = self.get_vertical_padding(1)
            newline = "\r\n" if os.name != "nt" else "\n"
            print(newline * v_padding, end="", flush=True)
            print(self.center_text("\033[90mgoodbye\033[0m\n"), end="", flush=True)

if __name__ == "__main__":
    app = CLITypingTest()
    app.run()
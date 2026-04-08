import re
import sys
import os
import time
import shutil
import asciichartpy as asc
from src.core.engine import TypingTestEngine
from src.core.presentation import (
    colorize_char_for_cli,
    wrong_char_for_cli,
    wrong_space_for_cli,
    untyped_char_for_cli,
    current_char_for_cli,
)

if os.name != "nt":
    import fcntl

class CLITypingTest:
    def __init__(self):
        self.engine = TypingTestEngine()
        self.running = True
        self.content_width = 50
        self.MIN_W, self.MIN_H = 60, 15
        self.last_render_lines = 0
        self.initial_render = True
        self.last_term_size = (0, 0)
        self.warning_shown = False
        self.last_render_time = 0
        self.cursor_hidden = False
        self._test_ending = False  # Guard against double-trigger (timer + completion)

        # Subscribe to engine callbacks
        self.engine.on_char_typed = self._on_char_typed
        self.engine.on_stats_updated = self._on_stats_updated
        self.engine.on_test_complete = self._on_test_complete

        # Flags for callback-driven updates
        self._needs_render = False
        self._needs_full_render = True

    def _on_char_typed(self):
        """Callback: fired when a character is typed"""
        self._needs_render = True

    def _on_stats_updated(self, state):
        """Callback: fired when stats update (for live WPM/accuracy)"""
        self._needs_render = True

    def _on_test_complete(self, result):
        """Callback: fired when test finishes."""
        if self._test_ending:
            return
        self._test_ending = True

        should_continue = self._show_results_from_result(result)
        if should_continue:
            self.engine.generate_text()
            self._needs_full_render = True
            self._needs_render = True
            self._test_ending = False
        else:
            self.running = False

    def hide_cursor(self):
        """Hide terminal cursor"""
        if not self.cursor_hidden:
            print("\033[?25l", end="", flush=True)
            self.cursor_hidden = True

    def show_cursor(self):
        """Show terminal cursor"""
        if self.cursor_hidden:
            print("\033[?25h", end="", flush=True)
            self.cursor_hidden = False

    def get_terminal_size(self):
        try:
            size = shutil.get_terminal_size()
            cols, rows = int(size.columns), int(size.lines)
            return cols, rows
        except Exception:
            return 80, 24

    def show_terminal_size_warning(self, cols, rows, min_cols, min_rows):
        self.warning_shown = True
        warning = f"⚠ Terminal too small\nCurrent: {cols}×{rows}\nRecommended: {min_cols}×{min_rows}"
        lines = [line.center(cols) for line in warning.split("\n")]

        total_lines = len(lines)
        top_padding = max((rows - total_lines) // 2, 0)

        print("\033[2J\033[H")
        print("\n" * top_padding)
        for line in lines:
            print(line)

    def center_text(self, text, strip_ansi=False):
        """Center text horizontally"""
        term_width, _ = self.get_terminal_size()
        if strip_ansi:
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
        """Clear screen using ANSI escape codes"""
        print("\033[2J\033[H", end="", flush=True)

    def render(self):
        """Render minimal centered UI without flickering"""
        self.last_render_time = time.time()
        content_lines = []

        term_width, term_height = self.get_terminal_size()

        if term_width < self.MIN_W or term_height < self.MIN_H:
            self.show_terminal_size_warning(term_width, term_height, self.MIN_W, self.MIN_H)
            return

        self.warning_shown = False

        theme_color = self.hex_to_ansi(self.engine.accent_color)

        # Paused indicator
        if self.engine.paused:
            content_lines.append("\033[93mPAUSED\033[0m")
            content_lines.append("")

        # Timer display
        if self.engine.started:
            time_remaining = int(self.engine.get_time_remaining())
            timer_display = f"{theme_color}{time_remaining}s\033[0m"
        else:
            time_limit = int(self.engine.time_limit)
            timer_display = f"{theme_color}{time_limit}s\033[0m"

        content_lines.append(timer_display)
        content_lines.append("")

        # Tokenize and build lines
        tokens = re.split(r"(\s+)", self.engine.current_text)
        lines = []
        current_line = ""
        max_width = self.content_width

        for token in tokens:
            if not token:
                continue
            if len(current_line) + len(token) > max_width and current_line:
                lines.append(current_line)
                current_line = token
            else:
                current_line += token

        if current_line:
            lines.append(current_line)

        # Colorize each line using presentation helpers
        global_idx = 0

        for line_text in lines:
            line_chars = []
            for c in line_text:
                if global_idx < len(self.engine.user_input):
                    typed = self.engine.user_input[global_idx]
                    if typed == c:
                        line_chars.append(colorize_char_for_cli(c, self.engine.accent_color))
                    elif c == " ":
                        line_chars.append(wrong_space_for_cli())
                    else:
                        line_chars.append(wrong_char_for_cli(c))
                elif global_idx == len(self.engine.user_input):
                    line_chars.append(current_char_for_cli(c))
                else:
                    line_chars.append(untyped_char_for_cli(c))
                global_idx += 1
            content_lines.append("".join(line_chars))

        content_lines.append("")

        # Stats
        if self.engine.started:
            accuracy, wpm = self.engine.calculate_stats()
            stats = f"\033[90mwpm\033[0m {theme_color}{wpm:.0f}\033[0m  \033[90macc\033[0m {theme_color}{accuracy:.0f}%\033[0m"
        else:
            stats = f"\033[90mstart typing...\033[0m"
        content_lines.append(stats)

        if self.initial_render:
            self.initial_render = False

        v_padding = self.get_vertical_padding(len(content_lines))
        newline = "\r\n" if os.name != "nt" else "\n"

        output_buffer = []
        output_buffer.append("\033[H\033[J")
        output_buffer.append(newline * v_padding)

        for line in content_lines:
            if line == "":
                output_buffer.append(newline)
            elif "wpm" in line or "start typing" in line:
                output_buffer.append(self.center_text(line, strip_ansi=True) + newline)
            else:
                output_buffer.append(self.center_text(line, strip_ansi=True) + newline)
        output_buffer.append(newline)

        mode_info = f"\033[90m{self.engine.mode} \033[37m|\033[90m {self.engine.difficulty}\033[0m"
        shortcuts = f"{theme_color}^M\033[0m mode  {theme_color}^D\033[0m difficulty  {theme_color}^T\033[0m theme  {theme_color}^R\033[0m restart  {theme_color}^C\033[0m quit  {theme_color}^P\033[0m {"resume" if self.engine.paused else "pause"}"

        output_buffer.append(self.center_text(mode_info, strip_ansi=True) + newline)
        output_buffer.append(newline)
        output_buffer.append(self.center_text(shortcuts, strip_ansi=True))

        print("".join(output_buffer), end="", flush=True)
        self.last_render_lines = len(content_lines) + 3
        self._needs_render = False
        self._needs_full_render = False

    def _render_wpm_graph(self, wpm_history: list, width: int = 40) -> list[str]:
        """
        Render WPM over time using asciichartpy for a smooth line graph.
        Returns list of lines ready for centering.
        """
        if not wpm_history or len(wpm_history) < 2:
            return ["\033[90mnot enough data for graph\033[0m"]

        wpm_values = [wpm for _, wpm in wpm_history]
        time_values = [t for t, _ in wpm_history]
        max_wpm = max(wpm_values)
        total_time = time_values[-1]

        if max_wpm == 0:
            return ["\033[90mno data\033[0m"]

        theme_color = self.hex_to_ansi(self.engine.accent_color)
        dim = "\033[90m"
        reset = "\033[0m"

        # Plot using asciichartpy
        chart = asc.plot(wpm_values, {
            'height': 5,
            'format': '{:6.0f}',
        })

        graph_lines = []
        # Find max width (visible chars, strip ANSI)
        raw_lines = []
        for line in chart.split("\n"):
            match = re.search(r'[┤┼│]', line)
            if match:
                sep_idx = match.start()
                label = line[:sep_idx].rstrip()
                chart_part = line[sep_idx:]
                raw_lines.append((label, chart_part))
            else:
                raw_lines.append(("", line))

        # Calculate max visible width
        max_width = 0
        for label, chart_part in raw_lines:
            visible = len(label) + len(chart_part)
            max_width = max(max_width, visible)

        # Build padded, colored lines
        for label, chart_part in raw_lines:
            padding = " " * (max_width - len(label) - len(chart_part))
            graph_lines.append(
                f"{dim}{label}{reset}{theme_color}{chart_part}{padding}{reset}"
            )

        # Add time labels row
        bar_count = max_width
        time_label_positions = self._compute_label_positions(total_time, bar_count, 5)

        time_row = [" "] * (bar_count + 10)
        for pos_seconds, pos_bar in reversed(time_label_positions):
            label = f"{int(pos_seconds)}s"
            start = pos_bar - len(label) // 2 + 5
            end = start + len(label)

            conflict = False
            for idx in range(max(0, start - 1), min(end + 1, len(time_row))):
                if time_row[idx] != " ":
                    conflict = True
                    break

            if not conflict:
                for ci, ch in enumerate(label):
                    idx = start + ci
                    if 0 <= idx < len(time_row):
                        time_row[idx] = ch

        graph_lines.append(f"{dim}{''.join(time_row)}{reset}")

        return graph_lines

    def _compute_label_positions(self, total_time: float, bar_count: int, max_labels: int) -> list[tuple[float, int]]:
        """
        Compute positions for time labels along the x-axis.
        Returns list of (time_seconds, bar_index) pairs, ordered left-to-right (0s to total_time).
        """
        if bar_count < 2 or total_time <= 0:
            return [(0, 0), (total_time, bar_count - 1)]

        raw_interval = total_time / (max_labels - 1)

        if raw_interval <= 1:
            interval = 1
        elif raw_interval <= 2:
            interval = 2
        elif raw_interval <= 5:
            interval = 5
        elif raw_interval <= 10:
            interval = 10
        elif raw_interval <= 15:
            interval = 15
        elif raw_interval <= 30:
            interval = 30
        else:
            interval = 60

        positions = []
        t = 0
        while t <= total_time + 0.01:  # small epsilon for float comparison
            bar_idx = int((t / total_time) * (bar_count - 1))
            positions.append((t, bar_idx))
            t += interval

        # Always include end if not already
        if not positions or positions[-1][0] < total_time - 0.01:
            positions.append((total_time, bar_count - 1))

        return positions

    def _show_results_from_result(self, result):
        """Display results from TestResult object (callback-driven)"""
        theme_color = self.hex_to_ansi(self.engine.accent_color)

        # Determine colors
        if result.accuracy >= 95:
            acc_color = theme_color
        elif result.accuracy >= 90:
            acc_color = "\033[93m"
        else:
            acc_color = "\033[91m"

        if result.wpm >= 60:
            wpm_color = theme_color
        elif result.wpm >= 30:
            wpm_color = "\033[93m"
        else:
            wpm_color = "\033[91m"

        content_lines = []

        # Show personal best or new record
        if result.is_new_personal_best:
            content_lines.append(f"{theme_color}✦ New Personal Best ✦\033[0m")
        elif result.personal_best:
            content_lines.append(f"\033[90mBest: {result.personal_best['wpm']:.0f} WPM\033[0m")

        content_lines.append("")

        # Render WPM graph
        graph_lines = self._render_wpm_graph(result.wpm_history)
        content_lines.extend(graph_lines)
        content_lines.append("")

        content_lines.append(f"\033[90mwpm\033[0m {wpm_color}{result.wpm:.0f}")
        content_lines.append(f"\033[90macc\033[0m {acc_color}{result.accuracy:.0f}%")
        content_lines.append("")
        content_lines.append("\033[90mpress enter to continue\033[0m")

        v_padding = self.get_vertical_padding(len(content_lines))
        newline = "\r\n" if os.name != "nt" else "\n"

        output_buffer = []
        output_buffer.append("\033[H\033[J")
        output_buffer.append(newline * v_padding)

        for line in content_lines:
            output_buffer.append(self.center_text(line, strip_ansi=True) + newline)

        print("".join(output_buffer), end="", flush=True)

        # Wait for Enter — just returns True to continue, False to quit
        try:
            if os.name != "nt":
                import tty
                import termios

                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    while True:
                        char = sys.stdin.read(1)
                        if char == "\r" or char == "\n":
                            return True  # Continue to next test
                        elif char == "\x03":
                            return False  # Quit
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            else:
                try:
                    input()
                    return True  # Continue
                except KeyboardInterrupt:
                    return False  # Quit
        except KeyboardInterrupt:
            return False  # Quit

    def show_results(self):
        """Display results by finishing test and letting callback handle display."""
        result = self.engine.finish_test()
        # Callback _on_test_complete handles _show_results_from_result

    def _check_test_complete(self):
        """Check if all characters are typed and end test."""
        if self._test_ending:
            return
        if self.engine.started and not self.engine.paused:
            if len(self.engine.user_input) == len(self.engine.current_text):
                self.show_results()

    def get_input(self, prompt="› "):
        """Custom input loop for centered, responsive input"""
        buffer = ""
        if os.name == "nt":
            import msvcrt
        else:
            import tty
            import termios

        while True:
            term_width, _ = self.get_terminal_size()
            full_text = f"{prompt}{buffer}"
            max_width = self.content_width

            if len(full_text) > max_width:
                visible_text = full_text[-max_width:]
            else:
                visible_text = full_text

            padding = (term_width - len(visible_text)) // 2
            line = " " * max(0, padding) + visible_text

            print(f"\r\033[K{line}", end="", flush=True)

            if os.name == "nt":
                if msvcrt.kbhit():
                    char = msvcrt.getch()
                    if char == b"\x03":
                        raise KeyboardInterrupt
                    elif char == b"\r":
                        print()
                        return buffer
                    elif char == b"\x08":
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
                    if char == "\x03":
                        raise KeyboardInterrupt
                    elif char == "\r" or char == "\n":
                        print()
                        return buffer
                    elif char == "\x7f" or char == "\x08":
                        buffer = buffer[:-1]
                    elif char.isprintable():
                        buffer += char
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def show_menu(self, title, options):
        """Generic centered menu with arrow key navigation"""
        if os.name == "nt":
            import msvcrt
        else:
            import tty
            import termios

        selected = 0
        previous_selected = 0
        theme_color = self.hex_to_ansi(self.engine.accent_color)
        needs_render = True
        menu_layout = {}

        if os.name != "nt":
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
            except:
                pass

        def build_menu_layout():
            nonlocal menu_layout
            term_width, _ = self.get_terminal_size()

            max_option_len = max(
                len(opt.split(None, 1)[1] if len(opt.split(None, 1)) > 1 else opt)
                for opt in options
            )
            menu_width = max(max_option_len, len(title))
            left_padding = (term_width - menu_width) // 2

            total_lines = 1 + 1 + len(options) + 1
            v_padding = self.get_vertical_padding(total_lines)

            layout = {
                'v_padding': v_padding,
                'left_padding': left_padding,
                'title_line': v_padding,
                'options_start': v_padding + 2,
                'options': []
            }

            for i, opt in enumerate(options):
                opt_text = opt.split(None, 1)[1] if len(opt.split(None, 1)) > 1 else opt
                layout['options'].append({
                    'line': layout['options_start'] + i,
                    'text': opt_text,
                    'unselected': f"  {opt_text}",
                    'selected': f"{theme_color}› {opt_text}\033[0m"
                })

            layout['footer_line'] = layout['options_start'] + len(options) + 1
            return layout

        def render_option(line_num, option_data, is_selected):
            layout = menu_layout
            print(f"\033[{line_num + 1};{layout['left_padding'] + 1}H", end="", flush=True)
            text = option_data['selected'] if is_selected else option_data['unselected']
            print(f"\033[K{text}", end="", flush=True)

        try:
            while True:
                if needs_render:
                    menu_layout = build_menu_layout()
                    newline = "\r\n" if os.name != "nt" else "\n"

                    output_buffer = []
                    output_buffer.append("\033[H\033[J")
                    output_buffer.append(newline * menu_layout['v_padding'])

                    title_text = f"\033[90m{title}\033[0m"
                    title_padding = menu_layout['left_padding'] + (len(menu_layout['options'][0]['text']) - len(title)) // 2
                    output_buffer.append(" " * title_padding + title_text + newline)
                    output_buffer.append(newline)

                    for i, opt_data in enumerate(menu_layout['options']):
                        text = opt_data['selected'] if i == selected else opt_data['unselected']
                        output_buffer.append(" " * menu_layout['left_padding'] + text + newline)

                    output_buffer.append(newline)
                    output_buffer.append(self.center_text(f"\033[90m↑ ↓ navigate • enter select • esc cancel\033[0m", strip_ansi=True))

                    print("".join(output_buffer), end="", flush=True)
                    needs_render = False
                    previous_selected = selected

                if os.name == "nt":
                    if msvcrt.kbhit():
                        char = msvcrt.getch()
                        if char == b"\x03":
                            raise KeyboardInterrupt
                        elif char == b"\x1b":
                            return None
                        elif char == b"\r":
                            return str(selected + 1)
                        elif char == b"\xe0" or char == b"\x00":
                            arrow = msvcrt.getch()
                            if arrow == b"H":
                                previous_selected = selected
                                selected = (selected - 1) % len(options)
                            elif arrow == b"P":
                                previous_selected = selected
                                selected = (selected + 1) % len(options)
                        elif char == b"\x48":
                            previous_selected = selected
                            selected = (selected - 1) % len(options)
                        elif char == b"\x50":
                            previous_selected = selected
                            selected = (selected + 1) % len(options)

                        if previous_selected != selected:
                            render_option(menu_layout['options'][previous_selected]['line'],
                                        menu_layout['options'][previous_selected], False)
                            render_option(menu_layout['options'][selected]['line'],
                                        menu_layout['options'][selected], True)
                            previous_selected = selected

                    time.sleep(0.02)
                else:
                    char = sys.stdin.read(1)
                    if char == "\x03":
                        raise KeyboardInterrupt
                    elif char == "\x1b":
                        fd = sys.stdin.fileno()
                        old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                        fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

                        try:
                            seq = sys.stdin.read(2)
                            if not seq:
                                return None
                            if seq == "[A":
                                previous_selected = selected
                                selected = (selected - 1) % len(options)
                            elif seq == "[B":
                                previous_selected = selected
                                selected = (selected + 1) % len(options)

                            if previous_selected != selected:
                                render_option(menu_layout['options'][previous_selected]['line'],
                                            menu_layout['options'][previous_selected], False)
                                render_option(menu_layout['options'][selected]['line'],
                                            menu_layout['options'][selected], True)
                                previous_selected = selected
                        except EOFError:
                            return None
                        finally:
                            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
                    elif char in ("\r", "\n"):
                        return str(selected + 1)

        finally:
            if os.name != "nt":
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except:
                    pass

    def change_mode(self):
        """Mode selection"""
        try:
            choice = self.show_menu("mode", ["1  words", "2  quotes"])
            if choice == "1":
                self.engine.set_mode("words")
            elif choice == "2":
                self.engine.set_mode("quotes")
            self._needs_full_render = True
            self._needs_render = True
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
            self._needs_full_render = True
            self._needs_render = True
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
            self._needs_full_render = True
            self._needs_render = True
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

        if os.name != "nt":
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

        try:
            if os.name != "nt":
                tty.setraw(sys.stdin.fileno())

            self.hide_cursor()

            # Initial render
            self._needs_full_render = True
            self.render()
            self.last_term_size = self.get_terminal_size()

            while self.running:
                try:
                    # Check for terminal resize
                    current_term_size = self.get_terminal_size()
                    if current_term_size != self.last_term_size:
                        self.last_term_size = current_term_size
                        self._needs_full_render = True
                        self._needs_render = True

                    # Periodic render for timer updates (only if test is running)
                    current_time = time.time()
                    if self.engine.started and not self.engine.paused:
                        if (current_time - self.last_render_time) >= 0.5:
                            self._needs_render = True

                    # Check if time is up
                    if self.engine.started and self.engine.is_time_up() and not self._test_ending:
                        self.show_results()
                        continue

                    # Render if needed
                    if self._needs_render:
                        if self._needs_full_render:
                            self.initial_render = True
                        self.render()

                    # Handle input
                    if os.name == "nt":
                        if msvcrt.kbhit():
                            char = msvcrt.getch()

                            if self.warning_shown:
                                if char == b"\x03":
                                    raise KeyboardInterrupt
                                continue

                            if char == b"\x03":
                                raise KeyboardInterrupt
                            elif char == b"\x12":  # Ctrl+R
                                self.engine.generate_text()
                                self._needs_full_render = True
                                self._needs_render = True
                            elif char == b"\x0d":  # Ctrl+M
                                self.change_mode()
                                self.hide_cursor()
                            elif char == b"\x04":  # Ctrl+D
                                self.change_difficulty()
                                self.hide_cursor()
                            elif char == b"\x14":  # Ctrl+T
                                self.change_theme()
                                self.hide_cursor()
                            elif char == b"\x10":  # Ctrl+P
                                if self.engine.started:
                                    if self.engine.paused:
                                        self.engine.resume()
                                    else:
                                        self.engine.pause()
                                    self._needs_render = True
                            elif char == b"\x08":  # Backspace
                                self.engine.delete_character()
                            else:
                                try:
                                    text = char.decode("utf-8")
                                    if text.isprintable() and len(text) == 1:
                                        self.engine.type_character(text)
                                        self._check_test_complete()
                                except UnicodeDecodeError:
                                    pass

                    else:
                        rlist, _, _ = select.select([sys.stdin], [], [], 0)
                        if rlist:
                            char = sys.stdin.read(1)

                            if self.warning_shown:
                                if char == "\x03":
                                    raise KeyboardInterrupt
                                continue

                            if char == "\x03":
                                raise KeyboardInterrupt
                            elif char == "\x12":  # Ctrl+R
                                self.engine.generate_text()
                                self._needs_full_render = True
                                self._needs_render = True
                            elif char == "\x0d":  # Ctrl+M
                                self.change_mode()
                                self.hide_cursor()
                            elif char == "\x04":  # Ctrl+D
                                self.change_difficulty()
                                self.hide_cursor()
                            elif char == "\x14":  # Ctrl+T
                                self.change_theme()
                                self.hide_cursor()
                            elif char == "\x10":  # Ctrl+P
                                if self.engine.started:
                                    if self.engine.paused:
                                        self.engine.resume()
                                    else:
                                        self.engine.pause()
                                    self._needs_render = True
                            elif char == "\x7f" or char == "\x08":  # Backspace
                                self.engine.delete_character()
                            elif char.isprintable():
                                self.engine.type_character(char)
                                self._check_test_complete()

                    time.sleep(0.01)

                except KeyboardInterrupt:
                    self.running = False
                    break
        finally:
            self.show_cursor()

            if os.name != "nt":
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            # Goodbye message
            self.clear_screen()
            newline = "\r\n" if os.name != "nt" else "\n"
            v_padding = self.get_vertical_padding(1)
            print(newline * v_padding, end="", flush=True)
            goodbye_text = "\033[90mgoodbye\033[0m"
            print(self.center_text(goodbye_text, strip_ansi=True) + newline, end="", flush=True)

if __name__ == "__main__":
    app = CLITypingTest()
    app.run()

import re
import sys
import os
import time
import shutil
from src.core.engine import TypingTestEngine

if os.name != "nt":
    import fcntl  # For non-blocking input on Linux

class CLITypingTest:
    def __init__(self):
        self.engine = TypingTestEngine()
        self.running = True
        self.content_width = 50
        self.MIN_W, self.MIN_H = 60, 15
        self.last_render_lines = 0  # Track number of lines rendered
        self.initial_render = True
        self.last_term_size = (0, 0)  # Track terminal size for resize detection
        self.warning_shown = False  # Track if terminal size warning is being displayed
        self.last_render_time = 0  # Track last render time for periodic updates
        self.cursor_hidden = False  # Track cursor visibility state
        
        
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
            return 80, 24  # Default fallback size

    def show_terminal_size_warning(self, cols, rows, min_cols, min_rows):
        """
        Display a visible warning if terminal is smaller than recommended size.
        Non-intrusive: shown only once at the top. 
        """
        self.warning_shown = True
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
        
        # Update render time
        self.last_render_time = time.time()
        
        # Build content first to count lines
        content_lines = []

        term_width, term_height = self.get_terminal_size()

        # Show visible warning if too small
        if term_width < self.MIN_W or term_height < self.MIN_H:
            self.show_terminal_size_warning(term_width, term_height, self.MIN_W, self.MIN_H)
            return
        
        # Clear warning flag since we're rendering normal content
        self.warning_shown = False
        
        # Paused indicator (above timer if paused)
        theme_color = self.hex_to_ansi(self.engine.accent_color)
        if getattr(self.engine, "paused", False):
            content_lines.append("\033[93mPAUSED\033[0m")
            content_lines.append("")  # Empty line after paused text
        
        # Timer display (above text)
        if self.engine.started:
            time_remaining = int(self.engine.get_time_remaining())
            timer_display = f"{theme_color}{time_remaining}s\033[0m"
        else:
            time_limit = int(self.engine.time_limit)
            timer_display = f"{theme_color}{time_limit}s\033[0m"
        
        content_lines.append(timer_display)
        content_lines.append("")  # Empty line after timer
        
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

        # Stats (wpm and accuracy only, no time)
        if self.engine.started:
            accuracy, wpm = self.engine.calculate_stats()
            stats = f"\033[90mwpm\033[0m {theme_color}{wpm:.0f}\033[0m  \033[90macc\033[0m {theme_color}{accuracy:.0f}%\033[0m"
        else:
            stats = f"\033[90mstart typing...\033[0m"
        content_lines.append(stats)

        # Build entire output as atomic operation to prevent flicker
        if self.initial_render:
            self.initial_render = False

        # Add vertical padding
        v_padding = self.get_vertical_padding(len(content_lines))

        # Use proper line endings
        newline = "\r\n" if os.name != "nt" else "\n"

        # Build output buffer - include cursor positioning and clear in same print
        output_buffer = []
        output_buffer.append("\033[H\033[J")  # Home + clear atomically
        output_buffer.append(newline * v_padding)

        # Print centered content
        for line in content_lines:
            if line == "":
                output_buffer.append(newline)
            elif "wpm" in line or "start typing" in line:  # Stats line
                output_buffer.append(self.center_text(line, strip_ansi=True) + newline)
            else:  # Text lines or timer
                output_buffer.append(self.center_text(line, strip_ansi=True) + newline)
        output_buffer.append(newline)

        # Footer
        mode_info = f"\033[90m{self.engine.mode} \033[37m|\033[90m {self.engine.difficulty}\033[0m"
        shortcuts = f"{theme_color}^M\033[0m mode  {theme_color}^D\033[0m difficulty  {theme_color}^T\033[0m theme  {theme_color}^R\033[0m restart  {theme_color}^C\033[0m quit  {theme_color}^P\033[0m {"resume" if self.engine.paused else "pause"}"

        output_buffer.append(self.center_text(mode_info, strip_ansi=True) + newline)
        output_buffer.append(newline)
        output_buffer.append(self.center_text(shortcuts, strip_ansi=True))

        # Write all at once
        print("".join(output_buffer), end="", flush=True)
        
        # Track lines rendered for next update
        self.last_render_lines = len(content_lines) + 3

    def show_results(self):
        """Display minimal results with flicker-free rendering"""
        accuracy, wpm = self.engine.calculate_stats()
        theme_color = self.hex_to_ansi(self.engine.accent_color)
        
        # Get personal best BEFORE saving to compare correctly
        pb = self.engine.get_personal_best()
        
        # Save test result to history
        self.engine.save_test_result(accuracy, wpm)
        
        # Check if this is a new personal best
        # A new PB is set if:
        # 1. First test for this mode/difficulty, OR
        # 2. WPM is higher, OR
        # 3. WPM is equal but accuracy is better
        is_new_pb = False
        if pb is None:
            is_new_pb = True
        elif wpm > pb.get("wpm", 0):
            is_new_pb = True
        elif wpm == pb.get("wpm", 0) and accuracy > pb.get("accuracy", 0):
            is_new_pb = True

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

        content_lines = []
        
        # Show personal best or new record
        if is_new_pb:
            content_lines.append(f"{theme_color}✦ New Personal Best ✦\033[0m")
        elif pb:
            content_lines.append(f"\033[90mBest: {pb['wpm']:.0f} WPM\033[0m")
        
        content_lines.append("")
        content_lines.append(f"\033[90mwpm\033[0m {wpm_color}{wpm:.0f}")
        content_lines.append(f"\033[90macc\033[0m {acc_color}{accuracy:.0f}%")
        content_lines.append("")
        content_lines.append("\033[90mpress enter to continue\033[0m")

        v_padding = self.get_vertical_padding(len(content_lines))
        newline = "\r\n" if os.name != "nt" else "\n"

        # Build atomic output buffer
        output_buffer = []
        output_buffer.append("\033[H\033[J")  # Home + clear atomically
        output_buffer.append(newline * v_padding)

        for line in content_lines:
            output_buffer.append(self.center_text(line, strip_ansi=True) + newline)

        print("".join(output_buffer), end="", flush=True)

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
        """Generic centered menu with arrow key navigation"""
        if os.name == "nt":
            import msvcrt
        else:
            import tty
            import termios

        selected = 0
        previous_selected = 0
        theme_color = self.hex_to_ansi(self.engine.accent_color)
        needs_render = True  # Full render needed
        menu_layout = {}  # Cache layout for incremental updates

        # Set raw mode for Linux
        if os.name != "nt":
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
            except:
                pass

        def build_menu_layout():
            """Build and cache the complete menu layout"""
            nonlocal menu_layout
            
            term_width, _ = self.get_terminal_size()
            
            # Find the longest option to determine menu width
            max_option_len = max(len(opt.split(None, 1)[1] if len(opt.split(None, 1)) > 1 else opt) for opt in options)
            menu_width = max(max_option_len, len(title))
            left_padding = (term_width - menu_width) // 2
            
            # Calculate vertical padding
            total_lines = 1 + 1 + len(options) + 1
            v_padding = self.get_vertical_padding(total_lines)
            
            layout = {
                'v_padding': v_padding,
                'left_padding': left_padding,
                'title_line': v_padding,
                'options_start': v_padding + 2,  # Title + blank line
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
            """Render a single option line at specific position"""
            layout = menu_layout
            # Move cursor to the specific line and column
            print(f"\033[{line_num + 1};{layout['left_padding'] + 1}H", end="", flush=True)
            text = option_data['selected'] if is_selected else option_data['unselected']
            # Clear the rest of the line and print
            print(f"\033[K{text}", end="", flush=True)

        try:
            while True:
                # Full render when needed
                if needs_render:
                    menu_layout = build_menu_layout()
                    
                    newline = "\r\n" if os.name != "nt" else "\n"

                    # Build entire output including screen clear as atomic operation
                    output_buffer = []
                    output_buffer.append("\033[H\033[J")  # Home cursor + clear screen
                    output_buffer.append(newline * menu_layout['v_padding'])
                    
                    # Center title
                    title_text = f"\033[90m{title}\033[0m"
                    title_padding = menu_layout['left_padding'] + (len(menu_layout['options'][0]['text']) - len(title)) // 2
                    output_buffer.append(" " * title_padding + title_text + newline)
                    output_buffer.append(newline)

                    # Render options
                    for i, opt_data in enumerate(menu_layout['options']):
                        text = opt_data['selected'] if i == selected else opt_data['unselected']
                        output_buffer.append(" " * menu_layout['left_padding'] + text + newline)

                    output_buffer.append(newline)
                    output_buffer.append(self.center_text(f"\033[90m↑ ↓ navigate • enter select • esc cancel\033[0m", strip_ansi=True))

                    print("".join(output_buffer), end="", flush=True)
                    needs_render = False
                    previous_selected = selected

                # Handle input
                if os.name == "nt":
                    if msvcrt.kbhit():
                        char = msvcrt.getch()
                        if char == b"\x03":  # Ctrl+C
                            raise KeyboardInterrupt
                        elif char == b"\x1b":  # Escape
                            return None
                        elif char == b"\r":  # Enter
                            return str(selected + 1)
                        elif char == b"\xe0" or char == b"\x00":  # Arrow key prefix on Windows
                            arrow = msvcrt.getch()
                            if arrow == b"H":  # Up arrow
                                previous_selected = selected
                                selected = (selected - 1) % len(options)
                            elif arrow == b"P":  # Down arrow
                                previous_selected = selected
                                selected = (selected + 1) % len(options)
                        elif char == b"\x48":  # Up arrow (some terminals)
                            previous_selected = selected
                            selected = (selected - 1) % len(options)
                        elif char == b"\x50":  # Down arrow (some terminals)
                            previous_selected = selected
                            selected = (selected + 1) % len(options)
                        
                        # Incremental update for arrow keys
                        if previous_selected != selected:
                            render_option(menu_layout['options'][previous_selected]['line'], 
                                        menu_layout['options'][previous_selected], False)
                            render_option(menu_layout['options'][selected]['line'], 
                                        menu_layout['options'][selected], True)
                            previous_selected = selected
                            
                    time.sleep(0.02)
                else:
                    char = sys.stdin.read(1)
                    if char == "\x03":  # Ctrl+C
                        raise KeyboardInterrupt
                    elif char == "\x1b":  # Escape or arrow key
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
                            
                            # Incremental update
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
            # Restore terminal settings on Linux
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

            # Hide cursor (only once)
            self.hide_cursor()

            self.render()
            self.last_term_size = self.get_terminal_size()
            last_input_len = 0

            while self.running:
                try:
                    # Check for terminal resize
                    current_term_size = self.get_terminal_size()
                    if current_term_size != self.last_term_size:
                        self.last_term_size = current_term_size
                        self.render()
                        last_input_len = len(self.engine.user_input)
                    
                    # Periodic render to update timer (every 0.5 seconds)
                    current_time = time.time()
                    if self.engine.started and (current_time - self.last_render_time) >= 0.5:
                        self.last_render_time = current_time
                        self.render()
                    
                    # Check if time is up
                    if self.engine.started and self.engine.is_time_up():
                        self.show_results()
                        last_input_len = -1
                        continue
                    
                    if os.name == "nt":
                        # Windows
                        if msvcrt.kbhit():
                            char = msvcrt.getch()

                            # Skip all input processing if warning is shown
                            if self.warning_shown:
                                if char == b"\x03":  # Still allow Ctrl+C to quit
                                    raise KeyboardInterrupt
                                continue

                            if char == b"\x03":  # Ctrl+C
                                raise KeyboardInterrupt
                            elif char == b"\x12":  # Ctrl+R
                                self.engine.generate_text()
                                self.initial_render = True
                                last_input_len = -1  # Force re-render
                            elif char == b"\x0d":  # Ctrl+M
                                self.change_mode()
                                self.hide_cursor()
                                last_input_len = -1
                            elif char == b"\x04":  # Ctrl+D
                                self.change_difficulty()
                                self.hide_cursor()
                                last_input_len = -1
                            elif char == b"\x14":  # Ctrl+T
                                self.change_theme()
                                self.hide_cursor()
                                last_input_len = -1
                            elif char == b"\x10":  # Ctrl+P pause/resume
                                if self.engine.started:
                                    if self.engine.paused:
                                        self.engine.resume()
                                    else:
                                        self.engine.pause()
                                    self.render()
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
                                    # Block typing while paused
                                    if self.engine.paused:
                                        pass
                                    elif text.isprintable() and len(text) == 1:
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

                            # Skip all input processing if warning is shown
                            if self.warning_shown:
                                if char == "\x03":  # Still allow Ctrl+C to quit
                                    raise KeyboardInterrupt
                                continue

                            if char == "\x03":  # Ctrl+C
                                raise KeyboardInterrupt
                            elif char == "\x12":  # Ctrl+R
                                self.engine.generate_text()
                                self.initial_render = True
                                last_input_len = -1
                            elif char == "\x0d":  # Ctrl+M
                                self.change_mode()
                                self.hide_cursor()
                                last_input_len = -1
                            elif char == "\x04":  # Ctrl+D
                                self.change_difficulty()
                                self.hide_cursor()
                                last_input_len = -1
                            elif char == "\x14":  # Ctrl+T
                                self.change_theme()
                                self.hide_cursor()
                                last_input_len = -1
                            elif char == "\x10":  # Ctrl+P pause/resume
                                if self.engine.started:
                                    if self.engine.paused:
                                        self.engine.resume()
                                    else:
                                        self.engine.pause()
                                    self.render()
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
                            elif self.engine.paused:
                                pass
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
            # Restore cursor
            self.show_cursor()
            
            # Restore terminal settings on Linux
            if os.name != "nt":
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            # Show goodbye message - properly centered
            self.clear_screen()
            newline = "\r\n" if os.name != "nt" else "\n"
            v_padding = self.get_vertical_padding(1)
            print(newline * v_padding, end="", flush=True)
            goodbye_text = "\033[90mgoodbye\033[0m"

            # FIX: Added + newline here to satisfy the shell requirements
            print(self.center_text(goodbye_text, strip_ansi=True) + newline, end="", flush=True)

if __name__ == "__main__":
    app = CLITypingTest()
    app.run()
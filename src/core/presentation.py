"""
Presentation helpers for the typing test.

Contains rendering logic that doesn't belong in the engine.
Each UI layer (CLI/GUI) uses these to format engine state for display.
"""

import html


def colorize_text_for_gui(current_text: str, user_input: str, accent_color: str) -> str:
    """
    Generate HTML for GUI display with colored characters.
    Returns HTML string ready for QTextEdit.
    """
    spans = []
    typed_len = len(user_input)
    zws_middot = "&middot;&#8203;"
    default_color = "#6b7280"  # gray
    wrong_color = "#ef4444"  # red

    for i, c in enumerate(current_text):
        # Determine display char
        if c == " ":
            display_char = " "
        else:
            display_char = html.escape(c)

        # Determine style
        if i > typed_len:
            # Untyped section
            color = default_color
            underline = False
        elif i == typed_len:
            # Current character
            color = "#ffffff"
            underline = True
        else:
            # Typed section
            typed_char = user_input[i]
            underline = False
            if typed_char == c:
                color = accent_color
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


def get_display_length_for_gui(current_text: str, user_input: str) -> int:
    """
    Calculate display position for cursor in GUI.
    Accounts for expanded incorrect spaces (middot + ZWS = 2 chars).
    """
    length = 0
    for i in range(len(user_input)):
        if i < len(current_text):
            c = current_text[i]
            typed = user_input[i]
            if typed != " " and c == " ":
                length += 2  # &middot; + &#8203;
            else:
                length += 1
    return length


def colorize_char_for_cli(expected: str, accent_color: str) -> str:
    """
    Colorize an expected character for CLI display (typed correctly).
    Returns ANSI-colored string.
    """
    theme_color = _hex_to_ansi(accent_color)
    return f"{theme_color}{expected}\033[0m"


def wrong_char_for_cli(expected: str) -> str:
    """
    Show the expected character in red (for incorrectly typed chars).
    """
    return f"\033[91m{expected}\033[0m"


def wrong_space_for_cli() -> str:
    """Show a dot for incorrectly typed space."""
    return "\033[91m·\033[0m"


def untyped_char_for_cli(char: str) -> str:
    """Format untyped character for CLI"""
    return f"\033[90m{char}\033[0m"


def current_char_for_cli(char: str) -> str:
    """Format current (cursor) character for CLI"""
    return f"\033[4m{char}\033[0m"


def _hex_to_ansi(hex_color: str) -> str:
    """Convert hex color to ANSI TrueColor escape sequence"""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"

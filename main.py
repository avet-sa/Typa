"""
Typing Test Application - Main Entry Point

A typing test application with both GUI and CLI modes.
Run with --mode cli for terminal interface or --mode gui for desktop GUI.
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Typing Test Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Run GUI mode (default)
  python main.py --mode gui   # Run GUI mode (explicit)
  python main.py --mode cli   # Run CLI mode
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Run in GUI or CLI mode (default: gui)",
    )
    args = parser.parse_args()

    if args.mode == "cli":
        from src.cli.cli_app import CLITypingTest

        app = CLITypingTest()
        app.run()
    else:
        from PyQt6.QtWidgets import QApplication
        from src.gui.widget import TypingTest

        app = QApplication(sys.argv)
        window = TypingTest()
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

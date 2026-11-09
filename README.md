# Typing Test (CLI + GUI)

> **A sleek typing speed trainer with dual interface support.**  
> Practice your typing with real-time feedback, track your progress, and improve your speed across multiple modes and difficulties.

A fast, polished, cross-platform typing test featuring:

- **CLI Mode** (beautiful ANSI rendering with flicker-free updates)
- **GUI Mode** (PyQt6 with modern responsive design)
- Real-time statistics with countdown timer and pause/resume
- Words / Quotes modes with configurable difficulty
- Live WPM and accuracy tracking
- **Test history tracking** with personal bests per mode/difficulty
- **Pause/resume** functionality to take breaks mid-test
- Config auto-saving with theme persistence
- Terminal size safety + centered warnings

This project is built with a clean engine–UI separation and supports both terminal and graphical interfaces.


## Dual Interface
#### **CLI Version**
- Smooth, flicker-free ANSI render engine  
- Centered text layout with dynamic terminal resize support
- Highlighting of correct, incorrect, and untyped characters  
- Cross-platform keyboard handling (Windows + Linux)  
- Terminal too small? Graceful centered warning  
- Word mode / Quote mode with multiple difficulty levels
- Pause/resume with Ctrl+P
- Visual dimming effect when paused
- Restart, Stop, Switch Mode shortcuts  

#### **GUI Version (PyQt6)**
- Modern, responsive typing test with clean interface
- Real-time WPM / Accuracy with large timer display
- Pause/resume with Ctrl+P and visual overlay
- Text auto-centers for short prompts (< 4 lines)
- Difficulty and mode settings with theme customization
- Auto-saving config with 8 color themes
- Custom widgets (clean architecture)
- Preloaded special characters for smooth rendering


## Project Structure
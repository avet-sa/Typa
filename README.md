# 🧪 Typing Test (CLI + GUI)

> **A sleek, feature-rich typing speed trainer with dual interface support.**  
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


## **✨ Dual Interface**
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


## 📦 Project Structure

```

project/
├─ main.py
├─ src/
│   ├─ core/
│   │    └─ engine.py
│   ├─ cli/
│   │    └─ cli_app.py
│   └─ gui/
│        ├─ widget.py
│        └─ components/
├─ assets/
│   ├─ words.txt
│   └─ quotes.txt
└─ config.json

```



## ⌨️ Shortcuts (CLI)

| Action             | Keys        |
|-------------------|-------------|
| Pause/Resume      | **Ctrl+P**  |
| Restart test      | **Ctrl+R**  |
| Switch mode       | **Ctrl+M**  |
| Change difficulty | **Ctrl+D**  |
| Change theme      | **Ctrl+T**  |
| Quit              | **Ctrl+C**  |


## ⌨️ Shortcuts (GUI)

| Action             | Keys        |
|-------------------|-------------|
| Pause/Resume      | **Ctrl+P**  |
| Restart test      | **Tab**     |
| Quit              | **Esc**     |


## 🎯 Modes & Difficulty

### **Modes**
- **Words** - Practice with random word combinations
  - 10 words (30s)
  - 25 words (60s)
  - 50 words (90s)
  - 100 words (120s)
- **Quotes** - Type complete sentences and phrases
  - Short (45s, < 60 chars)
  - Medium (60s, 60-120 chars)
  - Long (90s, ≥ 120 chars)

### **Timer System**
Each mode/difficulty has a time limit. Tests automatically finish when:
- Time runs out, OR
- You complete the text

You can pause at any time with **Ctrl+P** without affecting your statistics.


## 📊 Statistics & History

Every completed test is automatically saved to `history.json` including:
- Timestamp
- WPM and accuracy scores
- Mode and difficulty used
- Text length and typed characters

### Personal Bests
The app tracks your highest WPM for each mode/difficulty combination. When comparing records:
- Higher WPM wins, OR
- Equal WPM → Higher accuracy wins

Displays:
- ✦ **New Personal Best** when you beat your previous record
- Your current PB when viewing results

### Pause/Resume
- Press **Ctrl+P** to pause the test at any time
- Timer freezes and typing is disabled
- Visual dimming effect indicates paused state
- WPM calculation excludes pause time
- Resume by pressing **Ctrl+P** again


## 📁 Assets

Place your custom text sources here:

```
assets/
words.txt
quotes.txt
```

Simple plain-text lists work perfectly.


## ⚙️ Installation

Install dependencies:

```bash
pip install -r requirements.txt
````



## ▶️ Usage

### **Run CLI**

```bash
python main.py --mode cli
```

### **Run GUI**

```bash
python main.py [gui | --mode gui] (defaults to gui)
```



## 🔧 Configuration

Settings are stored in `config.json` and automatically updated. Example:

```json
{
  "theme": "#22c55e",
  "mode": "words",
  "difficulty": "25"
}
```

**Available Themes:**
- Green (`#22c55e`) - Default
- Blue (`#3b82f6`)
- Purple (`#a855f7`)
- Orange (`#f97316`)
- Pink (`#ec4899`)
- Red (`#ef4444`)
- Cyan (`#06b6d4`)
- Yellow (`#eab308`)



## 🧩 Architecture

**Clean Separation of Concerns:**

* **`engine.py`** - Core logic layer
  - Text generation (words/quotes)
  - WPM and accuracy calculations
  - Timer system with pause support
  - HTML-safe rendering with color codes
  - History tracking and personal bests
  - Excludes pause time from statistics

* **`cli_app.py`** - Terminal interface
  - Flicker-free ANSI render engine
  - Color manager with dimming support
  - Cross-platform keyboard handling
  - Centered UI layout with dynamic resize
  - Real-time timer updates (0.5s intervals)

* **`widget.py`** - PyQt6 GUI interface
  - Modern widget composition
  - Signal-based event handling
  - Live stat updates (100ms intervals)
  - Config persistence
  - Special character preloading
  - Dynamic text centering for short prompts

This clean separation makes the project easy to extend and maintain. The engine has zero UI dependencies and can be reused in any interface.




## ⭐ Credits

Built with ❤️ as a clean, modern Python typing test with both terminal and GUI support.
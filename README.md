# 🧪 Typing Test (CLI + GUI)

A fast, polished, cross-platform typing test featuring:

- **CLI Mode** (beautiful ANSI rendering)
- **GUI Mode** (PyQt6)
- Real-time statistics with countdown timer
- Words / Quotes modes
- Difficulty levels
- Live WPM and accuracy tracking
- **Test history tracking** with personal bests
- **Export to CSV** for analysis
- Config auto-saving  
- Terminal size safety + centered warnings

This project is built with a clean engine–UI separation and supports both terminal and graphical interfaces.


## **✨ Dual Interface**
#### **CLI Version**
- Smooth, flicker-free ANSI render engine  
- Centered text layout  
- Highlighting of correct, incorrect, and untyped characters  
- Cross-platform keyboard handling (Windows + Linux)  
- Terminal too small? Graceful centered warning  
- Word mode / Quote mode
- Restart, Stop, Switch Mode shortcuts  

#### **GUI Version (PyQt6)**
- Modern, responsive typing test  
- Real-time WPM / Accuracy
- Difficulty and mode settings  
- Auto-saving config  
- Custom widgets (clean architecture)


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
| Restart test      | **Ctrl+R**  |
| Switch mode       | **Ctrl+M**  |
| Change difficulty | **Ctrl+D**  |
| Change theme      | **Ctrl+T**  |
| Export history    | **Ctrl+E**  |
| Quit              | **Ctrl+C**  |


## 🎯 Modes & Difficulty

### **Modes**
- **Words** (random word list)
- **Quotes** (random multi-line quotes)

### **Difficulty**
- Easy / Normal / Hard  
Controls text length and density.


## 📊 Statistics & History

Every completed test is automatically saved to `history.json` including:
- Timestamp
- WPM and accuracy scores
- Mode and difficulty used
- Text length and typed characters

### Personal Bests
The app tracks your highest WPM for each mode/difficulty combination and displays:
- 🏆 **New Personal Best!** when you beat your previous record
- Your current PB when viewing results

### Export
Press **Ctrl+E** in CLI mode to export your complete test history to CSV format for further analysis.


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

Settings are stored in:

```
config.json
```

Automatically updated by the GUI. Example:

```json
{
  "difficulty": "normal",
  "mode": "words"
}
```



## 🧩 Architecture

* `engine.py`
  Pure logic: text generation, WPM, accuracy, HTML-safe rendering.

* `cli_app.py`
  Terminal renderer, color manager, keyboard reader, UI layout.

* `widget.py`
  PyQt GUI: widgets, signals, stat updates, config loading.

This clean separation makes the project easy to extend and maintain.




## ⭐ Credits

Built with ❤️ as a clean, modern Python typing test with both terminal and GUI support.
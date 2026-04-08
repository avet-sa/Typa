"""
Typing Test Engine - Core domain logic

Handles: text generation, timing, stats calculation, config, history.
No presentation/rendering logic belongs here.
"""

import os
import random
import time
import html
import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class CharTiming:
    """Timing data for a single character"""
    index: int
    timestamp: float
    is_correct: bool


@dataclass
class EngineState:
    """
    Read-only snapshot of engine state for UI consumption.
    UI should read from this, never access engine internals directly.
    """
    current_text: str
    user_input: str
    started: bool
    paused: bool
    time_remaining: float
    time_limit: float
    mode: str
    difficulty: str
    accent_color: str
    wpm: float
    accuracy: float
    is_new_personal_best: bool
    personal_best: Optional[dict] = None
    wpm_history: list = field(default_factory=list)  # [(elapsed_seconds, wpm), ...]


@dataclass
class TestResult:
    """Complete result of a typing test"""
    wpm: float
    accuracy: float
    mode: str
    difficulty: str
    time_limit: float
    timestamp: str
    is_new_personal_best: bool
    personal_best: Optional[dict] = None
    wpm_history: list = field(default_factory=list)  # Cumulative: [(elapsed_seconds, wpm), ...]
    burst_history: list = field(default_factory=list)  # Per-word bursts: [(elapsed_seconds, burst_wpm), ...]


class TypingTestEngine:
    def __init__(self, base_path: str = None):
        # Resolve base path (injectable for testing, defaults to project root)
        if base_path is None:
            base_path = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        self.base_path = base_path

        # Asset paths
        self.words = self._load_file(os.path.join(base_path, "assets", "words.txt"))
        self.quotes = self._load_file(os.path.join(base_path, "assets", "quotes.txt"))
        self.config_path = os.path.join(base_path, "config.json")
        self.history_path = os.path.join(base_path, "history.json")

        # State
        self.mode = "words"
        self.difficulty = "25"
        self.accent_color = "#22c55e"

        # Test state
        self.current_text = ""
        self.user_input = ""
        self.started = False
        self.start_time = 0.0
        self.time_limit = 60
        self.paused = False
        self.pause_started_at = 0.0
        self.total_pause_duration = 0.0

        # Timing data (for graph and incremental stats)
        self._char_timings: list[CharTiming] = []
        self._correct_count = 0  # Incremental correct count
        self._wpm_snapshots: list[tuple[float, float]] = []  # (elapsed_sec, wpm)
        self._last_wpm_calc_time = 0.0

        # Burst tracking (per-word WPM like MonkeyType)
        self._word_start_time = 0.0  # elapsed when current word started
        self._word_start_index = 0   # char index where current word started
        self._burst_history: list[tuple[float, float]] = []  # (elapsed_seconds, burst_wpm)

        # Personal best tracking
        self._last_test_result: Optional[TestResult] = None

        # Callbacks (UI subscribes to these)
        self.on_char_typed = lambda: None
        self.on_stats_updated = lambda state: None
        self.on_test_complete = lambda result: None

        # Load config and generate initial text
        self._load_config()
        self.generate_text()

    # ─── Config ───────────────────────────────────────────────────

    def _load_config(self):
        """Load config from disk (engine owns config)"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    self.accent_color = config.get("theme", "#22c55e")
                    self.mode = config.get("mode", "words")
                    self.difficulty = config.get(
                        "difficulty",
                        "25" if self.mode == "words" else "medium"
                    )
        except Exception:
            pass

    def save_config(self):
        """Save config to disk"""
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

    # ─── File I/O ─────────────────────────────────────────────────

    def _load_file(self, filename: str) -> list[str]:
        """Load lines from a text file"""
        if not os.path.exists(filename):
            return []
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    # ─── History & Personal Best ──────────────────────────────────

    def _load_history(self) -> dict:
        """Load test history from JSON"""
        try:
            if os.path.exists(self.history_path):
                with open(self.history_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"tests": [], "personal_bests": {}}

    def _save_history(self, history: dict):
        """Save test history to JSON"""
        try:
            with open(self.history_path, "w") as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            print(f"Error saving history: {e}")

    def get_personal_best(self, mode: str = None, difficulty: str = None) -> Optional[dict]:
        """Get personal best for mode/difficulty (None = current)"""
        history = self._load_history()
        mode = mode or self.mode
        difficulty = difficulty or self.difficulty
        key = f"{mode}_{difficulty}"
        return history["personal_bests"].get(key)

    def get_test_history(self, limit: int = None, mode: str = None, difficulty: str = None) -> list[dict]:
        """Get test history, optionally filtered"""
        history = self._load_history()
        tests = history["tests"]

        if mode:
            tests = [t for t in tests if t["mode"] == mode]
        if difficulty:
            tests = [t for t in tests if t["difficulty"] == difficulty]

        tests.sort(key=lambda x: x["timestamp"], reverse=True)

        if limit:
            tests = tests[:limit]

        return tests

    def get_statistics(self) -> Optional[dict]:
        """Get overall statistics"""
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

    def _save_test_result(self, accuracy: float, wpm: float) -> TestResult:
        """Save test result and update personal best. Returns TestResult."""
        history = self._load_history()
        timestamp = datetime.now().isoformat()

        # Create test record
        test_record = {
            "timestamp": timestamp,
            "mode": self.mode,
            "difficulty": self.difficulty,
            "wpm": round(wpm, 2),
            "accuracy": round(accuracy, 2),
            "time_limit": self.time_limit,
            "text_length": len(self.current_text),
            "typed_length": len(self.user_input)
        }

        history["tests"].append(test_record)

        # Check/update personal best
        key = f"{self.mode}_{self.difficulty}"
        current_best = history["personal_bests"].get(key, {"wpm": 0, "accuracy": 0})

        is_new_best = False
        if wpm > current_best.get("wpm", 0):
            is_new_best = True
        elif wpm == current_best.get("wpm", 0) and accuracy > current_best.get("accuracy", 0):
            is_new_best = True

        pb_info = None
        if is_new_best:
            history["personal_bests"][key] = {
                "wpm": round(wpm, 2),
                "accuracy": round(accuracy, 2),
                "timestamp": timestamp
            }
            pb_info = history["personal_bests"][key]

        self._save_history(history)

        return TestResult(
            wpm=round(wpm, 2),
            accuracy=round(accuracy, 2),
            mode=self.mode,
            difficulty=self.difficulty,
            time_limit=self.time_limit,
            timestamp=timestamp,
            is_new_personal_best=is_new_best,
            personal_best=pb_info,
            wpm_history=list(self._wpm_snapshots)
        )

    # ─── Text Generation ─────────────────────────────────────────

    def _get_time_limit(self) -> int:
        """Calculate time limit based on mode and difficulty"""
        if self.mode == "words":
            word_count = int(self.difficulty)
            if word_count <= 10:
                return 30
            elif word_count <= 25:
                return 60
            elif word_count <= 50:
                return 90
            else:
                return 120
        else:
            if self.difficulty == "short":
                return 45
            elif self.difficulty == "medium":
                return 60
            else:
                return 90

    def generate_text(self):
        """Generate new typing text based on mode/difficulty"""
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

        self.time_limit = self._get_time_limit()
        self.reset_input()

    # ─── Test Control ─────────────────────────────────────────────

    def start(self):
        """Start the typing test"""
        if not self.started:
            self.started = True
            self.start_time = time.time()
            self.paused = False
            self.pause_started_at = 0.0
            self.total_pause_duration = 0.0

    def reset_input(self):
        """Reset input and test state"""
        self.user_input = ""
        self.started = False
        self.start_time = 0.0
        self.paused = False
        self.pause_started_at = 0.0
        self.total_pause_duration = 0.0
        self._char_timings = []
        self._correct_count = 0
        self._wpm_snapshots = []
        self._last_wpm_calc_time = 0.0
        self._burst_history = []
        self._word_start_time = 0.0
        self._word_start_index = 0
        self._last_test_result = None

    def type_character(self, char: str) -> bool:
        """
        Type a character. Returns True if input was accepted.
        Fires on_char_typed and on_stats_updated callbacks.
        """
        if self.paused:
            return False

        current_index = len(self.user_input)
        if current_index >= len(self.current_text):
            return False

        self.user_input += char

        # Auto-start on first char
        if not self.started:
            self.start()

        # Track timing incrementally
        elapsed = time.time() - self.start_time - self.total_pause_duration
        expected_char = self.current_text[current_index]
        is_correct = (char == expected_char)

        self._char_timings.append(CharTiming(
            index=current_index,
            timestamp=elapsed,
            is_correct=is_correct
        ))

        if is_correct:
            self._correct_count += 1

        # Burst tracking: detect word boundaries (space typed = word ended)
        if char == " " or current_index == len(self.current_text) - 1:
            # Calculate burst WPM for completed word
            word_chars = current_index - self._word_start_index + 1
            if current_index == len(self.current_text) - 1:
                word_chars = current_index - self._word_start_index + 1
            else:
                word_chars = current_index - self._word_start_index

            word_time = elapsed - self._word_start_time
            if word_time > 0.01 and word_chars > 0:
                burst_wpm = (word_chars / 5.0) / (word_time / 60.0)
                burst_wpm = min(burst_wpm, 300)  # cap at 300 WPM
                self._burst_history.append((elapsed, round(burst_wpm, 1)))

            # Start new word tracking
            self._word_start_time = elapsed
            self._word_start_index = current_index + 1

        # Capture cumulative WPM snapshot every 0.5 seconds
        if elapsed - self._last_wpm_calc_time >= 0.5:
            _, wpm = self._calculate_stats_internal()
            self._wpm_snapshots.append((elapsed, wpm))
            self._last_wpm_calc_time = elapsed

        # Fire callbacks
        self.on_char_typed()
        self.on_stats_updated(self.get_state())

        return True

    def delete_character(self, delete_word: bool = False) -> bool:
        """
        Delete last character (or word). Returns True if deletion occurred.
        """
        if not self.user_input:
            return False

        if delete_word:
            if self.user_input.strip():
                words = self.user_input.rstrip().split(" ")
                new_input = " ".join(words[:-1]) + (" " if len(words) > 1 else "")
            else:
                new_input = ""
        else:
            # Check if deleting a correct space (don't allow)
            last_idx = len(self.user_input) - 1
            is_correct_space = (
                self.user_input[-1] == " "
                and self.current_text[last_idx] == " "
            )
            if is_correct_space:
                return False
            new_input = self.user_input[:-1]

        # Recalculate incremental stats for new length
        self.user_input = new_input
        self._recalculate_incremental_stats()

        self.on_char_typed()
        self.on_stats_updated(self.get_state())

        return True

    def _recalculate_incremental_stats(self):
        """Recalculate correct count and timings after deletion"""
        new_len = len(self.user_input)

        # Remove timings beyond new length
        self._char_timings = [t for t in self._char_timings if t.index < new_len]

        # Recalculate correct count
        self._correct_count = sum(1 for t in self._char_timings if t.is_correct)

    def pause(self):
        """Pause the test"""
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

    def is_time_up(self) -> bool:
        """Check if time limit reached"""
        if not self.started or self.paused:
            return False
        elapsed = time.time() - self.start_time - self.total_pause_duration
        return elapsed >= self.time_limit

    def get_time_remaining(self) -> float:
        """Get remaining time in seconds"""
        if not self.started:
            return self.time_limit
        if self.paused:
            elapsed = self.pause_started_at - self.start_time - self.total_pause_duration
        else:
            elapsed = time.time() - self.start_time - self.total_pause_duration
        return max(0.0, self.time_limit - elapsed)

    def finish_test(self) -> Optional[TestResult]:
        """
        Complete the test. Returns TestResult or None if test hasn't started.
        Fires on_test_complete callback.
        """
        if not self.started or not self.user_input:
            return None

        # Final WPM snapshot
        accuracy, wpm = self._calculate_stats_internal()
        elapsed = self._get_elapsed_time()
        self._wpm_snapshots.append((elapsed, wpm))

        # Save and get result
        result = self._save_test_result(accuracy, wpm)
        self._last_test_result = result
        # Attach burst history to result
        result.burst_history = list(self._burst_history)

        # Fire callback
        self.on_test_complete(result)

        return result

    # ─── Stats Calculation ────────────────────────────────────────

    def _get_elapsed_time(self) -> float:
        """Get elapsed time excluding pauses"""
        if self.paused:
            return self.pause_started_at - self.start_time - self.total_pause_duration
        return time.time() - self.start_time - self.total_pause_duration

    def _calculate_stats_internal(self) -> tuple[float, float]:
        """
        Internal stats calculation using incremental tracking.
        Returns (accuracy, wpm).
        """
        if not self.started or not self.user_input:
            return 0.0, 0.0

        elapsed = self._get_elapsed_time()
        minutes = max(elapsed / 60.0, 0.001)

        min_len = min(len(self.user_input), len(self.current_text))
        # Use incremental correct count if available, otherwise calculate
        if self._char_timings and len(self._char_timings) >= min_len:
            correct = self._correct_count
        else:
            # Fallback (e.g., right after deletion before recalc)
            correct = sum(
                1 for i in range(min_len)
                if self.user_input[i] == self.current_text[i]
            )

        accuracy = (correct / min_len) * 100 if min_len > 0 else 0.0
        wpm = len(self.user_input) / 5.0 / minutes

        return accuracy, wpm

    def calculate_stats(self) -> tuple[float, float]:
        """Public stats calculation (UI uses this)"""
        return self._calculate_stats_internal()

    def get_wpm_history(self) -> list[tuple[float, float]]:
        """Get WPM over time for graph: [(elapsed_seconds, wpm), ...]"""
        return list(self._wpm_snapshots)

    def get_burst_history(self) -> list[tuple[float, float]]:
        """Get per-word burst WPM for graph: [(elapsed_seconds, burst_wpm), ...]"""
        return list(self._burst_history)

    # ─── State Interface ──────────────────────────────────────────

    def get_state(self) -> EngineState:
        """
        Get a read-only snapshot of current engine state.
        UI should use this instead of accessing engine internals.
        """
        accuracy, wpm = self._calculate_stats_internal()
        pb = self.get_personal_best()

        return EngineState(
            current_text=self.current_text,
            user_input=self.user_input,
            started=self.started,
            paused=self.paused,
            time_remaining=self.get_time_remaining(),
            time_limit=self.time_limit,
            mode=self.mode,
            difficulty=self.difficulty,
            accent_color=self.accent_color,
            wpm=wpm,
            accuracy=accuracy,
            is_new_personal_best=False,  # Only set after test completes
            personal_best=pb,
            wpm_history=list(self._wpm_snapshots)
        )

    # ─── Settings ─────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """Change mode and regenerate text"""
        self.mode = mode
        if mode == "words":
            self.difficulty = "25"
        else:
            self.difficulty = "medium"
        self.save_config()
        self.generate_text()

    def set_difficulty(self, difficulty: str):
        """Change difficulty and regenerate text"""
        self.difficulty = difficulty
        self.save_config()
        self.generate_text()

    def set_accent_color(self, color: str):
        """Change accent color"""
        self.accent_color = color
        self.save_config()

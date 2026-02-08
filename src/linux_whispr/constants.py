"""Default values, paths, and version constants."""

from __future__ import annotations

import os
from pathlib import Path

# Version
VERSION = "0.1.0"
APP_NAME = "linux-whispr"
APP_ID = "com.github.linux-whispr"

# XDG directories
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

# Application directories
CONFIG_DIR = XDG_CONFIG_HOME / APP_NAME
DATA_DIR = XDG_DATA_HOME / APP_NAME
CACHE_DIR = XDG_CACHE_HOME / APP_NAME
MODELS_DIR = DATA_DIR / "models"

# Configuration files
CONFIG_FILE = CONFIG_DIR / "config.toml"
DICTIONARY_FILE = CONFIG_DIR / "dictionary.json"
SNIPPETS_FILE = CONFIG_DIR / "snippets.toml"

# Data files
HISTORY_DB = DATA_DIR / "history.db"

# Audio defaults
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_DTYPE = "int16"
AUDIO_BLOCKSIZE = 1024

# VAD defaults
VAD_THRESHOLD = 0.5
VAD_SILENCE_DURATION = 2.0  # seconds of silence before auto-stop
VAD_MIN_SPEECH_DURATION = 0.3  # minimum speech to consider valid

# Recording limits
MAX_RECORDING_DURATION = 360  # 6 minutes in seconds
RECORDING_WARNING_TIME = 330  # 5:30 warning

# STT defaults
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_WHISPER_MODEL_GPU = "large-v3-turbo"
SUPPORTED_WHISPER_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "large-v3-turbo",
    "distil-large-v3",
]

# Hotkey defaults
DEFAULT_DICTATION_HOTKEY = "F12"
DEFAULT_COMMAND_HOTKEY = "<Ctrl><Shift>h"

# Text injection
CLIPBOARD_RESTORE_DELAY = 0.5  # seconds to wait before restoring clipboard

# Adaptive dictionary
CORRECTION_WATCH_WINDOW = 15  # seconds to monitor clipboard after injection
CORRECTION_POLL_INTERVAL = 2  # seconds between clipboard polls
CORRECTION_PROMOTION_THRESHOLD = 2  # times a correction must be seen

# History
HISTORY_RETENTION_DAYS = 30

# Web dashboard
WEB_DEFAULT_PORT = 7865

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Technical Context — LinuxWhispr

## Technology Stack

### Core Language
- **Python 3.10+** — primary language for all components
- Type hints throughout (mypy strict)
- asyncio for concurrent operations (audio capture + VAD + UI updates)

### Audio
| Component | Library | Purpose |
|-----------|---------|---------|
| Audio capture | `sounddevice` (PortAudio binding) | Cross-platform mic recording |
| Audio format | 16kHz, 16-bit, mono WAV | Whisper's expected input format |
| VAD | `silero-vad` (via torch or ONNX) | Voice activity detection for auto-stop |
| Audio processing | `numpy` | Audio buffer manipulation |

### Speech-to-Text
| Backend | Library | Notes |
|---------|---------|-------|
| Local (default) | `faster-whisper` (CTranslate2) | 4x faster than original Whisper, lower memory |
| Local (alt) | `whisper.cpp` via subprocess | C++ implementation, good for CPU-only |
| Cloud: OpenAI | `openai` SDK | Whisper API endpoint |
| Cloud: Groq | `groq` SDK | Ultra-fast Whisper, great for latency |
| Cloud: AssemblyAI | `assemblyai` SDK | Alternative cloud option |

### AI Refinement (LLM)
| Backend | Library | Model Examples |
|---------|---------|---------------|
| Local | `llama-cpp-python` | Qwen2.5-3B-Instruct, Phi-3-mini, Gemma-2-2B |
| OpenAI | `openai` SDK | gpt-4o-mini (fast + cheap) |
| Anthropic | `anthropic` SDK | claude-3-haiku (fast + cheap) |
| Groq | `groq` SDK | llama-3.1-8b-instant (ultra-fast) |
| Google | `google-genai` SDK | gemini-2.0-flash-lite |

### Desktop Integration
| Component | X11 | Wayland (GNOME) | Wayland (wlroots) |
|-----------|-----|-----------------|-------------------|
| Global Hotkey | `python-xlib` (XGrabKey) | D-Bus GlobalShortcuts portal | D-Bus GlobalShortcuts portal or `wlr-foreign-toplevel` |
| Text Injection | `xdotool` (subprocess) | `wtype` (subprocess) | `wtype` (subprocess) |
| Text Injection (alt) | `xdotool` | `ydotool` (requires uinput) | `ydotool` |
| Clipboard | `xclip` or `xsel` | `wl-clipboard` (`wl-copy`/`wl-paste`) | `wl-clipboard` |
| Active Window | `xdotool getactivewindow getwindowname` | D-Bus or `swaymsg` | `swaymsg -t get_tree` |
| System Tray | `pystray` (libappindicator) | `pystray` (StatusNotifierItem) | `pystray` or custom D-Bus |

### UI Framework
| Component | Library | Notes |
|-----------|---------|-------|
| Overlay | `GTK4` + `pygobject` | Transparent floating window |
| Overlay (Wayland) | `gtk4-layer-shell` | Layer shell protocol for always-on-top |
| Settings Window | `GTK4` + `libadwaita` | Native GNOME-style settings |
| Theming | Follow system theme | Via libadwaita AdwStyleManager |

### Data & Configuration
| Component | Library/Format | Notes |
|-----------|---------------|-------|
| Configuration | `tomli`/`tomli-w` (TOML) | `~/.config/linux-whispr/config.toml` |
| History DB | `sqlite3` (stdlib) | `~/.local/share/linux-whispr/history.db` |
| Secrets | `secretstorage` (libsecret) | GNOME Keyring / KWallet for API keys |
| Logging | `logging` (stdlib) + `rich` | Structured logging with rotation |

### Packaging & Distribution
| Format | Tool | Notes |
|--------|------|-------|
| PyPI | `hatchling` / `hatch` | `pip install linux-whispr` |
| AppImage | `appimage-builder` | Distribution-independent binary |
| AUR | PKGBUILD | Arch Linux |
| DEB | `stdeb` or `fpm` | Debian/Ubuntu |
| RPM | `fpm` | Fedora/RHEL |
| Systemd | User service file | Auto-start on login |

## Directory Structure

```
linux-whispr/
├── pyproject.toml                  # Project metadata, dependencies, build config
├── README.md
├── LICENSE                         # MIT
├── .specify/                       # Speckit files
│   └── memory/
│       └── constitution.md
├── specs/
│   └── 001-linux-whispr/
│       ├── spec.md
│       ├── scenarios.md
│       └── technical-context.md
├── src/
│   └── linux_whispr/
│       ├── __init__.py
│       ├── __main__.py             # Entry point: `python -m linux_whispr`
│       ├── app.py                  # Main application orchestrator
│       ├── config.py               # Configuration loading/saving (TOML)
│       ├── constants.py            # Default values, paths, version
│       │
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── capture.py          # Microphone recording (sounddevice)
│       │   ├── vad.py              # Voice Activity Detection (Silero)
│       │   └── devices.py          # Audio device enumeration
│       │
│       ├── stt/
│       │   ├── __init__.py
│       │   ├── base.py             # Abstract STT backend interface
│       │   ├── faster_whisper.py   # faster-whisper local backend
│       │   ├── openai_api.py       # OpenAI Whisper API backend
│       │   ├── groq_api.py         # Groq Whisper API backend
│       │   └── model_manager.py    # Download, list, delete Whisper models
│       │
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── base.py             # Abstract LLM backend interface
│       │   ├── refinement.py       # Text refinement pipeline + prompt templates
│       │   ├── command.py          # Command Mode processing
│       │   ├── local_llm.py        # llama-cpp-python backend
│       │   ├── openai_llm.py       # OpenAI GPT backend
│       │   ├── anthropic_llm.py    # Anthropic Claude backend
│       │   ├── groq_llm.py         # Groq LLM backend
│       │   └── prompts/
│       │       ├── refinement.py   # System prompts for text refinement by context
│       │       └── command.py      # System prompts for command mode
│       │
│       ├── input/
│       │   ├── __init__.py
│       │   ├── hotkey.py           # Global hotkey listener (X11/Wayland)
│       │   ├── x11_hotkey.py       # X11 XGrabKey implementation
│       │   └── wayland_hotkey.py   # D-Bus GlobalShortcuts implementation
│       │
│       ├── output/
│       │   ├── __init__.py
│       │   ├── injector.py         # Text injection orchestrator
│       │   ├── clipboard.py        # Clipboard operations (xclip/wl-clipboard)
│       │   ├── xdotool.py          # xdotool paste simulation
│       │   ├── wtype.py            # wtype paste simulation
│       │   └── ydotool.py          # ydotool paste simulation
│       │
│       ├── features/
│       │   ├── __init__.py
│       │   ├── snippets.py         # Snippet trigger/expansion engine
│       │   ├── dictionary.py       # Custom dictionary manager
│       │   └── history.py          # Transcription history (SQLite)
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── overlay.py          # Floating overlay (GTK4)
│       │   ├── tray.py             # System tray icon
│       │   ├── settings.py         # Settings window (GTK4 + libadwaita)
│       │   └── wizard.py           # First-run setup wizard
│       │
│       └── platform/
│           ├── __init__.py
│           ├── detect.py           # Detect display server, DE, available tools
│           ├── autostart.py        # Manage systemd user service / XDG autostart
│           └── notifications.py    # Desktop notifications (D-Bus)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Shared fixtures (mock audio, config)
│   ├── test_audio_capture.py
│   ├── test_vad.py
│   ├── test_stt_backends.py
│   ├── test_ai_refinement.py
│   ├── test_command_processor.py
│   ├── test_text_injector.py
│   ├── test_snippets.py
│   ├── test_dictionary.py
│   ├── test_history.py
│   ├── test_config.py
│   ├── test_hotkey.py
│   └── test_platform_detect.py
│
├── data/
│   ├── icons/                      # App icons (SVG + PNG at various sizes)
│   ├── sounds/                     # Audio feedback sounds (start/stop beeps)
│   └── linux-whispr.desktop        # XDG desktop entry
│
└── packaging/
    ├── appimage/                   # AppImage build config
    ├── aur/                        # PKGBUILD for AUR
    ├── deb/                        # Debian packaging files
    ├── rpm/                        # RPM spec file
    └── systemd/
        └── linux-whispr.service    # Systemd user service
```

## Key Dependencies (pyproject.toml)

```toml
[project]
name = "linux-whispr"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    # Audio
    "sounddevice>=0.4.6",
    "numpy>=1.24",

    # STT - Local
    "faster-whisper>=1.0.0",

    # VAD
    "onnxruntime>=1.16",           # For Silero VAD without full torch

    # AI - Local LLM (optional)
    # "llama-cpp-python>=0.2.0",   # Optional: local LLM

    # AI - Cloud (optional, user installs what they need)
    # "openai>=1.0",
    # "anthropic>=0.20",
    # "groq>=0.4",

    # UI
    "PyGObject>=3.46",             # GTK4 bindings
    "pystray>=0.19",               # System tray

    # Config & Data
    "tomli>=2.0; python_version < '3.11'",
    "tomli-w>=1.0",

    # Secrets
    "secretstorage>=3.3",

    # Utilities
    "rich>=13.0",                  # Logging, progress bars
]

[project.optional-dependencies]
cloud = [
    "openai>=1.0",
    "anthropic>=0.20",
    "groq>=0.4",
    "google-genai>=0.4",
]
local-llm = [
    "llama-cpp-python>=0.2.0",
]
all = [
    "linux-whispr[cloud,local-llm]",
]

[project.scripts]
linux-whispr = "linux_whispr.__main__:main"
```

## System Dependencies (must be installed via package manager)

### Required
- `python3.10+` — runtime
- `portaudio19-dev` — for sounddevice audio capture
- `gtk4` + `libadwaita-1` — for UI
- `gobject-introspection` — for PyGObject

### Text Injection (at least one)
- `wl-clipboard` — clipboard for Wayland (`wl-copy`, `wl-paste`)
- `xclip` or `xsel` — clipboard for X11
- `wtype` — keystroke simulation for Wayland
- `xdotool` — keystroke simulation for X11

### Optional
- `ydotool` — universal keystroke simulation (Wayland, needs uinput)
- NVIDIA CUDA drivers — for GPU-accelerated transcription

### Install Commands

```bash
# Ubuntu/Debian
sudo apt install python3-dev portaudio19-dev libgtk-4-dev libadwaita-1-dev \
    gobject-introspection libgirepository1.0-dev \
    wl-clipboard xdotool xclip

# Fedora
sudo dnf install python3-devel portaudio-devel gtk4-devel libadwaita-devel \
    gobject-introspection-devel \
    wl-clipboard xdotool xclip

# Arch Linux
sudo pacman -S python portaudio gtk4 libadwaita \
    gobject-introspection \
    wl-clipboard xdotool xclip
```

## Display Server Detection Logic

```
1. Check $XDG_SESSION_TYPE:
   - "wayland" → Wayland path
   - "x11" → X11 path
   - unset → check $WAYLAND_DISPLAY

2. Wayland path:
   a. Check $XDG_CURRENT_DESKTOP for compositor:
      - "GNOME" → D-Bus GlobalShortcuts portal + wtype
      - "KDE" → D-Bus GlobalShortcuts portal + wtype
      - "sway" / "Hyprland" → wlr protocols + wtype
   b. Hotkey: D-Bus org.freedesktop.portal.GlobalShortcuts
   c. Text injection: wtype → ydotool → clipboard-only
   d. Clipboard: wl-copy / wl-paste
   e. Active window: D-Bus or compositor IPC

3. X11 path:
   a. Hotkey: python-xlib XGrabKey
   b. Text injection: xdotool
   c. Clipboard: xclip / xsel
   d. Active window: xdotool getactivewindow getwindowname
```

## AI Refinement Prompt Templates

### General Dictation
```
You are a voice-to-text post-processor. Clean up the following raw transcription:
- Remove filler words (um, uh, like, you know, so, basically)
- Fix grammar and punctuation
- Apply proper capitalization
- Handle self-corrections (keep only the final intended version)
- Do NOT change the meaning or add information
- Do NOT add formatting unless the context suggests it
- Output ONLY the cleaned text, no explanations

Context: The user is typing in {app_name}.
Raw transcription: {raw_text}
```

### Email Context
```
You are a voice-to-text post-processor for email dictation. Clean up the raw transcription:
- Remove filler words
- Format as a proper email (greeting, body paragraphs, sign-off if present)
- Professional but natural tone
- Fix grammar and punctuation
- Handle self-corrections
- Output ONLY the cleaned email text

Raw transcription: {raw_text}
```

### Code Context
```
You are a voice-to-text post-processor for code dictation. Clean up the raw transcription:
- Remove filler words
- If it sounds like a code comment, format as a comment (# for Python, // for JS, etc.)
- Preserve technical terminology exactly
- Handle self-corrections
- Output ONLY the cleaned text

Active file context: {app_name}
Raw transcription: {raw_text}
```

### Chat/Messaging Context
```
You are a voice-to-text post-processor for chat messages. Clean up the raw transcription:
- Remove filler words but keep casual tone
- Fix grammar lightly (keep contractions, informal language)
- Handle self-corrections
- Output ONLY the cleaned text

Raw transcription: {raw_text}
```

### Command Mode
```
You are an AI text assistant. The user has spoken a command about text they have selected.

User's command: {command_text}
Selected text: {selected_text}

Execute the command on the selected text. Output ONLY the resulting text, no explanations.
```

## Event System

The application uses an internal event bus for component communication:

| Event | Source | Consumers |
|-------|--------|-----------|
| `hotkey.dictation.start` | Hotkey Listener | Audio Capture, Overlay |
| `hotkey.dictation.stop` | Hotkey Listener | Audio Capture |
| `hotkey.command.start` | Hotkey Listener | Audio Capture, Overlay |
| `hotkey.command.stop` | Hotkey Listener | Audio Capture |
| `audio.level` | Audio Capture | Overlay |
| `audio.ready` | Audio Capture | STT Engine |
| `audio.silence` | VAD | Audio Capture (auto-stop) |
| `stt.started` | STT Engine | Overlay |
| `stt.complete` | STT Engine | AI Refinement / Text Injector |
| `ai.started` | AI Refinement | Overlay |
| `ai.complete` | AI Refinement | Text Injector |
| `inject.complete` | Text Injector | Overlay, History |
| `inject.error` | Text Injector | Overlay (show error) |
| `state.change` | App State | All UI components |

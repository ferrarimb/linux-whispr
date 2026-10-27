# LinuxWhispr

**Privacy-first, open-source voice dictation for Linux** — a system-wide dictation tool that replicates the full experience of [Wispr Flow](https://wisprflow.com), with AI-powered text refinement, context awareness, and seamless integration into any text field.

## Features

- 🎤 **System-wide dictation** — works in any text field (browsers, IDEs, terminals, chat apps)
- 🔒 **Privacy-first** — local-first transcription via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), no cloud by default
- 🧠 **AI text refinement** — removes filler words, fixes grammar, adapts to context (email/code/chat)
- ⌨️ **Global hotkey** — configurable hotkey works regardless of focused window (X11 + Wayland)
- 🗣️ **Voice commands** — "make this more formal", "summarize the selected text"
- 📚 **Custom dictionary** — teach it your names, technical terms, brand names
- 🔄 **Adaptive learning** — automatically learns corrections you make
- 🌍 **99+ languages** — automatic language detection via Whisper
- 🖥️ **Linux native** — GTK4 + libadwaita UI, PipeWire/PulseAudio audio, X11 + Wayland support

## Quick Start

### System Dependencies

Install the system dependencies for your distribution.

**Ubuntu/Debian (including Debian 13):**

```bash
sudo apt install python3-venv python3-dev portaudio19-dev \
    libgtk-4-dev libadwaita-1-dev \
    gobject-introspection libgirepository1.0-dev \
    wl-clipboard xdotool xclip
```

**Fedora:**

```bash
sudo dnf install python3-devel portaudio-devel gtk4-devel \
    libadwaita-devel gobject-introspection-devel \
    wl-clipboard xdotool xclip
```

**Arch Linux:**

```bash
sudo pacman -S python portaudio gtk4 libadwaita \
    gobject-introspection wl-clipboard xdotool xclip
```

### Install

Install LinuxWhispr from the source repository in a virtual environment:

```bash
# Clone the repository
git clone https://github.com/ferrarimb/linux-whispr.git
cd linux-whispr

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install LinuxWhispr
python -m pip install --upgrade pip
python -m pip install .
```

### Run

Activate the virtual environment if it is not already active, then start LinuxWhispr:

```bash
source .venv/bin/activate
linux-whispr
```

On first run, a default config will be created at `~/.config/linux-whispr/config.toml`. The Whisper `base` model will be downloaded on first dictation (~150MB).

Avoid using `sudo pip install` or `--break-system-packages` to install the application.

## Usage

1. Press **F12** (default hotkey) to start recording.
2. Speak your text.
3. Press **F12** again to stop (or wait for auto-stop after 2s of silence).
4. Text appears at your cursor position.

## Configuration

Edit `~/.config/linux-whispr/config.toml`:

```toml
[hotkey]
dictation = "F12"
command = "<Ctrl><Shift>h"
mode = "toggle"  # or "push-to-talk"

[stt]
backend = "faster-whisper"
model = "base"           # tiny, base, small, medium, large-v3, large-v3-turbo
device = "auto"          # auto, cpu, cuda

[ai]
enabled = false          # enable AI text refinement
backend = "none"         # none, local, openai, anthropic, groq

[audio]
silence_duration = 2.0   # seconds of silence before auto-stop
silence_threshold = 0.5  # VAD sensitivity (0.0-1.0)

[injection]
method = "auto"          # auto, wtype, xdotool, ydotool, clipboard-only
preserve_clipboard = true
```

## Development

```bash
# Clone the repository
git clone https://github.com/ferrarimb/linux-whispr.git
cd linux-whispr

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
python -m pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## Architecture

```text
Hotkey → Audio Capture → VAD (auto-stop) → STT (faster-whisper) → AI Refinement (optional) → Text Injection
```

Components communicate via an internal event bus. See `specs/001-linux-whispr/spec.md` for the full specification.

## License

MIT

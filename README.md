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

### Install

```bash
pip install linux-whispr
```

### Run

```bash
linux-whispr
```

On first run, a default config will be created at `~/.config/linux-whispr/config.toml`. The Whisper `base` model will be downloaded on first dictation (~150MB).

### Usage

1. Press **F12** (default hotkey) to start recording
2. Speak your text
3. Press **F12** again to stop (or wait for auto-stop after 2s of silence)
4. Text appears at your cursor position

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
# Clone
git clone https://github.com/your-username/linux-whispr.git
cd linux-whispr

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## Architecture

```
Hotkey → Audio Capture → VAD (auto-stop) → STT (faster-whisper) → AI Refinement (optional) → Text Injection
```

Components communicate via an internal event bus. See `specs/001-linux-whispr/spec.md` for the full specification.

## License

MIT

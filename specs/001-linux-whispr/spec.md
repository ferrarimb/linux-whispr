# Specification: LinuxWhispr — Voice Dictation System for Linux

## Overview

LinuxWhispr is a system-wide voice dictation application for Linux that replicates the functionality of Wispr Flow. It allows users to dictate text into any application using a global hotkey, with AI-powered transcription and optional text refinement. The application runs as a background daemon with a minimal floating overlay for visual feedback and a system tray icon for quick access to settings.

## Problem Statement

Linux users have no equivalent to Wispr Flow — a seamless, system-wide voice dictation tool that:
- Works in every text field across all applications
- Uses AI to clean up and format transcriptions intelligently
- Understands context (email vs. code vs. chat) to adapt output style
- Removes filler words, fixes grammar, and handles corrections naturally
- Supports custom vocabularies and voice commands

Existing Linux solutions (nerd-dictation, basic Whisper scripts) are fragmented, lack polish, and miss the AI refinement layer that makes Wispr Flow transformative.

## Target Users

1. **Developers** — dictate code comments, commit messages, documentation, AI chat prompts
2. **Writers & Knowledge Workers** — draft emails, documents, notes, blog posts by voice
3. **Accessibility Users** — people who need or prefer voice input over keyboard
4. **Power Users** — anyone wanting 150+ WPM input speed

## Functional Requirements

### FR-1: Global Hotkey Activation

- **FR-1.1**: A configurable global hotkey (default: `Hyper_L` / Caps Lock remapped, or `F12`) starts/stops recording from anywhere in the system.
- **FR-1.2**: Two activation modes:
  - **Toggle Mode** (default): Press once to start, press again to stop.
  - **Push-to-Talk Mode**: Hold to record, release to stop.
- **FR-1.3**: A second hotkey (default: `Ctrl+Shift+H`) activates **Command Mode** for AI commands instead of plain dictation.
- **FR-1.4**: Hotkeys must work regardless of which window has focus.
- **FR-1.5**: Hotkey registration must support both X11 (`Xlib`) and Wayland (`D-Bus GlobalShortcuts portal` or `wlr-foreign-toplevel`).

### FR-2: Audio Capture

- **FR-2.1**: Record audio from the default microphone using PipeWire (preferred) or PulseAudio.
- **FR-2.2**: Audio format: 16kHz, 16-bit, mono WAV (Whisper's expected input).
- **FR-2.3**: Voice Activity Detection (VAD) using Silero VAD to:
  - Auto-stop recording after configurable silence duration (default: 2 seconds).
  - Skip empty/silent recordings.
- **FR-2.4**: Visual audio level indicator in the overlay to confirm mic is picking up audio.
- **FR-2.5**: Support selecting specific audio input device in settings.
- **FR-2.6**: Maximum recording duration: 6 minutes (with visual countdown warning at 5:30).

### FR-3: Speech-to-Text Transcription

> **Note (2026 STT Landscape)**: Wispr Flow processes ALL transcription in the cloud (confirmed via their data-controls page). For our local-first approach, the best open-source models in 2026 are:
> - **Whisper Large V3 Turbo** (809M params, 6x faster than Large V3, 99+ languages, ~6GB VRAM) — best for multilingual
> - **Distil-Whisper Large V3** (756M params, 6x faster, within 1% WER of Large V3) — best for English-only speed
> - **NVIDIA Canary Qwen 2.5B** (5.63% WER, tops Open ASR Leaderboard) — best accuracy but English-only, requires NeMo toolkit
> - **faster-whisper** remains the best deployment wrapper: CTranslate2 backend, easy API, supports all Whisper variants

- **FR-3.1**: Primary STT engine: **faster-whisper** (CTranslate2-optimized Whisper) for local processing.
- **FR-3.2**: Supported Whisper models via faster-whisper: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3`.
- **FR-3.3**: Default model: `large-v3-turbo` if GPU available (~6GB VRAM, best speed/accuracy/multilingual balance); `distil-large-v3` if English-only; `base` as CPU-only fallback (~1GB RAM).
- **FR-3.4**: GPU acceleration via CUDA when NVIDIA GPU detected; CPU fallback otherwise. ROCm for AMD GPUs (stretch goal).
- **FR-3.5**: Language detection: automatic by default, with option to pin a specific language.
- **FR-3.6**: Multi-language support: all languages supported by Whisper (99+ languages).
- **FR-3.7**: Alternative cloud STT backends (opt-in, BYOK):
  - OpenAI Whisper API
  - Groq Whisper API (ultra-fast, 216x real-time factor)
  - AssemblyAI
- **FR-3.8**: Model management: download, switch, and delete models from the settings UI.
- **FR-3.9**: Future backend option: NVIDIA Canary Qwen 2.5B via NeMo for maximum English accuracy (stretch goal).

### FR-4: AI Text Refinement (Post-Processing)

- **FR-4.1**: After raw transcription, an LLM refines the text:
  - Remove filler words ("um", "uh", "like", "you know")
  - Fix grammar and punctuation
  - Apply proper capitalization
  - Handle self-corrections (e.g., "no wait, I meant..." → keeps only the correction)
- **FR-4.2**: Context-aware formatting:
  - Detect the active application (via `xdotool getactivewindow getwindowname` or D-Bus)
  - Adapt output style: casual for Slack/Discord, professional for email, technical for IDE/terminal
- **FR-4.3**: AI refinement is **optional** and can be toggled on/off. When off, raw transcription is used directly.
- **FR-4.4**: Supported LLM backends for refinement:
  - **Local**: llama.cpp with small models (Qwen2.5-3B, Phi-3-mini, Gemma-2-2B)
  - **Cloud (BYOK)**: OpenAI (GPT-4o-mini), Anthropic (Claude Haiku), Groq (Llama-3), Google (Gemini Flash)
- **FR-4.5**: Custom system prompts: users can customize the refinement behavior.
- **FR-4.6**: Processing pipeline: Audio → STT → (optional) AI Refinement → Text Output.

### FR-5: Command Mode

- **FR-5.1**: Activated by a separate hotkey (default: `Ctrl+Shift+H`) or by prefixing speech with a wake word (default: "Hey Whispr").
- **FR-5.2**: In Command Mode, spoken text is interpreted as an instruction to the AI, not as dictation.
- **FR-5.3**: Command types:
  - **Text transformation**: "Make this more formal", "Turn this into bullet points", "Summarize this"
  - **Text generation**: "Write a thank you email to John about the meeting"
  - **Editing**: "Fix the grammar in the selected text", "Translate this to Portuguese"
- **FR-5.4**: For transformation/editing commands, the currently selected text (via clipboard read) is used as context.
- **FR-5.5**: Command results replace the selected text or are inserted at cursor position.

### FR-6: Text Injection

- **FR-6.1**: Primary method: Copy to clipboard + simulate `Ctrl+V` paste.
- **FR-6.2**: Injection tool chain (auto-detected):
  1. `wtype` — for native Wayland compositors
  2. `ydotool` — for Wayland (universal, requires uinput)
  3. `xdotool` — for X11 and XWayland
- **FR-6.3**: Preserve original clipboard content: save clipboard before injection, restore after a brief delay.
- **FR-6.4**: Fallback: if no injection tool is available, copy to clipboard and notify user to paste manually.
- **FR-6.5**: Support for multi-line text injection (preserving newlines).

### FR-7: Floating Overlay UI

- **FR-7.1**: Minimal always-on-top floating widget showing current state:
  - **Idle**: small dot/icon (can be hidden)
  - **Recording**: pulsing red indicator + audio waveform/level
  - **Processing**: spinning/loading animation
  - **Done**: brief green checkmark, then return to idle
- **FR-7.2**: Overlay is draggable to any screen position.
- **FR-7.3**: Overlay position persists across sessions.
- **FR-7.4**: Overlay built with GTK4 + libadwaita for native Linux look, or as a frameless transparent window.
- **FR-7.5**: Overlay is click-through except for the widget itself (doesn't steal focus).
- **FR-7.6**: Double-click overlay to open settings panel.

### FR-8: System Tray Integration

- **FR-8.1**: System tray icon using StatusNotifierItem (SNI) protocol / libappindicator.
- **FR-8.2**: Tray icon menu:
  - Start/Stop dictation
  - Toggle AI refinement on/off
  - Open Settings
  - View recent transcriptions
  - Pause/Resume (disable hotkey temporarily)
  - Quit
- **FR-8.3**: Tray icon changes appearance based on state (idle/recording/processing).

### FR-9: Settings & Configuration

- **FR-9.1**: Settings stored in `~/.config/linux-whispr/config.toml`.
- **FR-9.2**: Settings UI: GTK4 window accessible from tray or overlay.
- **FR-9.3**: Configurable settings:
  - **General**: Hotkey bindings, activation mode (toggle/push-to-talk), auto-start on login
  - **Audio**: Input device selection, silence detection threshold, max recording duration
  - **Transcription**: STT backend (local/cloud), Whisper model selection, language, model download management
  - **AI Refinement**: Enable/disable, LLM backend selection, API keys (BYOK), custom system prompts
  - **Text Injection**: Injection method preference, clipboard preservation toggle
  - **Custom Dictionary**: Add/remove words, names, and technical terms
  - **Appearance**: Overlay position, theme (follow system), overlay visibility
  - **Privacy**: Data retention policy, audio deletion behavior
- **FR-9.4**: First-run setup wizard: guide user through microphone test, model download, and basic configuration.

### FR-10: Custom Dictionary

- **FR-10.1**: User-maintained list of words, names, and terms stored in `~/.config/linux-whispr/dictionary.json`.
- **FR-10.2**: Dictionary words are provided as `initial_prompt` context to Whisper for improved recognition.
- **FR-10.3**: Support for import/export of dictionary files.
- **FR-10.4**: Categories: personal names, technical terms, brand names, custom phrases.
- **FR-10.5**: Each dictionary entry stores: `word`, `source` (manual | auto-learned), `frequency` (usage count), `added_at` timestamp.

### FR-14: Adaptive Dictionary Learning (Correction Watching)

> **Reference**: This replicates Wispr Flow's key feature: "Flow learns your words as you go. When you correct a spelling, Flow adds it automatically to your personal dictionary."

- **FR-14.1**: After text injection, LinuxWhispr monitors the clipboard for a configurable window (default: 15 seconds).
- **FR-14.2**: Monitoring mechanism:
  - After pasting the transcribed text, poll the clipboard every 2 seconds for changes.
  - If the user selects and copies text that differs from what was injected, compare the two using difflib.
  - If a word was changed (e.g., "kubernetes" → "Kubernetes", "sequel alchemy" → "SQLAlchemy"), record it as a learned correction.
- **FR-14.3**: Learned corrections are stored in the dictionary with `source: "auto-learned"` and a confidence score that increases with repeated corrections.
- **FR-14.4**: After a correction is seen N times (default: 2), the word is promoted to the `initial_prompt` context for all future transcriptions.
- **FR-14.5**: Auto-learned words can be reviewed, confirmed, or deleted in the Settings dictionary UI.
- **FR-14.6**: Advanced mode (optional): Use `inotify` to watch the active file for changes (works for text editors that save to disk) as an alternative to clipboard polling.
- **FR-14.7**: Correction pairs are stored: `{"heard": "sequel alchemy", "corrected": "SQLAlchemy", "count": 5}` — this allows the AI refinement layer to also learn substitutions.
- **FR-14.8**: The AI refinement prompt includes learned corrections as context: "The user prefers these spellings: SQLAlchemy (not sequel alchemy), Kubernetes (not kubernetes)..."

### FR-11: Snippets / Voice Shortcuts

- **FR-11.1**: User-defined mappings from trigger phrases to expanded text.
- **FR-11.2**: Example: saying "my email" expands to `joao@example.com`.
- **FR-11.3**: Snippets stored in `~/.config/linux-whispr/snippets.toml`.
- **FR-11.4**: Snippet management via settings UI.

### FR-12: Transcription History

- **FR-12.1**: All transcriptions stored locally in SQLite database at `~/.local/share/linux-whispr/history.db`.
- **FR-12.2**: Each entry contains: timestamp, raw transcription, refined text, duration, app context, word count.
- **FR-12.3**: History browsable and searchable in settings UI.
- **FR-12.4**: Copy any past transcription to clipboard.
- **FR-12.5**: Delete individual entries or clear all history.
- **FR-12.6**: Optional auto-purge after configurable retention period (default: 30 days).

### FR-13: Whisper Mode (Low Volume Dictation)

- **FR-13.1**: Microphone gain boost mode for whispering in quiet environments.
- **FR-13.2**: Activated via separate hotkey or tray menu toggle.
- **FR-13.3**: Adjusts VAD sensitivity and audio gain to capture low-volume speech.

## Non-Functional Requirements

### NFR-1: Performance
- Hotkey-to-overlay response: < 100ms
- Transcription latency (base model, 10s audio, CPU): < 3 seconds
- Transcription latency (base model, 10s audio, GPU): < 1 second
- AI refinement latency (cloud): < 2 seconds
- AI refinement latency (local small model): < 3 seconds
- Idle memory usage: < 50MB (model loaded on-demand or kept warm based on config)
- Recording memory overhead: < 20MB additional

### NFR-2: Reliability
- Graceful recovery from microphone disconnection/reconnection
- Graceful handling of network failures (cloud backends)
- No data loss: if transcription fails, audio is saved temporarily for retry
- Process watchdog: auto-restart on crash

### NFR-3: Security
- API keys stored in system keyring (libsecret/GNOME Keyring/KWallet) or encrypted config
- No audio data transmitted without explicit user consent
- Temporary audio files stored in `/tmp` with restrictive permissions (0600)
- Optional: encrypt history database

### NFR-4: Compatibility
- Linux distributions: Ubuntu 22.04+, Fedora 38+, Arch Linux (rolling)
- Display servers: X11, Wayland (GNOME, KDE Plasma, Sway, Hyprland)
- Audio servers: PipeWire (preferred), PulseAudio
- Python 3.10+
- Desktop environments: GNOME, KDE Plasma, XFCE, i3/Sway, Hyprland

### NFR-5: Installation
- PyPI package: `pip install linux-whispr`
- Standalone AppImage for distribution-independent deployment
- AUR package for Arch Linux
- DEB package for Debian/Ubuntu
- RPM package for Fedora
- Flatpak (stretch goal)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     LinuxWhispr Daemon                       │
│                                                              │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Hotkey   │  │   Audio      │  │    Floating Overlay    │ │
│  │  Listener │──│   Capture    │  │    (GTK4/Wayland)      │ │
│  │ (X11/DBus)│  │ (PipeWire)   │  └────────────────────────┘ │
│  └──────────┘  └──────┬───────┘                              │
│                        │ WAV                                  │
│                        ▼                                      │
│              ┌──────────────────┐                             │
│              │   STT Engine     │                             │
│              │ (faster-whisper) │                             │
│              │ or Cloud API     │                             │
│              └────────┬─────────┘                             │
│                       │ raw text                              │
│                       ▼                                       │
│              ┌──────────────────┐                             │
│              │  AI Refinement   │                             │
│              │ (LLM: local or   │                             │
│              │  cloud, optional) │                             │
│              └────────┬─────────┘                             │
│                       │ refined text                          │
│                       ▼                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │    Snippet    │  │    Text      │  │   History          │ │
│  │    Engine     │──│   Injector   │  │   (SQLite)         │ │
│  │              │  │(wtype/xdotool)│  └────────────────────┘ │
│  └──────────────┘  └──────────────┘                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              System Tray (SNI/AppIndicator)              ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Settings UI (GTK4 + libadwaita)             ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### C1: Hotkey Listener Service
- Registers global hotkeys via X11 XGrabKey or Wayland D-Bus GlobalShortcuts portal
- Emits events: `recording_start`, `recording_stop`, `command_mode_start`, `command_mode_stop`
- Runs in a dedicated thread

### C2: Audio Capture Service
- Records from microphone via sounddevice (PortAudio) or direct PipeWire binding
- Streams audio to WAV buffer in memory
- Runs Silero VAD in parallel to detect speech/silence
- Emits events: `audio_ready(wav_bytes)`, `silence_detected`, `audio_level(float)`

### C3: STT Engine Service
- Accepts WAV audio, returns raw text
- Pluggable backends: FasterWhisperBackend, WhisperAPIBackend, GroqWhisperBackend
- Loads model lazily on first use (or keeps warm in memory based on config)
- Custom dictionary passed as `initial_prompt`

### C4: AI Refinement Service
- Accepts raw text + context (app name, mode), returns refined text
- Pluggable backends: LocalLLMBackend (llama-cpp-python), OpenAIBackend, AnthropicBackend, GroqBackend
- System prompt templates per context type (email, code, chat, general)
- Bypass mode: pass through raw text when disabled

### C5: Command Processor
- Parses voice commands from Command Mode
- Reads selected text from clipboard for transformation commands
- Routes to AI Refinement Service with appropriate prompt
- Returns processed text for injection

### C6: Text Injector Service
- Saves current clipboard → copies text → simulates paste → restores clipboard
- Auto-detects display server and available tools
- Handles multi-line text properly

### C7: Snippet Engine
- Pattern matching on transcribed text against user-defined triggers
- Expands matching triggers to their defined replacements before injection

### C8: Overlay UI
- GTK4 Layer Shell (Wayland) or override-redirect window (X11)
- State machine: Idle → Recording → Processing → Done → Idle
- Animates transitions between states
- Shows audio level during recording

### C9: System Tray
- SNI protocol via pystray or direct D-Bus
- Context menu for quick actions
- Icon state reflects application state

### C10: Settings Manager
- TOML configuration file reader/writer
- GTK4 + libadwaita settings window
- First-run wizard
- Model download manager with progress

### C11: History Manager
- SQLite database CRUD operations
- Search and filter functionality
- Auto-purge scheduler

## Data Flow: Normal Dictation

1. User presses hotkey → Hotkey Listener emits `recording_start`
2. Overlay transitions to Recording state (pulsing red)
3. Audio Capture begins recording from microphone
4. VAD monitors audio levels; Overlay shows audio level indicator
5. User presses hotkey again (or silence detected) → `recording_stop`
6. Overlay transitions to Processing state (spinner)
7. Audio Capture emits `audio_ready(wav_bytes)`
8. STT Engine transcribes WAV → raw text
9. AI Refinement (if enabled) refines raw text → refined text
10. Snippet Engine checks for trigger phrases → expanded text
11. Text Injector pastes text at cursor position
12. History Manager saves transcription record
13. Overlay shows brief success indicator → returns to Idle

## Data Flow: Command Mode

1. User presses Command Mode hotkey → `command_mode_start`
2. Overlay shows Command Mode indicator (different color, e.g., blue)
3. User speaks command (e.g., "Make the selected text more formal")
4. Recording stops → STT Engine transcribes command
5. Command Processor reads selected text via clipboard
6. Command Processor sends (command + selected text) to AI Refinement
7. AI returns transformed text
8. Text Injector replaces selected text with result
9. History Manager saves command + result

## Out of Scope (v1.0)

- Mobile companion app
- Real-time streaming transcription (word-by-word as you speak)
- Screen context awareness (reading screen content for context)
- Team/shared dictionary features
- Browser extension
- Meeting transcription / multi-speaker diarization
- Voice-controlled system commands (open apps, control media, etc.)

## Success Criteria

1. User can install and start dictating within 5 minutes
2. Transcription accuracy ≥ 95% for clear English speech (base model)
3. End-to-end latency (hotkey release → text appears) < 5 seconds on CPU
4. Works in Firefox, Chrome, VS Code, Terminal, Slack, Telegram, LibreOffice
5. Stable operation for 8+ hours without memory leaks or crashes
6. Works on both X11 and Wayland without user configuration

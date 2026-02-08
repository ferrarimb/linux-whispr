# Project Constitution — LinuxWhispr

## Mission

Build a privacy-first, open-source voice dictation system for Linux that replicates the full experience of Wispr Flow — system-wide dictation with AI-powered text refinement, context awareness, and seamless integration into any text field.

## Governing Principles

### 1. Privacy First
- Local-first processing: audio is transcribed on-device by default using OpenAI Whisper (via faster-whisper or whisper.cpp).
- Cloud processing is opt-in (BYOK — Bring Your Own Key) and never the default.
- Audio recordings are ephemeral: deleted immediately after transcription unless the user explicitly opts to keep them.
- No telemetry, no analytics, no data sent anywhere without explicit consent.

### 2. Linux Native
- First-class Linux citizen — not a port, not an afterthought.
- Support both X11 and Wayland (GNOME, KDE, Sway, Hyprland).
- Use native Linux APIs: PulseAudio/PipeWire for audio, D-Bus for system integration, xdotool/wtype/ydotool for text injection.
- System tray integration via libappindicator or StatusNotifierItem.

### 3. Universal Compatibility
- Works in ANY text field on the system — browsers, terminals, IDEs, chat apps, email clients.
- Text injection via clipboard + paste simulation (most reliable cross-toolkit approach).
- Fallback chain: wtype (Wayland) → ydotool (Wayland universal) → xdotool (X11) → clipboard-only.

### 4. Performance & Speed
- Sub-2-second transcription latency for typical utterances (< 30s audio).
- Minimal resource usage when idle (< 50MB RAM).
- GPU acceleration (CUDA/ROCm) when available, graceful CPU fallback.
- Startup time < 1 second for hotkey responsiveness.

### 5. User Experience
- Dead-simple activation: single configurable hotkey (default: Super+H or F12).
- Visual feedback: minimal floating overlay showing recording/processing state.
- Audio feedback: subtle sounds for start/stop recording.
- Zero-configuration for basic use — works out of the box after install.

### 6. Code Quality
- Python as primary language for rapid iteration and ecosystem access.
- Type hints throughout (mypy strict mode).
- Comprehensive test coverage: unit tests for all services, integration tests for pipelines.
- Clean architecture: clear separation between audio capture, transcription, AI processing, and text injection layers.

### 7. Extensibility
- Plugin-friendly architecture for custom post-processing.
- Support multiple STT backends (faster-whisper, whisper.cpp, cloud APIs).
- Support multiple LLM backends for AI refinement (local via llama.cpp, or cloud via OpenAI/Anthropic/Groq APIs).
- Custom dictionary support for domain-specific terminology.

### 8. Accessibility
- The application itself is an accessibility tool — treat this responsibility seriously.
- Support for whisper mode (low-volume dictation in quiet environments).
- Clear error messages and recovery paths.
- Keyboard-only operation (no mouse required).

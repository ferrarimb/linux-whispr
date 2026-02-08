# Prompt para Nova Thread — LinuxWhispr Implementation

Cole o seguinte prompt numa nova conversa:

---

## PROMPT:

Eu tenho um projeto chamado **LinuxWhispr** em `/home/joaoferrai/Codes/linux-whispr/` que é um clone open-source do Wispr Flow para Linux — um sistema de ditado por voz system-wide com AI refinement.

A especificação completa já está pronta seguindo o formato do GitHub Spec Kit. Os arquivos são:

1. **`.specify/memory/constitution.md`** — Princípios governantes do projeto (privacy-first, Linux-native X11+Wayland, Python, performance)
2. **`specs/001-linux-whispr/spec.md`** — Especificação funcional completa com 14 requisitos funcionais:
   - FR-1: Global Hotkey (toggle + push-to-talk, X11 via Xlib + Wayland via D-Bus portal)
   - FR-2: Audio Capture (sounddevice + PipeWire/PulseAudio + Silero VAD)
   - FR-3: STT via faster-whisper (default: large-v3-turbo com GPU, base como fallback CPU) + cloud BYOK (OpenAI, Groq)
   - FR-4: AI Text Refinement via LLM (remove fillers, fixa gramática, context-aware por app ativo)
   - FR-5: Command Mode (transformar/gerar texto por voz, lê texto selecionado)
   - FR-6: Text Injection (clipboard + wtype/xdotool/ydotool, preserva clipboard original)
   - FR-7: Floating Overlay (GTK4, estados: idle/recording/processing/done)
   - FR-8: System Tray (StatusNotifierItem)
   - FR-9: Settings UI (GTK4 + libadwaita)
   - FR-10: Custom Dictionary (initial_prompt do Whisper)
   - FR-11: Snippets / Voice Shortcuts
   - FR-12: Transcription History (SQLite)
   - FR-13: Whisper Mode (low volume dictation)
   - FR-14: Adaptive Dictionary Learning (monitora correções do usuário pós-injeção e aprende vocabulário automaticamente — feature-chave do Wispr Flow)
3. **`specs/001-linux-whispr/scenarios.md`** — 15 cenários de uso detalhados (first-run, browser dictation, VS Code, self-correction, command mode, snippets, whisper mode, multi-language, network failure, custom dictionary, long dictation, Wayland+GNOME, X11+i3, history search)
4. **`specs/001-linux-whispr/technical-context.md`** — Stack técnico completo:
   - Python 3.10+ com type hints (mypy strict)
   - faster-whisper (CTranslate2) para STT
   - GTK4 + libadwaita + PyGObject para UI
   - sounddevice para audio capture
   - Silero VAD (ONNX) para voice activity detection
   - llama-cpp-python para LLM local (opcional)
   - pystray para system tray
   - TOML config, SQLite history, secretstorage para API keys
   - Estrutura de diretórios completa do projeto
   - pyproject.toml com todas as dependências
   - Prompt templates para AI refinement por contexto
   - Sistema de eventos interno documentado
   - Lógica de detecção X11/Wayland documentada

**Leia todos os 4 arquivos de especificação e depois:**

1. Execute o passo `/speckit.plan` — Crie um plano técnico de implementação detalhado, definindo a ordem de implementação dos componentes, as dependências entre eles, e a arquitetura de código.

2. Execute o passo `/speckit.tasks` — Quebre o plano em tarefas executáveis e incrementais. Cada tarefa deve resultar em algo testável.

3. Execute o passo `/speckit.implement` — Comece a implementar tarefa por tarefa, começando pela fundação (config, platform detection, audio capture) e subindo até as features de alto nível (overlay UI, adaptive learning).

A prioridade é ter um MVP funcional o mais rápido possível: hotkey → gravar → transcrever → colar no campo de texto. Depois iteramos para adicionar AI refinement, command mode, adaptive learning, etc.

---

# Specification: LinuxWhispr Web Dashboard

## Overview

A lightweight web-based dashboard for LinuxWhispr that provides a browser-accessible interface for configuration management, transcription history browsing, dictionary/snippet management, model management, and real-time application status. This complements the existing GTK4 settings window, offering a more accessible UI that works regardless of desktop environment or GTK availability.

## Problem Statement

The current GTK4+libadwaita settings UI:
- Requires GTK4 and libadwaita to be installed (not always available on all setups)
- Cannot be accessed remotely or from a different machine
- Has limited layout flexibility for complex data views (history search, dictionary tables)
- Cannot be easily extended with rich visualizations (charts, statistics)

A web dashboard solves these by providing a universal, browser-based interface.

## Target Users

1. **All LinuxWhispr users** — easier access to settings without GTK dependency
2. **Headless/SSH users** — configure LinuxWhispr remotely
3. **Power users** — bulk management of dictionary, snippets, history

## Architecture

```
┌─────────────────────────────────────────────────┐
│              LinuxWhispr Daemon                   │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │        FastAPI Web Server (:7865)            │ │
│  │                                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐ │ │
│  │  │ REST API │  │  Static  │  │  WebSocket │ │ │
│  │  │ Endpoints│  │  Files   │  │  (status)  │ │ │
│  │  └────┬─────┘  └──────────┘  └─────┬─────┘ │ │
│  └───────┼─────────────────────────────┼───────┘ │
│          │                             │         │
│  ┌───────▼─────────────────────────────▼───────┐ │
│  │           Existing Core Modules              │ │
│  │  AppConfig · HistoryManager · Dictionary     │ │
│  │  SnippetEngine · ModelManager · EventBus     │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Functional Requirements

### WD-1: Dashboard Home / Status

- **WD-1.1**: Show application state (idle/recording/processing/error)
- **WD-1.2**: Display current configuration summary (active STT backend, model, language, AI status)
- **WD-1.3**: Show quick stats: total transcriptions today, total words, average duration
- **WD-1.4**: WebSocket connection for real-time state updates

### WD-2: Configuration Management

- **WD-2.1**: View and edit all config sections: Audio, STT, AI, Hotkey, Injection, History, Adaptive
- **WD-2.2**: Form-based editing with validation and appropriate input types (toggles, dropdowns, sliders)
- **WD-2.3**: Save configuration persists to `config.toml` via existing `AppConfig.save()`
- **WD-2.4**: Reset to defaults button per section
- **WD-2.5**: Config changes take effect description (some require restart, some are live)

### WD-3: Transcription History

- **WD-3.1**: Paginated table of all transcriptions (newest first)
- **WD-3.2**: Columns: timestamp, raw text, refined text, duration, app context, word count, language
- **WD-3.3**: Full-text search across raw and refined text
- **WD-3.4**: Copy any transcription to clipboard (via browser API)
- **WD-3.5**: Delete individual entries
- **WD-3.6**: Bulk clear all history with confirmation
- **WD-3.7**: Export history as JSON

### WD-4: Dictionary Management

- **WD-4.1**: Table view of all dictionary entries (word, source, frequency, category, added_at)
- **WD-4.2**: Add new words with category selection
- **WD-4.3**: Remove words
- **WD-4.4**: View learned corrections (heard → corrected, count, last_seen)
- **WD-4.5**: Delete individual corrections

### WD-5: Snippets Management

- **WD-5.1**: Table view of all snippets (trigger → expansion)
- **WD-5.2**: Add new snippets
- **WD-5.3**: Remove snippets
- **WD-5.4**: Inline editing of trigger/expansion

### WD-6: Model Management

- **WD-6.1**: List all supported Whisper models with download status and size
- **WD-6.2**: Download models (with progress indicator)
- **WD-6.3**: Delete downloaded models
- **WD-6.4**: Show total disk usage of models
- **WD-6.5**: Indicate currently active model

## Non-Functional Requirements

### NF-1: Technology Stack
- **Backend**: FastAPI + uvicorn (async, lightweight)
- **Frontend**: Single HTML page with Tailwind CSS (CDN) + Alpine.js (CDN) for reactivity
- **No build step**: Zero frontend tooling required
- **Port**: 7865 (configurable)

### NF-2: Performance
- Dashboard loads in < 1 second
- API responses < 200ms for all CRUD operations
- WebSocket latency < 100ms for state updates

### NF-3: Security
- Binds to localhost only by default (127.0.0.1)
- No authentication required for local-only access
- Optional: configurable bind address for remote access

### NF-4: Integration
- Reuses all existing modules (AppConfig, HistoryManager, Dictionary, SnippetEngine, ModelManager)
- Does not duplicate any business logic
- Can run alongside the main daemon or standalone

## API Endpoints

### Status
- `GET /api/status` — App state, version, uptime
- `WS /api/ws/status` — Real-time state updates

### Config
- `GET /api/config` — Full config as JSON
- `PUT /api/config` — Update config (partial merge)
- `POST /api/config/reset` — Reset to defaults

### History
- `GET /api/history?page=1&limit=20&q=search` — Paginated history
- `GET /api/history/stats` — Aggregate statistics
- `DELETE /api/history/{id}` — Delete single entry
- `DELETE /api/history` — Clear all
- `GET /api/history/export` — Export as JSON

### Dictionary
- `GET /api/dictionary` — All entries + corrections
- `POST /api/dictionary/words` — Add word
- `DELETE /api/dictionary/words/{word}` — Remove word
- `DELETE /api/dictionary/corrections/{index}` — Remove correction

### Snippets
- `GET /api/snippets` — All snippets
- `POST /api/snippets` — Add snippet
- `DELETE /api/snippets/{trigger}` — Remove snippet

### Models
- `GET /api/models` — List models with status
- `POST /api/models/{name}/download` — Download model
- `DELETE /api/models/{name}` — Delete model
- `GET /api/models/disk-usage` — Total disk usage

## File Structure

```
src/linux_whispr/web/
├── __init__.py
├── server.py           # FastAPI app, static file serving, entry point
├── api/
│   ├── __init__.py
│   ├── config_routes.py
│   ├── history_routes.py
│   ├── dictionary_routes.py
│   ├── snippets_routes.py
│   ├── models_routes.py
│   └── status_routes.py
└── static/
    └── index.html      # SPA (Tailwind + Alpine.js)
```

## UI Design

### Layout
- **Sidebar navigation**: Dashboard, Config, History, Dictionary, Snippets, Models
- **Dark theme** by default (matches developer preference), with light mode toggle
- **Responsive**: Works on desktop and tablet viewports
- **Color palette**: Neutral grays with accent purple/blue (matching LinuxWhispr branding)

### Pages
1. **Dashboard**: Status card, quick stats cards, recent transcriptions preview
2. **Configuration**: Accordion/tab sections for each config group, form controls
3. **History**: Searchable data table with pagination, copy/delete actions
4. **Dictionary**: Two tables (words + corrections), add forms
5. **Snippets**: Editable table with add/remove
6. **Models**: Card grid showing each model with download/delete actions

## Out of Scope (v1)
- User authentication / multi-user
- Remote access without VPN/SSH tunnel
- Real-time audio visualization in browser
- Triggering dictation from the browser
- WebRTC-based browser microphone recording

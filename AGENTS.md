# Repository Guidelines

## Project Structure & Module Organization

- `main.py`: GTK app, audio capture, Deepgram transcription, clipboard/paste logic.
- `enhance.py`: Optional Prompt Mode using OpenAI (concise/balanced/detailed styles).
- `images/`: App icons and screenshots.
- `requirements.txt`: Python dependencies. System deps: GTK 3 + gobject-introspection.
- `voice-transcribe`: Launcher that ensures `venv` and runs the app.
- `install-desktop-app.sh`: Installs `.desktop` entry and Ctrl+Q shortcut (GNOME).
- `config.json`: Saved UI preferences (Prompt Mode + style). Do not hand-edit.

## Build, Test, and Development Commands

- Create venv + install: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- Run locally: `python main.py`
- Launcher (auto-venv): `./voice-transcribe` or `./voice-transcribe toggle`
- Desktop install: `bash install-desktop-app.sh`
- System packages (Debian/Ubuntu): `sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 libgirepository-2.0-dev xclip xdotool wl-clipboard`
- Env keys (required): add `.env` with `DEEPGRAM_API_KEY=...` (and optional `OPENAI_API_KEY=...`).

## Coding Style & Naming Conventions

- Python 3, PEP 8, 4‑space indent. Use type hints where clear.
- Names: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants.
- UI updates must occur on GTK thread; use `GLib.idle_add(...)` from workers.
- Keep audio/transcription in background threads; avoid blocking the main loop.
- Match existing color palette and CSS classes in `apply_css()`.

## Testing Guidelines

- No formal test suite. Use manual smoke tests:
  - Launch, record ~3s, confirm transcript and word count.
  - Toggle Prompt Mode (checkbox or Ctrl+Shift+Q), verify enhanced text renders or error fallback.
  - Clipboard copies (Original/Enhanced) and X11 auto‑paste.
- Network/API failures must leave original transcript available.

## Commit & Pull Request Guidelines

- Branch: target `dev` for PRs. Keep changes scoped and reversible.
- Messages: concise, imperative (“increase timeout”, “update README”); optional scope prefix (e.g., `ui:`, `transcribe:`, `enhance:`).
- PRs include: purpose, summary of changes, test steps, screenshots for UI, and any config/env impacts.

## Security & Configuration Tips

- Never commit secrets. `.env` is git‑ignored.
- Handle failures without exposing API keys in logs.
- Keep `config.json` for preferences only; do not store credentials.

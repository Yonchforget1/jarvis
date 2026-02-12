# JARVIS AI Agent Platform v2

## CORE RULES (NEVER BREAK THESE)
1. After EVERY code change, test that localhost:3000 chat responds to "hello" correctly. If it doesn't, fix it before doing ANYTHING else.
2. Core functionality > new features. Always.
3. Never spend more than 30 minutes on any feature without testing the full chat flow end-to-end.
4. If any test fails, stop all other work and fix it immediately.

## Architecture

```
jarvis/                Core Python package
  config.py            Config loading (config.yaml + .env)
  conversation.py      Agent loop with tool calling (max 25 turns)
  memory.py            Persistent learnings + ChromaDB vector search
  tool_registry.py     ToolDef registration, stats tracking
  tool_router.py       TF-IDF smart tool selection (top-K per message)
  plugin_loader.py     Auto-discover plugins/ directory
  backends/
    base.py            Backend ABC + ToolCall/BackendResponse dataclasses
    claude_code.py     Routes through Claude Code CLI (Max subscription, $0 cost)
    __init__.py         Backend factory
  tools/
    filesystem.py      8 tools: read, write, delete, move, list, info, search, mkdir
    shell.py           2 tools: run_shell, run_python (with safety checks)
    web.py             2 tools: search_web, fetch_url (with SSRF protection)
    computer.py        10 tools: screenshots, OCR, mouse, keyboard, window mgmt
    browser.py         8 tools: Playwright browser automation
    memory_tools.py    3 tools: save_learning, recall, search_memory
api/                   FastAPI server (port 3000)
  main.py              App with CORS, rate limiting, static serving
  auth.py              JWT auth with bcrypt
  models.py            Pydantic models
  deps.py              FastAPI dependencies
  session_manager.py   Per-user session lifecycle
  routers/             Endpoint modules (auth, chat, tools, stats)
  static/index.html    Dark-theme HTML chat UI (fallback)
web/                   Next.js frontend (TypeScript, Tailwind)
desktop/               Electron app (system tray, auto-update)
plugins/               Drop-in .py files with register(registry)
memory/                Learnings JSON + ChromaDB vector DB
tests/                 112+ tests across all modules
```

## Key Patterns
- Tools: `ToolDef(name, description, parameters, func)` registered via `registry.register()`
- Backend: `send(messages, system, tools, max_tokens)` returns `BackendResponse`
- ClaudeCodeBackend: shells out to `claude -p --output-format json` (Max subscription)
- Conversation.send() returns `str` (the final assistant text)
- Plugin: drop a .py file in plugins/ with `register(registry)` function

## Backend
- Uses Claude Code CLI (`claude -p`) which routes through Max subscription ($0 per use)
- Tool calling via prompt engineering (JSON format detection in response text)
- No API key needed – config.yaml has `backend: claude_code`

## Development Rules
- Always run `python -m pytest tests/` before committing
- Always test localhost:3000 chat after API changes
- New tools go in jarvis/tools/ or plugins/
- Keep optional deps behind try/except ImportError

## Business Context
Owner: Yonatan Weintraub. Target: $450K+ year one via SaaS ($97-497/mo), done-for-you ($5K-25K), white-label.

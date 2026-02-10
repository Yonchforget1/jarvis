# JARVIS AI Agent Platform

## 1. Identity

Jarvis is the most advanced AI agent platform on earth. It is not a chatbot, not an assistant, not a toy. It is a digital workforce that executes real tasks on real computers using real professional software.

Jarvis has the mentality of a champion - relentless, resourceful, and refuses to fail. It never says "I can't" - it says "let me figure out how." It treats every single task like millions of dollars depend on the result.

Before every task it reads its past learnings and asks itself "how do I destroy my previous best today."

## 2. Architecture Rules

- Every component must be modular and pluggable.
- New tools are added by dropping a Python file in `/plugins`.
- The AI brain is swappable between Claude, OpenAI, Gemini, and open-source models via `config.yaml`.
- All code must be production-quality - no prototypes, no placeholders, no shortcuts.
- Every file must be clean, documented, and tested.
- The self-improvement system logs every task outcome to `/memory/learnings.json` and reads it before every new task.

## 3. Quality Standards

Nothing leaves Jarvis that looks amateur.

- **Games** must use real engines like Unreal, Unity, or Godot with professional assets - never colored rectangles.
- **Software** must be deployable with proper error handling, logging, and documentation.
- **Content** must be polished and professional.

If a tool produces low-quality output, Jarvis must iterate until it meets professional standards.

## 4. Capabilities Roadmap

1. **Done** - 18 tools including filesystem, web scraping, code execution, shell commands, game dev, memory.
2. **Done** - Computer vision and GUI control (pywinauto/pyautogui/OCR) - 31 tools.
3. **Done** - Web UI at localhost:3000 (FastAPI + dark-theme chat UI).
4. **Done** - Desktop app via Electron (system tray, auto-start, auto-update, Windows/Mac/Linux installers).
5. **Done** - WhatsApp chatbot via whatsapp-web.js bridge.
6. **Done** - Smart tool router: picks 8 most relevant tools per message for local models.
7. **Next** - Background automation so Jarvis runs 24/7 without human supervision.
8. **Then** - Voice control.
9. **Then** - White-label system for reselling.

## 4a. Architecture Overview

```
desktop/          Electron app (the product users install)
  main.js         Main process - starts backend, creates window, system tray
  tray.js         System tray with auto-start, quick actions
  updater.js      Auto-update from GitHub Releases
api/              FastAPI server (port 3000)
  main.py         Routes, middleware, static file serving
  routers/        Endpoint modules (chat, auth, whatsapp, tools, etc.)
  static/         Web chat UI (fallback when Next.js not built)
web/              Next.js frontend (full dashboard, chat, settings)
jarvis/           Core Python package
  backends/       LLM backends (Claude, OpenAI, Gemini, Ollama)
  tools/          Tool modules (filesystem, shell, web, computer, browser, etc.)
  tool_router.py  Smart tool selection for local models
  conversation.py Agent loop with tool calling
```

## 5. Business Context

**Owner:** Yonatan Weintraub. This is a real business targeting $450K+ year one revenue.

Revenue streams:
- **SaaS subscriptions** at $97-497/month
- **Done-for-you custom builds** at $5K-25K each
- **White-label licensing**

Every feature built must serve the goal of making this product sellable and valuable. No feature exists just to be cool - it must make money or make the product better for paying customers.

## 6. Development Rules

- When working on this codebase always think about scalability, modularity, and production-readiness.
- Never use toy libraries when professional alternatives exist.
- Always prefer real software integration over AI-generated alternatives.
- Jarvis controls Blender, not DALL-E. Jarvis controls Unreal Engine, not Pygame. Jarvis uses professional tools because professionals are the customers.
- Always commit after completing features.
- Always test before committing.
- Always think about what makes this sellable.

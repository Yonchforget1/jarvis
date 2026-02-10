# Jarvis AI Agent Platform

**The most advanced AI agent platform for real business automation.**

Jarvis is not a chatbot. It is a production-grade AI agent that executes real tasks on real computers using real professional software. It reads files, writes code, browses the web, controls desktop applications, creates documents, builds games, and improves itself autonomously.

Built for business professionals who need a digital workforce, not a text generator.

---

## What Jarvis Can Do

### Core Capabilities

| Category | Tools | Description |
|----------|-------|-------------|
| **Filesystem** | `read_file`, `write_file`, `delete_file`, `list_files`, `directory_tree`, `file_search` | Full file system operations with search |
| **Shell** | `run_shell`, `run_python`, `execute_code` | Execute any command or script |
| **Web** | `search_web`, `fetch_url` | DuckDuckGo search and web scraping |
| **Computer Vision** | `analyze_screen`, `take_screenshot`, `read_screen_text`, `find_text_on_screen` | See the screen with AI vision and OCR |
| **Desktop Control** | `click_control`, `type_into_control`, `send_keys`, `handle_dialog`, `inspect_window` | Control any Windows application via pywinauto |
| **Window Management** | `list_windows`, `focus_window`, `launch_application`, `close_window`, `detect_popups` | Full window lifecycle management |
| **Browser Automation** | `open_browser`, `navigate_to`, `click_element`, `fill_form`, `extract_text` | Playwright-based web automation |
| **Game Development** | `create_godot_project` | Generate complete playable Godot 4 projects |
| **Planning** | `create_plan`, `decompose_task` | Task decomposition and multi-step planning |
| **Memory** | `save_learning`, `recall` | Persistent learning across sessions |

### Office Document Automation (Skills)

Jarvis includes a professional document automation suite for the four most common business formats:

| Skill | Capabilities |
|-------|-------------|
| **Word (.docx)** | Create, read, and edit Word documents. Tracked changes, comments, smart quotes, ISO OOXML schema validation. XML-level editing via pack/unpack workflow. |
| **PDF** | Extract text and tables, create PDFs, merge/split/rotate, OCR scanned documents, fill PDF forms, add watermarks, encrypt/decrypt. 8 helper scripts. |
| **PowerPoint (.pptx)** | Create presentations from scratch, edit existing decks via XML, professional design guidance (color palettes, typography, layout variety), QA verification loops. |
| **Excel (.xlsx)** | Create and edit spreadsheets with proper formula chains, industry-standard color coding (blue=inputs, black=formulas, green=links), recalculation verification. |

### Self-Improvement Engine

Jarvis has an autonomous evolution system (`evolve.py`) that:
1. Analyzes its own codebase
2. Researches the latest AI agent techniques
3. Generates improvement proposals
4. Tests changes on isolated git branches
5. Commits successful improvements
6. Logs learnings for future sessions

Every improvement is validated, tested, and safely rolled back on failure.

---

## Architecture

```
jarvis/
├── agent.py                 # CLI entry point
├── api/main.py              # FastAPI web server (REST + WebSocket + SSE)
├── evolve.py                # Autonomous self-improvement engine
├── config.yaml              # Backend and model configuration
├── jarvis/
│   ├── config.py            # Configuration management
│   ├── conversation.py      # Agent loop with tool calling
│   ├── memory.py            # Persistent learning system
│   ├── vision.py            # Claude Vision API integration
│   ├── tool_registry.py     # Tool registration and dispatch
│   ├── backends/
│   │   ├── __init__.py      # Backend factory
│   │   ├── claude.py        # Anthropic Claude backend
│   │   ├── openai_backend.py # OpenAI GPT backend
│   │   ├── gemini.py        # Google Gemini backend
│   │   └── ollama.py        # Local Ollama backend
│   └── tools/
│       ├── filesystem.py    # File operations
│       ├── shell.py         # Command execution
│       ├── web.py           # Web search and scraping
│       ├── computer.py      # Desktop automation (pywinauto + OCR)
│       ├── browser.py       # Playwright browser automation
│       ├── gamedev.py       # Game development tools
│       ├── game_engine.py   # Godot 4 project generation
│       └── planner_tools.py # Task planning
├── plugins/                 # Drop-in plugin system
│   ├── system_info.py       # System information
│   ├── process_manager.py   # Process management
│   ├── github_integration.py # GitHub API
│   ├── database.py          # Database queries
│   ├── docker_manager.py    # Docker management
│   ├── http_request.py      # HTTP client
│   └── ...                  # 12+ plugins
├── skills/                  # Document automation skills
│   ├── docx/                # Word document processing
│   ├── pdf/                 # PDF processing
│   ├── pptx/                # PowerPoint creation
│   └── xlsx/                # Excel spreadsheet automation
├── memory/                  # Persistent storage
│   ├── learnings.json       # Accumulated knowledge
│   └── evolution_log.json   # Self-improvement history
└── web/                     # Next.js web UI
    └── src/
        ├── app/             # Pages (chat, dashboard, tools, learnings)
        └── components/      # React components
```

### Design Principles

- **Modular**: Every tool, backend, and plugin is independent and swappable
- **Pluggable**: Add new tools by dropping a `.py` file in `/plugins`
- **Backend-agnostic**: Switch between Claude, OpenAI, Gemini, or local Ollama models with one config change
- **Production-ready**: Error handling, logging, rate limiting, JWT authentication, CORS
- **Self-improving**: The evolution engine learns from every task outcome

---

## Installation

### Prerequisites

- **Python 3.12+** (tested on 3.14)
- **Node.js 18+** (for web UI)
- **Tesseract OCR** (for screen reading)
- **Godot 4.3** (optional, for game development)

### 1. Clone and set up Python environment

```bash
git clone https://github.com/your-org/jarvis.git
cd jarvis
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Install system dependencies

**Tesseract OCR** (required for screen reading):
```bash
# Windows
winget install UB-Mannheim.TesseractOCR

# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt install tesseract-ocr
```

**Playwright browsers** (required for web automation):
```bash
python -m playwright install
```

### 4. Configure API keys

Create a `.env` file in the project root:

```env
# Pick one (or more) based on your backend
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...

# For the web API (generate a random secret)
JWT_SECRET=your-random-secret-here
```

### 5. Configure your backend

Edit `config.yaml`:

```yaml
# Claude (recommended)
backend: claude
model: claude-sonnet-4-5-20250929

# OpenAI
# backend: openai
# model: gpt-4o

# Gemini
# backend: gemini
# model: gemini-2.0-flash

# Local (free, no API key needed)
# backend: ollama
# model: llama3.1:8b
# ollama_base_url: http://localhost:11434
```

### 6. (Optional) Set up the web UI

```bash
cd web
npm install
npm run dev
```

---

## Usage

### CLI (Interactive Chat)

```bash
python agent.py
```

This starts an interactive session where you can give Jarvis any task:

```
You: Read all the CSV files in /data and create a summary spreadsheet
Jarvis: [reads files, analyzes data, creates Excel with formulas]

You: Open Chrome, go to linkedin.com, and extract the top 10 job postings for "AI engineer"
Jarvis: [launches browser, navigates, scrapes data, returns structured results]

You: Take a screenshot and tell me what's on screen
Jarvis: [captures screen, runs OCR + AI vision, describes everything visible]
```

### CLI Commands

```bash
python agent.py                  # Interactive chat (default)
python agent.py tools            # List all available tools
python agent.py check-config     # Validate configuration
python agent.py benchmark        # Run performance benchmarks
python agent.py new-plugin name  # Scaffold a new plugin
python agent.py test-tool name   # Test a specific tool
python agent.py docs             # Generate tool documentation
```

### Web API

```bash
# Start the API server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Or with auto-reload for development
uvicorn api.main:app --reload
```

**Key endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with system stats |
| `/api/auth/login` | POST | JWT authentication |
| `/api/chat/stream` | POST | Chat with SSE streaming |
| `/api/ws/chat` | WS | WebSocket chat |
| `/api/tools` | GET | List all tools |
| `/api/learnings` | GET | View accumulated learnings |
| `/api/stats` | GET | Usage statistics |

### Self-Improvement

```bash
python evolve.py                # Run evolution engine (continuous)
python evolve.py --once         # Single improvement cycle
python evolve.py --dry-run      # Plan without writing files
python evolve.py --interval 120 # Custom cycle interval (seconds)
python evolve.py --no-dashboard # Plain text output
```

---

## Adding New Tools

### As a Plugin (Easiest)

Create a `.py` file in `/plugins`:

```python
# plugins/my_tool.py
from jarvis.tool_registry import ToolDef

def register(registry):
    def my_function(input_text: str) -> str:
        """Process some input and return a result."""
        return f"Processed: {input_text}"

    registry.register(ToolDef(
        name="my_tool",
        description="Description of what this tool does.",
        parameters={
            "properties": {
                "input_text": {
                    "type": "string",
                    "description": "The input to process"
                },
            },
            "required": ["input_text"],
        },
        func=my_function,
    ))
```

Drop it in `/plugins` and restart Jarvis. It will be automatically discovered and registered.

### As a Core Tool

Add a new file in `jarvis/tools/`, implement `register(registry)`, and import it in `jarvis/tools/__init__.py`.

---

## Switching AI Backends

Jarvis supports four AI backends. Switch by editing `config.yaml`:

### Claude (Anthropic) - Recommended
```yaml
backend: claude
model: claude-sonnet-4-5-20250929
```
Best tool-calling accuracy. Supports vision. Requires `ANTHROPIC_API_KEY`.

### OpenAI
```yaml
backend: openai
model: gpt-4o
```
Requires `OPENAI_API_KEY`.

### Gemini (Google)
```yaml
backend: gemini
model: gemini-2.0-flash
```
Requires `GOOGLE_API_KEY`.

### Ollama (Local, Free)
```yaml
backend: ollama
model: llama3.1:8b
ollama_base_url: http://localhost:11434
```
No API key needed. Install Ollama and pull a model:
```bash
ollama pull llama3.1:8b
```

---

## Desktop Automation

Jarvis uses **pywinauto** (UIA backend) as its primary Windows automation engine, with pyautogui as a fallback for pixel-level control. It can:

- **List and manage windows**: Find, focus, minimize, maximize, close any window
- **Inspect UI controls**: See every button, text field, menu item with automation IDs
- **Click controls by name**: Click "Save" button, not coordinates — resolution-independent
- **Handle dialogs automatically**: Save dialogs, confirmation prompts, error messages
- **Type text reliably**: Uses pyautogui.write() for literal text (no dropped characters)
- **Read the screen**: OCR via Tesseract (fast, no API calls) or AI vision via Claude
- **Find text coordinates**: Locate any text on screen and get click-ready coordinates

### Example: Automate Notepad

```
You: Open Notepad, type "Hello World", save it as test.txt on the desktop

Jarvis uses: launch_application → type_text → send_keys(^+s) → save_file_dialog
```

---

## Document Skills

The `/skills` directory contains professional document automation capabilities. These were selected from a rigorous evaluation of 16 candidate skills, scoring only 9+/10 for business value.

### Selected Skills (4/16)

| Skill | Score | Why Selected |
|-------|-------|-------------|
| **docx** | 9/10 | Word documents are the #1 business format. XML-level editing with tracked changes. |
| **pdf** | 9/10 | PDF manipulation is the most requested automation task globally. |
| **pptx** | 9/10 | "Make me a presentation" is one of the highest-value AI agent tasks. |
| **xlsx** | 9/10 | Spreadsheet work is the most common office automation task. |

These four skills share a common `office/` module (pack/unpack/validate) and together enable workflows like:

> "Take this PDF contract, extract the key terms into a spreadsheet, create a summary presentation for the board, and draft a Word memo for legal review."

See [skills/skill_evaluation.md](../skills/skill_evaluation.md) for the full evaluation of all 16 skills.

---

## Memory System

Jarvis learns from every interaction:

- **Learnings** are saved to `memory/learnings.json` with category, insight, context, and timestamp
- Before each task, Jarvis reads past learnings to avoid repeating mistakes
- The evolution engine records improvement history in `memory/evolution_log.json`
- Topic-based retrieval lets Jarvis recall relevant knowledge by keyword

---

## Web UI

Jarvis includes a Next.js web interface at `/web`:

- **Chat**: Real-time conversation with streaming responses and tool call visualization
- **Dashboard**: System health, memory usage, uptime monitoring
- **Tools**: Browse all available tools with descriptions and parameters
- **Learnings**: View and export accumulated knowledge
- **Settings**: Configure preferences and API keys

Start the web UI:
```bash
cd web
npm install
npm run dev
# Open http://localhost:3000
```

---

## Configuration Reference

### config.yaml

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `backend` | string | `claude` | AI backend: `claude`, `openai`, `gemini`, `ollama` |
| `model` | string | `claude-sonnet-4-5-20250929` | Model identifier |
| `api_key_env` | string | `ANTHROPIC_API_KEY` | Environment variable for API key |
| `max_tokens` | int | `4096` | Maximum completion tokens (1-200000) |
| `system_prompt` | string | (built-in) | System instruction for the AI |
| `tool_timeout` | int | `30` | Tool execution timeout in seconds |
| `max_tool_turns` | int | `25` | Max tool calls per conversation turn |
| `ollama_base_url` | string | `http://localhost:11434` | Ollama server URL |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | For Claude | Anthropic API key |
| `OPENAI_API_KEY` | For OpenAI | OpenAI API key |
| `GOOGLE_API_KEY` | For Gemini | Google AI API key |
| `JWT_SECRET` | For web API | JWT signing secret (randomize in production) |
| `CORS_ORIGINS` | Optional | Comma-separated allowed origins |

---

## Project Status

### Current Capabilities
- 30+ built-in tools across 8 categories
- 12+ plugins for system integration
- 4 professional document automation skills
- Full desktop automation with pywinauto
- OCR screen reading with Tesseract
- Browser automation with Playwright
- 4 swappable AI backends
- Self-improving evolution engine
- Production REST API with authentication
- Real-time web UI

### Roadmap
1. Background automation (24/7 unattended operation)
2. Voice control interface
3. White-label system for reselling
4. Multi-agent orchestration

---

## License

Proprietary. All rights reserved.

---

Built by [Yonatan Weintraub](https://github.com/yonch). Powered by Claude, OpenAI, Gemini, and Ollama.

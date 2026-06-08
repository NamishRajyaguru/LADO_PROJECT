# LADO — Local Autonomous Digital Operator

> A fully local, modular AI agent for personal file system management on Windows 11.

LADO watches your file system, detects duplicates, generates cleanup suggestions, and explains every decision in plain English — all running on your machine, no cloud required.

---

## What it does

- Scans selected directories and indexes all file metadata into a local SQLite database
- Detects duplicate files using size-first SHA256 hashing
- Runs a rule-based policy engine to generate file management suggestions
- Explains decisions in plain English via Groq LLM
- Executes approved suggestions (move, archive, quarantine) via a controlled action engine
- Monitors your folders in real time using a file watchdog — no manual rescans needed
- Maintains a full audit trail via structured logging
- Provides a desktop UI with Dashboard, File Browser, Suggestions, Duplicates, Chat, and Logs panels

---

## Project structure

```
LADO_PROJECT/
├── main.py                  ← entry point
├── config.py                ← your local settings (not committed)
├── config.example.py        ← template for config.py
├── requirements.txt
├── core/
│   ├── scanner.py           ← file system indexer
│   ├── database.py          ← SQLite memory layer
│   ├── hashing.py           ← duplicate detection
│   ├── logger.py            ← audit trail
│   ├── policy_engine.py     ← rule-based decision engine
│   ├── action_engine.py     ← executes approved suggestions
│   └── llm.py               ← Groq LLM interface
├── ui/
│   ├── app.py               ← main window and navigation
│   ├── dashboard.py         ← overview stats + run scan
│   ├── file_browser.py      ← browsable file table with filters
│   ├── suggestions.py       ← approve / reject suggestions
│   ├── duplicates.py        ← duplicate cluster viewer
│   ├── chat.py              ← LLM chat + command detection
│   ├── logs.py              ← daily log viewer
│   ├── watcher.py           ← real-time file watchdog
│   └── _state.py            ← shared app state across panels
└── data/                    ← auto-created on first run
    ├── lado.db
    └── logs/
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/NamishRajyaguru/LADO_PROJECT.git
cd LADO_PROJECT
```

**2. Configure**
```bash
copy config.example.py config.py
```
Open `config.py` and fill in:
- `SCAN_TARGETS` — folders to watch (e.g. `C:/Users/YourName/Downloads`)
- `GROQ_API_KEY` — get yours free at [console.groq.com](https://console.groq.com)

**3. Install dependencies**
```bash
pip install -r requirements.txt
pip install customtkinter watchdog
```

**4. Run**
```bash
python ui\app.py
```

The UI launches, starts watching your folders, and is ready to scan.

---

## Usage

| Action | How |
|---|---|
| Run a full scan | Dashboard → **Run Scan** button |
| Auto-scan on file change | Automatic — watchdog runs in background |
| Review suggestions | Suggestions panel → Approve or Reject |
| See duplicate clusters | Duplicates panel → expand any cluster |
| Browse indexed files | Files panel → search, filter by type or size |
| Chat with LADO | Chat panel — ask anything or give commands |
| View activity logs | Logs panel → browse by date |

### Chat commands

Type these in the Chat panel to trigger real actions:

| Command | What happens |
|---|---|
| `run a scan` | Runs a full file scan immediately |
| `approve all duplicates` | Executes all approved duplicate suggestions |
| `approve all suggestions` | Executes all approved suggestions |

---

## Architecture

LADO is a model-based AI agent built on symbolic AI principles. Intelligence comes from structured rules, persistent memory, and reinforcement from user feedback — not from the LLM. The LLM is used only for plain English explanations and conversational responses.

```
Files on disk
     ↓
Scanner → SQLite DB
     ↓
Hashing → Duplicate clusters
     ↓
Policy Engine → Suggestions (pending / approved / rejected)
     ↓
Action Engine → Physical file operations (move, archive, quarantine)
     ↓
LLM → Plain English explanations
     ↓
UI → Dashboard, Files, Suggestions, Duplicates, Chat, Logs
```

---

## Phase roadmap

- [x] Phase 1 — File indexing and metadata database
- [x] Phase 2 — Duplicate detection
- [x] Phase 3 — Rule-based policy engine
- [ ] Phase 4 — Controlled action engine
- [ ] Phase 5 — Adaptive reinforcement
- [ ] Phase 6 — Desktop UI + voice interface

---

## Contributing

Backend lives in `core/` — owned by [@NamishRajyaguru](https://github.com/NamishRajyaguru).
Frontend lives in `ui/` — owned by [@NishadRaval](https://github.com/NishadRaval).

Branch workflow: feature branches → PR → review → merge to `main`.

---

## License

Private project. All rights reserved.
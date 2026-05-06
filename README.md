# LADO — Local Autonomous Digital Operator

A fully local, modular AI agent for personal file system management on Windows 11.

## What it does
- Scans selected user directories and indexes all file metadata
- Detects duplicate files using size-first SHA256 hashing
- Runs a rule-based policy engine to generate file management suggestions
- Explains decisions in plain English via Groq LLM
- Maintains a full audit trail via structured logging

## Project structure
LADO_PROJECT/
├── main.py              ← entry point
├── config.py            ← your local settings (not committed)
├── config.example.py    ← template for config.py
├── requirements.txt
├── core/
│   ├── scanner.py       ← file system indexer
│   ├── database.py      ← SQLite memory layer
│   ├── hashing.py       ← duplicate detection
│   ├── logger.py        ← audit trail
│   ├── policy_engine.py ← rule-based decision engine
│   └── llm.py           ← Groq LLM interface
└── data/                ← auto-created on first run
    ├── lado.db
    └── logs/

## Setup
1. Clone the repo
2. Copy config.example.py to config.py and fill in your values
3. pip install -r requirements.txt
4. python main.py

## Architecture
LADO is a model-based AI agent built on symbolic AI principles.
Intelligence comes from structured rules, persistent memory, and 
reinforcement from user feedback — not from the LLM.
The LLM is used only for plain English explanations.

## Phase roadmap
- [x] Phase 1 — File indexing and metadata database
- [x] Phase 2 — Duplicate detection
- [x] Phase 3 — Rule-based policy engine
- [ ] Phase 4 — Controlled action engine
- [ ] Phase 5 — Adaptive reinforcement
- [ ] Phase 6 — Desktop UI + voice interface
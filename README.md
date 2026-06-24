# LADO — Local Autonomous Digital Operator

LADO is a local-first agentic AI system that continuously monitors, analyzes, and improves file organization through intelligent recommendations and autonomous file management workflows.

Unlike traditional file managers, LADO combines real-time monitoring, machine learning feedback loops, and natural language interaction to help users keep their systems organized without manually sorting files.

## Features

### Intelligent File Indexing

* Scans and indexes local files
* Stores metadata in SQLite
* Fast file search and filtering

### AI-Powered Recommendations

* Detects redundant and low-value files
* Generates cleanup suggestions
* Confidence and risk scoring for every recommendation

### Duplicate Detection

* Hash-based duplicate identification
* Duplicate cluster visualization
* Storage recovery insights

### Reinforcement Learning Loop

* Learns from approved and rejected suggestions
* Adapts future recommendations based on user feedback

### Real-Time Monitoring

* Watches file system activity
* Automatically refreshes insights when files change

### Natural Language Agent

* Chat with LADO using plain English
* Ask questions about your file system
* Trigger supported actions through conversation

### Safety First

* Suggestions require user approval
* Quarantine system for potentially removable files
* Local-first architecture

## Tech Stack

* Python
* CustomTkinter
* SQLite
* Watchdog
* Groq LLM Integration
* Hash-based File Analysis
* Agentic Decision Engine

## Project Structure

core/

* Scanner
* Policy Engine
* Reinforcement Engine
* Action Engine
* Database Layer
* LLM Layer

ui/

* Dashboard
* Agent Chat
* File Browser
* Suggestions
* Duplicates
* Logs

## Future Roadmap

* Theme Switching
* Executable Installer
* Advanced Autonomous Actions
* Multi-Agent Collaboration
* Improved Memory and Learning

## Authors

### Namu

* Project Architecture
* Backend Development
* Agent Design
* Database Integration
* Reinforcement System
* Core Logic

### [Friend's Name]

* UI Development
* Design Improvements
* Interface Components
* User Experience

## Disclaimer

LADO is designed to assist users in managing files and storage. Users should review recommendations before approving actions involving file modification, movement, or deletion.

# HyxTerminal v0.6

A smart terminal emulator with advanced features.

## Features
- All v0.5 features
- Command pipelines with |> operator
- Plugin hot-reloading
- AI-powered command suggestions
- Command grouping and categories
- Enhanced help system

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python src/main.py
```

## Commands
All v0.5 commands plus:
- Grouped command listing
- Detailed command help
- Pipeline support

## Command Pipelines
Chain commands with output passing:
```bash
ls |> grep .py |> wc -l
```

## Plugin Hot-Reloading
Plugins are automatically reloaded when their source files change.

## Command Groups
Commands are now organized into groups:
- general
- file
- system
- network
- etc.

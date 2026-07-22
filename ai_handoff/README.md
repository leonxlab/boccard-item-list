# AI Handoff Context: Item List Revision Project

## Project Overview
This is a Flask-based web application designed to manage and display P&ID (Piping and Instrumentation Diagram) item lists. Users upload Excel files containing item details, and the system parses them into an SQLite database for filtering, editing, and managing.

## Stack
- Backend: Flask, Python, SQLite (using `sqlite3` in `app/services/db_service.py`)
- Frontend: HTML/Jinja2 templates, Vanilla CSS, Vanilla JavaScript (fetch API)
- Styling: Custom modern UI, glassmorphism, responsive design

## Handoff Purpose
The user wants to implement "Phase 2" of the project, which introduces an "Advanced Data Assistant". To save usage limits on the current agent, the implementation plan has been broken down into 4 Milestones, separated into individual Markdown files in this directory.

Please read the individual Milestone markdown files for detailed requirements and architecture instructions.

## Directory Structure
- `app/` - Application code
  - `routes.py` - Flask routes
  - `services/` - Business logic (`db_service.py`, `excel_service.py`)
  - `templates/` - HTML files (`base.html`, `index.html`, `admin.html`)
- `data/` - SQLite database
- `uploads/` - Stored Excel files

Please proceed with implementing the milestones as requested by the user.

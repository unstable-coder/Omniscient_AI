# Omniscient AI

Omniscient AI is a FastAPI-based industrial knowledge assistant for ingesting documents, indexing them, and answering questions with retrieval-augmented generation (RAG). The project also includes demo enterprise features for maintenance ticketing and compliance checking for hackathon-style demonstrations.

## What this project includes

- Multi-file document upload and ingestion
- Document parsing for PDFs, DOCX, XLSX, CSV, text, images, and more
- Vector search with Qdrant
- Graph-aware retrieval support for Neo4j
- Chat UI for asking questions over indexed documents
- Demo maintenance ticket creation workflow
- Demo compliance checklist evaluation for SOP/manual-style content

## Requirements

- Python 3.11+
- pip
- A working environment for the following optional integrations:
  - Qdrant
  - Neo4j
  - Google Gemini API key

## Quick start (Windows PowerShell)

1. Clone the repository and enter the project folder

```powershell
cd C:\path\to\omniscient
```

2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies

```powershell
pip install -r requirements.txt
```

4. Create a `.env` file in the project root

Example:

```env
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=
EMBEDDING_MODEL=
EMBEDDING_BATCH_SIZE=
CHUNK_SIZE=
CHUNK_OVERLAP=
UPLOAD_DIR=storage/uploads
TEMP_DIR=storage/temp
STATUS_FILE=storage/status/documents.json
MAX_UPLOAD_SIZE_MB=
APP_HOST=127.0.0.1
APP_PORT=8000
GOOGLE_API_KEY=
GEMINI_MODEL=
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=
NEO4J_DATABASE=
AURA_INSTANCEID=
AURA_INSTANCENAME=
```

5. Run the app

```powershell
python -m uvicorn app.main:app --reload
```

6. Open the app in your browser

- Admin/upload page: http://127.0.0.1:8000/
- Chat page: http://127.0.0.1:8000/chat
- Demo tickets admin page: http://127.0.0.1:8000/admin/tickets

## Demo enterprise features

- After an AI response, the app may show Suggested Enterprise Actions.
- If the answer looks maintenance-related, a Create Ticket action appears.
- If the retrieved context looks like an SOP/manual/policy, a Check Compliance action appears.
- Tickets are stored locally in `storage/demo_tickets.json`.
- Compliance rules are stored in `storage/compliance_rules.json`.

## Project structure

- `app/main.py` — FastAPI app entry point
- `app/api/` — API routes for chat, admin, history, and tickets
- `app/services/` — business logic for chat, ingestion, tickets, and compliance
- `app/utils/templates/` — HTML templates for the UI
- `app/static/` — CSS and JavaScript assets
- `tests/` — unit tests for the core services

## Running tests

```powershell
pytest -q
```

## Notes

- The app can run locally without a full production backend, but document ingestion and chat answers depend on your configured Qdrant, Gemini, and Neo4j services.
- The ticketing and compliance features are intentionally demo-focused and modular so they can later be replaced with real enterprise integrations.

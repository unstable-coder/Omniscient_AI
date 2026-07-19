<<<<<<< HEAD
# Industrial Knowledge Intelligence Admin Document Ingestion

A complete Python 3.11+ FastAPI admin dashboard for uploading and indexing industrial documents with Qdrant vector storage.

## Features

- Drag-and-drop and multi-file upload
- Local original storage and safe status tracking
- Modular parsers for PDF, DOCX, PPTX, XLSX, CSV, JSON, XML, HTML, YAML, images, EML, ZIP
- Structure-aware chunking with overlap and metadata preservation
- Batched open-source embeddings via `sentence-transformers`
- Qdrant Cloud vector upsert and document deletion
- Status polling, retry, and delete actions in the dashboard

## Setup

1. Create a virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Copy the example environment file

```powershell
copy .env.example .env
```

4. Configure `.env` with your Qdrant Cloud values

5. Run the application

```powershell
uvicorn app.main:app --reload
```

6. Open the admin dashboard

`http://127.0.0.1:8000/`

## Tests

```powershell
pip install pytest
pytest
```

## Storage Layout

- `storage/uploads/` — saved originals
- `storage/temp/` — temporary extraction files
- `storage/status/documents.json` — atomic status record

## Notes

- No database is required
- Qdrant collection is created only if missing
- Original file deletion also removes Qdrant points by `document_id`
- Missing OCR support does not prevent startup, but image OCR is only used if `pytesseract` and `Pillow` are available
=======

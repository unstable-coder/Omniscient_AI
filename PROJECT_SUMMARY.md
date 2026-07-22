# Omniscient Project Summary

## 1. Project Overview
Omniscient is an AI-powered knowledge management system for industrial and technical documents. It allows users to upload documents, extract meaningful content, index it for semantic search, and query it through a chat interface for fast, context-based answers.

## 2. Workflow and Working
1. User uploads files through the admin dashboard.
2. The backend saves the file locally and records its status.
3. A suitable parser extracts text and structure from the file.
4. The content is split into chunks and enriched with metadata.
5. Embeddings are generated for semantic search and entities are extracted for graph-based reasoning.
6. The data is stored in Qdrant (vector search) and Neo4j (knowledge graph).
7. Users ask questions in the chat UI, and the system retrieves relevant context from both vector and graph stores to generate an answer.

## 3. Technologies Used
- Python with FastAPI
- Jinja2 templates, HTML, CSS, and JavaScript for the web UI
- Qdrant for vector storage and similarity search
- Neo4j for graph-based relationship retrieval
- sentence-transformers for embeddings
- Google Gemini for conversational answer generation
- Parsers for PDF, DOCX, PPTX, XLSX, CSV, JSON, XML, HTML, YAML, images, email, and ZIP files

## 4. System Design
The system follows a modular architecture:
- Frontend: admin dashboard and chat interface
- API layer: FastAPI routes for upload, ingestion, chat, and history
- Services layer: ingestion, chunking, embedding, entity extraction, status tracking, storage, and retrieval
- Data layer: local file storage, Qdrant vector database, and Neo4j graph database

## 5. Real-World Problem Solved
It solves the problem of information overload in industrial environments. Engineers, operators, and managers often struggle to find the right procedure, maintenance record, compliance document, or troubleshooting guidance from scattered files. This system turns those documents into a searchable, AI-assisted knowledge base.

## 6. Value Proposition
- Faster access to technical knowledge
- Better search than keyword-only systems
- Context-aware answers using AI
- Structured knowledge representation for deeper reasoning

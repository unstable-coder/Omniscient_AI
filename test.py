from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if not ENV_FILE.exists():
    print(f"ERROR: .env not found at: {ENV_FILE}")
    sys.exit(1)

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# Read configuration
# ---------------------------------------------------------

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "omniscient")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")


if not QDRANT_URL:
    print("ERROR: QDRANT_URL is missing")
    sys.exit(1)

if not QDRANT_API_KEY:
    print("ERROR: QDRANT_API_KEY is missing")
    sys.exit(1)


# ---------------------------------------------------------
# Connect to Qdrant
# ---------------------------------------------------------

print(f"Collection: {QDRANT_COLLECTION}")
print(f"Embedding model: {EMBEDDING_MODEL}")
print("Connecting to Qdrant...")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=30,
    prefer_grpc=False,
)


# ---------------------------------------------------------
# Verify collection
# ---------------------------------------------------------

try:
    collection_info = client.get_collection(
        collection_name=QDRANT_COLLECTION
    )

    print("Qdrant connection: OK")
    print(f"Points count: {collection_info.points_count}")

except Exception as exc:
    print(f"ERROR connecting to collection: {exc}")
    sys.exit(1)


# ---------------------------------------------------------
# Load same embedding model used during ingestion
# ---------------------------------------------------------

print("\nLoading embedding model...")

model = SentenceTransformer(EMBEDDING_MODEL)

print("Embedding model loaded.")


# ---------------------------------------------------------
# Ask for query
# ---------------------------------------------------------

query = input("\nEnter search query: ").strip()

if not query:
    print("ERROR: Query cannot be empty")
    sys.exit(1)


try:
    top_k_input = input("Enter top_k [default 5]: ").strip()
    top_k = int(top_k_input) if top_k_input else 5
except ValueError:
    top_k = 5


# ---------------------------------------------------------
# Generate query embedding
# ---------------------------------------------------------

print("\nGenerating query embedding...")

query_vector = model.encode(
    query,
    normalize_embeddings=True,
).tolist()


# ---------------------------------------------------------
# Search Qdrant
# ---------------------------------------------------------

print("Searching Qdrant...\n")

try:
    result = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )

    hits = result.points

except Exception as exc:
    print(f"SEARCH ERROR: {exc}")
    sys.exit(1)


# ---------------------------------------------------------
# Display results
# ---------------------------------------------------------

if not hits:
    print("No results found.")
    sys.exit(0)


print("=" * 80)
print(f"TOP {len(hits)} RESULTS")
print("=" * 80)


for rank, hit in enumerate(hits, start=1):
    payload = hit.payload or {}

    text = payload.get("text", "")
    filename = payload.get("original_filename", "unknown")
    document_id = payload.get("document_id", "unknown")
    chunk_index = payload.get("chunk_index", "unknown")

    print(f"\nRANK: {rank}")
    print(f"SCORE: {hit.score:.6f}")
    print(f"POINT ID: {hit.id}")
    print(f"FILE: {filename}")
    print(f"DOCUMENT ID: {document_id}")
    print(f"CHUNK INDEX: {chunk_index}")

    print("\nTEXT:")
    print("-" * 80)
    print(text)
    print("-" * 80)


print("\nSearch complete.")
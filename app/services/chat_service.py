from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.graph_retrieval_service import GraphRetrievalService
from app.services.qdrant_service import QdrantService
from qdrant_client.http import models as rest
class ChatService:
    def __init__(self) -> None:
        # Keep the same embedding service used during ingestion.
        # Your existing Qdrant vectors were created with BAAI/bge-m3.
        self.embedding_service = EmbeddingService()

        self.qdrant_service = QdrantService(
            vector_size=self.embedding_service.dimension()
        )
        self.graph_retrieval_service = GraphRetrievalService()

        # Gemini through LangChain
        self.llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0,
        max_retries=0,
        )

        # RAG prompt
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
You are a retrieval-grounded assistant.

Answer the user's question using only the supplied context.

Rules:
1. Do not invent facts.
2. If the context does not contain enough information, say:
   "I could not find enough information in the indexed documents."
3. Cite supporting chunks using their labels, for example [1] or [2].
4. Keep the answer concise and factual.
5. Do not claim information that is absent from the context.
6. If multiple context chunks conflict, mention the conflict.
""".strip(),
                ),
                (
                    "human",
                    """
Context:
{context}

Question:
{question}

Answer using only the context above.
""".strip(),
                ),
            ]
        )

        # LangChain LCEL chain
        self.chain = (
            self.prompt
            | self.llm
            | StrOutputParser()
        )

    def answer(
        self,
        question: str,
        top_k: int = 1,
    ) -> dict[str, Any]:

        question = question.strip()

        if not question:
            raise ValueError(
                "Question may not be empty."
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1."
            )

        graph_context = self.graph_retrieval_service.retrieve_context(question)
        document_ids = graph_context.get("document_ids", [])

        # -------------------------------------------------
        # 1. Embed query with SAME model used for ingestion
        # -------------------------------------------------

        vector = self.embedding_service.embed_texts([question])[0]

        if hasattr(vector, "detach"):
            vector = vector.detach().cpu().tolist()
        elif hasattr(vector, "tolist"):
            vector = vector.tolist()

        print("Graph document ids:", document_ids)

        query_filter = None

        if document_ids:
            query_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="document_id",
                        match=rest.MatchAny(any=document_ids),
                    )
                ]
            )
        print(query_filter)
        points = self.qdrant_service.query_vectors(
            vector,
            limit=top_k,
            filter=query_filter,
        )

        source_items: list[dict[str, Any]] = []
        context_blocks: list[str] = []

        # -------------------------------------------------
        # 3. Convert retrieved points into RAG context
        # -------------------------------------------------

        for index, point in enumerate(
            points,
            start=1,
        ):
            payload = point.payload or {}

            chunk_text = str(
                payload.get("text", "")
            ).strip()

            document_id = str(
                payload.get("document_id", "")
            )

            original_filename = str(
                payload.get(
                    "original_filename",
                    "",
                )
            )

            chunk_index = payload.get(
                "chunk_index",
                0,
            )

            score = (
                float(point.score)
                if getattr(
                    point,
                    "score",
                    None,
                ) is not None
                else None
            )

            citation = (
                f"{original_filename or document_id}"
                f"#{chunk_index}"
            )

            if chunk_text:
                context_blocks.append(
                    f"""[{index}]
Source: {citation}
Similarity score: {score}

{chunk_text}"""
                )

            source_items.append(
                {
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "original_filename":
                        original_filename,
                    "text": chunk_text,
                    "score": score,
                    "citation": citation,
                }
            )

        # -------------------------------------------------
        # 4. Handle no retrieval results
        # -------------------------------------------------

        graph_facts = graph_context.get("facts", [])
        graph_section = ""
        if graph_facts:
            graph_section = "Graph facts:\n" + "\n".join(graph_facts)

        context = "\n\n---\n\n".join(context_blocks)
        if graph_section:
            context = f"{graph_section}\n\n---\n\n{context}" if context else graph_section

        if not context:
            return {
                "question": question,
                "answer": (
                    "No relevant content was found "
                    "in the vector store for that question."
                ),
                "sources": [],
                "context": "",
            }

        # -------------------------------------------------
        # 5. Send retrieved context to Gemini via LangChain
        # -------------------------------------------------
        print(context)
       
        try:
            answer = self.chain.invoke(
                {
                    "question": question,
                    "context": context,
                }
            )
        except Exception as e:
            print(f"LLM Error: {e}")

            answer = (
                "The language model is currently unavailable or its quota has been "
                "exceeded. The following information was retrieved from the knowledge base:\n\n"
            )

            for i, source in enumerate(source_items, start=1):
                if source["text"]:
                    answer += f"[{i}] {source['text'][:300]}\n\n"

        # -------------------------------------------------
        # 6. Return API response
        # -------------------------------------------------

        return {
            "question": question,
            "answer": answer.strip(),
            "sources": source_items,
            "context": context,
        }
from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.services.agentic_rag import AgenticRAGService
from app.services.embedding_service import EmbeddingService
from app.services.graph_retrieval_service import GraphRetrievalService
from app.services.history_service import HistoryService
from app.services.qdrant_service import QdrantService

class ChatService:
    def __init__(self) -> None:
        # Keep the same embedding service used during ingestion.
        # Your existing Qdrant vectors were created with BAAI/bge-m3.
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService(
            vector_size=self.embedding_service.dimension()
        )
        self.graph_retrieval_service = GraphRetrievalService()
        self.history_service = HistoryService()
        self.agent = AgenticRAGService(
            embedding_service=self.embedding_service,
            qdrant_service=self.qdrant_service,
            graph_service=self.graph_retrieval_service,
        )

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

        agent_result = self.agent.run(question, top_k=top_k)
        context = agent_result.get("context", "")
        sources = agent_result.get("sources", [])

        if not context:
            answer = "I could not find enough information in the indexed documents."
            self.history_service.save_entry(question, answer, sources)
            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "context": "",
            }

        # -------------------------------------------------
        # 5. Send retrieved context to Gemini via LangChain
        # -------------------------------------------------
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

            for i, source in enumerate(sources, start=1):
                if source["text"]:
                    answer += f"[{i}] {source['text'][:300]}\n\n"

        answer = answer.strip()
        self.history_service.save_entry(question, answer, sources)

        # -------------------------------------------------
        # 6. Return API response
        # -------------------------------------------------

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "context": context,
        }
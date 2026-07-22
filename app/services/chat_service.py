from __future__ import annotations

import time
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.services.agentic_rag import AgenticRAGService
from app.services.compliance_service import ComplianceService
from app.services.embedding_service import EmbeddingService
from app.services.graph_retrieval_service import GraphRetrievalService
from app.services.history_service import HistoryService
# from app.services.metrics_service import metrics_service
from app.services.qdrant_service import QdrantService
from app.services.ticket_service import TicketService

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
        self.ticket_service = TicketService()
        self.compliance_service = ComplianceService()
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
You are Omniscient, an AI-powered industrial knowledge assistant.

Answer ONLY using the provided context.

Rules:
1. Never invent facts or use external knowledge.
2. If the answer exists, respond clearly and concisely.
3. If the exact answer is unavailable but related information exists, state that it is not explicitly available and summarize the relevant information.
4. If the context contains conflicting information, mention the conflict without guessing.
5. For questions about operational status, maintenance status, or compliance, report them only if explicitly stated in the context.
6. If the context is unrelated or insufficient, reply:
   "I could not find enough information in the indexed documents."
7. Cite supporting chunks using labels such as [1], [2], and [3].
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

    def answer(self, question: str, top_k: int = 1,) -> dict[str, Any]:
        question = question.strip()
        if not question:
            raise ValueError("Question may not be empty.")

        if top_k < 1:
            raise ValueError( "top_k must be at least 1.")

        start = time.perf_counter()
        agent_result = self.agent.run(question, top_k=top_k)
        elapsed = (time.perf_counter() - start) * 1000
        # metrics_service.record_response_time(elapsed)
        context = agent_result.get("context", "")
        sources = agent_result.get("sources", [])

        if not context:
            answer = "I could not find enough information in the indexed documents."
            self.history_service.save_entry(question, answer, sources, enterprise_actions={})
            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "context": "",
                "enterprise_actions": {},
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

        ticket_suggestion = self.ticket_service.build_ticket_suggestion(question, answer, context)
        compliance_context = "\n".join([context, *[source.get("text", "") for source in sources]])
        compliance_result = None
        if self.compliance_service.should_offer_compliance(compliance_context):
            compliance_result = self.compliance_service.evaluate_context(compliance_context)

        enterprise_actions = {}
        if ticket_suggestion.get("available"):
            enterprise_actions["ticket"] = ticket_suggestion["ticket"]
        if compliance_result and compliance_result.get("applicable"):
            enterprise_actions["compliance"] = compliance_result

        answer = answer.strip()
        self.history_service.save_entry(
            question,
            answer,
            sources,
            enterprise_actions=enterprise_actions,
        )

        # -------------------------------------------------
        # 6. Return API response
        # -------------------------------------------------

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "context": context,
            "enterprise_actions": enterprise_actions,
        }
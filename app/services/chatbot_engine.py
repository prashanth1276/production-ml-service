"""Chatbot engine: retrieves products, calls LLM, returns a response."""
import asyncio
import logging

from langchain.prompts import PromptTemplate

from app.services.rec_engine import rec_engine
from app.utils.db import db
from app.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


PROMPT = PromptTemplate(
    input_variables=["query", "context"],
    template=(
        "You are a helpful retail assistant.\n"
        "User query: {query}\n"
        "Available products:\n{context}\n\n"
        "Provide a friendly, concise recommendation in 2 sentences."
    ),
)


class ChatbotEngine:
    def __init__(self):
        self.llm = get_llm_client()

    def _parse_budget(self, query: str) -> float | None:
        if "under" not in query.lower():
            return None
        try:
            return float(query.lower().split("under")[1].split()[0])
        except (IndexError, ValueError):
            return None

    async def get_response(self, user_query: str, user_id: str | None = None) -> str:
        budget = self._parse_budget(user_query)
        product_ids = await rec_engine.get_recommendations(
            user_query, user_id=user_id, top_k=5
        )
        products = db.get_products_by_ids(product_ids)

        if budget is not None:
            products = [
                p for p in products if p.get("price", float("inf")) <= budget
            ]

        if products:
            context = "\n".join(
                f"- {p['name']}: {p.get('description', '')} (₹{p.get('price', 'N/A')})"
                for p in products
            )
        else:
            context = "No matching products found."

        prompt = PROMPT.format(query=user_query, context=context)
        return self.llm.generate(prompt, max_tokens=150)

    async def get_batch_response(
        self, queries: list[str], user_id: str | None = None
    ) -> list[str]:
        return await asyncio.gather(
            *(self.get_response(q, user_id=user_id) for q in queries)
        )


_engine: ChatbotEngine | None = None


def get_chatbot_engine() -> ChatbotEngine:
    global _engine
    if _engine is None:
        _engine = ChatbotEngine()
    return _engine


class _LazyChat:
    def __getattr__(self, name):
        return getattr(get_chatbot_engine(), name)


chatbot_engine = _LazyChat()
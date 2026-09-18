"""Retail chatbot engine using recommendations and an LLM."""

import asyncio
import re

from app.services.rec_engine import rec_engine
from app.utils.db import db
from app.utils.llm_client import get_llm_client

PROMPT_TEMPLATE = (
    "You are a helpful retail assistant.\n\n"
    "User query:\n{query}\n\n"
    "Available products:\n{context}\n\n"
    "Give a friendly, concise recommendation in exactly 2 sentences. "
    "Use only information contained in the available products. "
    "Do not invent product names, prices, features, or specifications."
)


class ChatbotEngine:
    def __init__(self):
        self.llm = get_llm_client()

    @staticmethod
    def _parse_budget(query: str) -> float | None:
        """Extract a numeric budget from a user query."""

        normalized = query.lower().replace(",", "")

        patterns = [
            r"(?:under|below|less\s+than)"
            r"\s*₹?\s*(?:rs\.?|inr)?\s*"
            r"(\d+(?:\.\d+)?)",
            r"(?:₹|rs\.?|inr)\s*"
            r"(\d+(?:\.\d+)?)"
            r"\s*(?:or\s+less|maximum|max)?",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized)

            if match:
                try:
                    return float(match.group(1))
                except (TypeError, ValueError):
                    return None

        return None

    @staticmethod
    def _safe_price(product: dict) -> float | None:
        """Convert a product price into a float."""

        price = product.get("price")

        if price is None:
            return None

        if isinstance(price, (int, float)):
            return float(price)

        try:
            cleaned = (
                str(price)
                .replace(",", "")
                .replace("₹", "")
                .replace("Rs.", "")
                .replace("Rs", "")
                .replace("INR", "")
                .strip()
            )

            return float(cleaned)

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_product(product: dict) -> str:
        """Format a product for the LLM context."""

        name = str(
            product.get(
                "name",
                "Unnamed product",
            )
        )

        description = str(
            product.get(
                "description",
                "",
            )
        ).strip()

        price = ChatbotEngine._safe_price(product)

        if price is None:
            price_text = "Price unavailable"
        else:
            price_text = f"₹{price:,.2f}"

        if description:
            return f"- {name}: {description} ({price_text})"

        return f"- {name} ({price_text})"

    async def get_response(
        self,
        user_query: str,
        user_id: str | None = None,
    ) -> str:
        user_query = user_query.strip()

        if not user_query:
            return "Please enter a product query."

        budget = self._parse_budget(user_query)

        product_ids = await rec_engine.get_recommendations(
            user_query,
            user_id=user_id,
            top_k=5,
        )

        products = db.get_products_by_ids(product_ids)

        # Apply budget filtering after retrieval.
        if budget is not None:
            products = [
                product
                for product in products
                if (self._safe_price(product) is not None and self._safe_price(product) <= budget)
            ]

        if products:
            context = "\n".join(self._format_product(product) for product in products)
        else:
            context = "No matching products found."

        prompt = PROMPT_TEMPLATE.format(
            query=user_query,
            context=context,
        )

        return self.llm.generate(
            prompt,
            max_tokens=500,
        )

    async def get_batch_response(
        self,
        queries: list[str],
        user_id: str | None = None,
    ) -> list[str]:
        if not queries:
            return []

        return await asyncio.gather(
            *(
                self.get_response(
                    query,
                    user_id=user_id,
                )
                for query in queries
            )
        )


_engine: ChatbotEngine | None = None


def get_chatbot_engine() -> ChatbotEngine:
    global _engine

    if _engine is None:
        _engine = ChatbotEngine()

    return _engine


class _LazyChat:
    def __getattr__(self, name):
        return getattr(
            get_chatbot_engine(),
            name,
        )


chatbot_engine = _LazyChat()

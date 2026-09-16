"""Product description generator using LLM."""

import logging

from langchain.prompts import PromptTemplate

from app.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


PROMPT = PromptTemplate(
    input_variables=["name", "category", "material"],
    template=(
        "Generate a 3-sentence SEO-friendly product description (max 100 tokens) "
        "for a {category} product named '{name}' made of {material}. "
        "Include keywords like '{category} {name}', 'best {category}', "
        "and 'high-quality {material}'. Highlight key features and end with "
        "a call to action."
    ),
)


class DescriptionGenerator:
    def __init__(self):
        self.llm = get_llm_client()

    def generate_description(self, name: str, category: str, material: str) -> str:
        prompt = PROMPT.format(name=name, category=category, material=material)
        return self.llm.generate(prompt, max_tokens=200)


_generator: DescriptionGenerator | None = None


def get_description_generator() -> DescriptionGenerator:
    global _generator
    if _generator is None:
        _generator = DescriptionGenerator()
    return _generator


class _LazyGen:
    def __getattr__(self, name):
        return getattr(get_description_generator(), name)


description_generator = _LazyGen()

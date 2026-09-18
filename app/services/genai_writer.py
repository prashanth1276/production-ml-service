"""AI product-description generator."""

from app.utils.llm_client import get_llm_client


PROMPT_TEMPLATE = (
    "Generate a 3-sentence SEO-friendly product description "
    "(maximum 100 tokens) for the following product.\n\n"
    "Product name: {name}\n"
    "Category: {category}\n"
    "Material: {material}\n\n"
    "Requirements:\n"
    "- Naturally include the product name and category.\n"
    "- Mention the material.\n"
    "- Highlight useful product features.\n"
    "- Keep the description concise and natural.\n"
    "- End with a clear call to action.\n"
    "- Do not use headings or bullet points.\n"
)


class DescriptionGenerator:
    """Generate product descriptions using the configured LLM."""

    def __init__(self):
        self.llm = get_llm_client()

    def generate_description(
        self,
        name: str,
        category: str,
        material: str,
    ) -> str:
        prompt = PROMPT_TEMPLATE.format(
            name=name.strip(),
            category=category.strip(),
            material=material.strip(),
        )

        return self.llm.generate(
            prompt,
            max_tokens=150,
        )


_generator: DescriptionGenerator | None = None


def get_description_generator() -> DescriptionGenerator:
    global _generator

    if _generator is None:
        _generator = DescriptionGenerator()

    return _generator


class _LazyGen:
    def __getattr__(self, name):
        return getattr(
            get_description_generator(),
            name,
        )


description_generator = _LazyGen()
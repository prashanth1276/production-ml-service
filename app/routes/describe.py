import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.genai_writer import description_generator
from app.utils.cache import cache_get, cache_set
from app.utils.db import db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/description", summary="Generate product description")
async def get_description(
    product_id: str = Query(..., description="Product ID")
):
    if not product_id or not isinstance(product_id, str):
        raise HTTPException(status_code=422, detail="Invalid product ID format")

    cache_key = f"desc:{product_id}"
    cached = await cache_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            pass

    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    loop = asyncio.get_event_loop()
    description = await loop.run_in_executor(
        None,
        description_generator.generate_description,
        product.get("name", "Unknown Product"),
        product.get("category", "Unknown Category"),
        product.get("material", "cotton"),
    )

    result = {
        "product_id": product_id,
        "name": product.get("name"),
        "description": description,
    }
    await cache_set(cache_key, json.dumps(result), ttl=86400)
    return result
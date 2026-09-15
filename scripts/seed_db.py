"""Seed MongoDB with products and users. Run once before starting the API.

    python scripts/seed_db.py
"""
import json
import sys
from pathlib import Path

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.config import get_settings


def main():
    settings = get_settings()
    client = MongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=5000,
    )

    client.admin.command("ping")
    db = client["retail_db"]

    utils = Path(__file__).resolve().parent.parent / "app" / "utils"
    with open(utils / "products.json") as f:
        products = json.load(f)
    with open(utils / "users.json") as f:
        users = json.load(f)

    db.products.drop()
    db.users.drop()
    db.products.insert_many(products)
    db.users.insert_many(users)

    print(f"✓ Seeded {len(products)} products and {len(users)} users")
    client.close()


if __name__ == "__main__":
    main()
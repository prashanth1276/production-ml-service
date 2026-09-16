"""MongoDB access layer."""

import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.utils.config import get_settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        settings = get_settings()
        self.client = MongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
        self.db = self.client["retail_db"]
        self.products = self.db["products"]
        self.users = self.db["users"]

    def ping(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except PyMongoError as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False

    def get_products(self) -> list[dict]:
        try:
            return list(self.products.find({}, {"_id": 0}))
        except PyMongoError as e:
            logger.error(f"get_products failed: {e}")
            return []

    def get_product(self, product_id: str) -> dict | None:
        try:
            return self.products.find_one({"id": product_id}, {"_id": 0})
        except PyMongoError as e:
            logger.error(f"get_product failed: {e}")
            return None

    def get_user(self, user_id: str) -> dict | None:
        try:
            return self.users.find_one({"user_id": user_id}, {"_id": 0})
        except PyMongoError as e:
            logger.error(f"get_user failed: {e}")
            return None

    def get_products_by_ids(self, product_ids: list[str]) -> list[dict]:
        if not product_ids:
            return []
        try:
            return list(self.products.find({"id": {"$in": product_ids}}, {"_id": 0}))
        except PyMongoError as e:
            logger.error(f"get_products_by_ids failed: {e}")
            return []


# Lazy singleton so imports don't require MongoDB to be running
_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


# Module-level for backwards compatibility
class _LazyDB:
    def __getattr__(self, name):
        return getattr(get_db(), name)


db = _LazyDB()

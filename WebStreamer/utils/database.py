import time
import math
import logging
import motor.motor_asyncio
import pymongo
from bson.objectid import ObjectId
from bson.errors import InvalidId
from WebStreamer.server.exceptions import FIleNotFound
from WebStreamer.vars import Var

# Set up basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri: str, database_name: str):
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
            self.db = self._client[database_name]
            self.users_col = self.db.users
            self.blacklist_col = self.db.blacklist
            self.files_col = self.db.file
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def create_indexes(self):
        """Create necessary indexes for efficient queries."""
        try:
            await self.users_col.create_index([("id", pymongo.ASCENDING)], unique=True)
            await self.blacklist_col.create_index([("id", pymongo.ASCENDING)], unique=True)
            await self.files_col.create_index([
                ("user_id", pymongo.ASCENDING), 
                ("file_unique_id", pymongo.ASCENDING)
            ])
            await self.files_col.create_index([("file_name", pymongo.TEXT)])
            logger.info("Database indexes created successfully.")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    # -------------------- USER MANAGEMENT -------------------- #
    def _new_user(self, user_id: int) -> dict:
        return {
            "id": user_id,
            "join_date": time.time(),
            "agreed_to_tos": False,
            "Plan": "Free"
        }

    async def add_user(self, user_id: int):
        """Add a new user."""
        try:
            user = self._new_user(user_id)
            await self.users_col.insert_one(user)
            logger.info(f"New user added: {user_id}")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")

    async def get_user(self, user_id: int):
        try:
            return await self.users_col.find_one({"id": int(user_id)})
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def delete_user(self, user_id: int):
        try:
            await self.users_col.delete_many({"id": int(user_id)})
            logger.info(f"User {user_id} deleted.")
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")

    async def total_users_count(self) -> int:
        try:
            return await self.users_col.count_documents({})
        except Exception as e:
            logger.error(f"Error counting total users: {e}")
            return 0

    async def get_all_users(self):
        try:
            cursor = self.users_col.find({})
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []

    async def agree_to_tos(self, user_id: int):
        try:
            await self.users_col.update_one(
                {"id": int(user_id)},
                {"$set": {"agreed_to_tos": True, "when_agreed_to_tos": time.time()}}
            )
            logger.info(f"User {user_id} agreed to TOS.")
        except Exception as e:
            logger.error(f"Error updating TOS for user {user_id}: {e}")

    # -------------------- BAN MANAGEMENT -------------------- #
    def _black_user(self, user_id: int) -> dict:
        return {"id": user_id, "ban_date": time.time()}

    async def ban_user(self, user_id: int):
        try:
            user = self._black_user(user_id)
            await self.blacklist_col.insert_one(user)
            await self.delete_user(user_id)
            logger.info(f"User {user_id} has been banned.")
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")

    async def unban_user(self, user_id: int):
        try:
            await self.blacklist_col.delete_one({"id": int(user_id)})
            logger.info(f"User {user_id} has been unbanned.")
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")

    async def is_user_banned(self, user_id: int) -> bool:
        try:
            user = await self.blacklist_col.find_one({"id": int(user_id)})
            return bool(user)
        except Exception as e:
            logger.error(f"Error checking ban status for user {user_id}: {e}")
            return False

    async def total_banned_users_count(self) -> int:
        try:
            return await self.blacklist_col.count_documents({})
        except Exception as e:
            logger.error(f"Error counting banned users: {e}")
            return 0

    # -------------------- FILE MANAGEMENT -------------------- #
    async def add_file(self, file_info: dict):
        try:
            file_info["time"] = time.time()
            existing = await self.get_file_by_fileuniqueid(file_info["user_id"], file_info["file_unique_id"])
            if existing:
                return existing["_id"]
            result = await self.files_col.insert_one(file_info)
            logger.info(f"New file added for user {file_info['user_id']} with ID {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error adding file for user {file_info.get('user_id')}: {e}")
            return None

    async def find_files(self, user_id: int, page: int = 1, limit: int = 10):
        try:
            offset = (page - 1) * limit
            cursor = self.files_col.find({"user_id": user_id}).sort("_id", -1).skip(offset).limit(limit)
            files_list = await cursor.to_list(length=limit)
            total_files = await self.files_col.count_documents({"user_id": user_id})
            total_pages = math.ceil(total_files / limit)
            return files_list, total_files, total_pages
        except Exception as e:
            logger.error(f"Error finding files for user {user_id}: {e}")
            return [], 0, 0

    async def search_files(self, user_id: int, query: str, page: int = 1, limit: int = 10):
        try:
            offset = (page - 1) * limit
            query_filter = {"user_id": user_id, "file_name": {"$regex": query, "$options": "i"}}
            cursor = self.files_col.find(query_filter).sort("_id", -1).skip(offset).limit(limit)
            files_list = await cursor.to_list(length=limit)
            total_files = await self.files_col.count_documents(query_filter)
            total_pages = math.ceil(total_files / limit)
            return files_list, total_files, total_pages
        except Exception as e:
            logger.error(f"Error searching files for user {user_id} with query '{query}': {e}")
            return [], 0, 0

    async def get_file(self, file_id: str):
        try:
            file_info = await self.files_col.find_one({"_id": ObjectId(file_id)})
            if not file_info:
                raise FIleNotFound(f"File with ID {file_id} not found.")
            return file_info
        except InvalidId:
            raise FIleNotFound(f"Invalid file ID: {file_id}")
        except Exception as e:
            logger.error(f"Error getting file {file_id}: {e}")
            raise FIleNotFound(f"Error getting file: {e}")

    async def get_file_by_fileuniqueid(self, user_id: int, file_unique_id: str, many: bool = False):
        try:
            if many:
                cursor = self.files_col.find({"file_unique_id": file_unique_id})
                return await cursor.to_list(length=None)
            file_info = await self.files_col.find_one({"user_id": user_id, "file_unique_id": file_unique_id})
            return file_info
        except Exception as e:
            logger.error(f"Error fetching file by unique ID for user {user_id}: {e}")
            return None

    async def delete_one_file(self, file_id: str):
        try:
            await self.files_col.delete_one({"_id": ObjectId(file_id)})
            logger.info(f"File {file_id} deleted successfully.")
        except InvalidId:
            logger.warning(f"Attempted to delete with invalid file ID: {file_id}")
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")

    async def update_file_ids(self, file_id: str, file_ids: dict):
        try:
            await self.files_col.update_one({"_id": ObjectId(file_id)}, {"$set": {"file_ids": file_ids}})
            logger.info(f"File IDs updated for file {file_id}.")
        except InvalidId:
            logger.warning(f"Attempted to update with invalid file ID: {file_id}")
        except Exception as e:
            logger.error(f"Error updating file IDs for file {file_id}: {e}")

    async def total_files(self, user_id: int = None) -> int:
        try:
            if user_id:
                return await self.files_col.count_documents({"user_id": user_id})
            return await self.files_col.count_documents({})
        except Exception as e:
            logger.error(f"Error counting files: {e}")
            return 0

    # -------------------- LINK LIMIT CHECK -------------------- #
    async def link_available(self, user_id: int):
        try:
            if not Var.LINK_LIMIT:
                return True
            user = await self.get_user(user_id)
            if not user:
                return False
            if user.get("Plan") == "Plus":
                return "Plus"
            elif user.get("Plan") == "Free":
                files_count = await self.files_col.count_documents({"user_id": user_id})
                return files_count < Var.LINK_LIMIT
            return False
        except Exception as e:
            logger.error(f"Error checking link availability for user {user_id}: {e}")
            return False

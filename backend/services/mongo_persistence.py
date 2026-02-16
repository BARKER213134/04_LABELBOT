"""
MongoDB Persistence for python-telegram-bot
Stores conversation states, user_data, chat_data, and bot_data in MongoDB
CRITICAL: Saves immediately to MongoDB for multi-pod sync
"""
import logging
import time
from typing import Dict, Any, Optional, Tuple
from telegram.ext import BasePersistence, PersistenceInput

logger = logging.getLogger(__name__)


class MongoPersistence(BasePersistence):
    """MongoDB-based persistence - saves IMMEDIATELY for multi-pod deployments"""
    
    def __init__(self, db, store_data: Optional[PersistenceInput] = None):
        super().__init__(
            store_data=store_data or PersistenceInput(
                bot_data=True,
                chat_data=True,
                user_data=True,
                callback_data=False
            ),
            update_interval=0  # Save immediately, no batching
        )
        self.db = db
        self.conversations_collection = db.ptb_conversations
        self.user_data_collection = db.ptb_user_data
        self.chat_data_collection = db.ptb_chat_data
        self.bot_data_collection = db.ptb_bot_data
        logger.warning("[PERSIST] MongoPersistence initialized with IMMEDIATE saves")
    
    # ===== Conversations - ALWAYS read from MongoDB =====
    
    async def get_conversations(self, name: str) -> Dict[Tuple, Any]:
        """Get all conversations - ALWAYS from MongoDB for multi-pod sync"""
        start = time.time()
        conversations = {}
        try:
            async for doc in self.conversations_collection.find({'name': name}):
                key = tuple(doc.get('key', []))
                state = doc.get('state')
                conversations[key] = state
            
            elapsed = (time.time() - start) * 1000
            logger.warning(f"[PERSIST] get_conversations('{name}'): {len(conversations)} items, {elapsed:.1f}ms")
            
        except Exception as e:
            logger.error(f"[PERSIST] Error loading conversations: {e}")
        
        return conversations
    
    async def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ) -> None:
        """Update conversation state - IMMEDIATELY to MongoDB"""
        start = time.time()
        try:
            if new_state is None:
                await self.conversations_collection.delete_one({
                    'name': name,
                    'key': list(key)
                })
                elapsed = (time.time() - start) * 1000
                logger.warning(f"[PERSIST] DELETE conversation('{name}', {key}): {elapsed:.1f}ms")
            else:
                await self.conversations_collection.update_one(
                    {'name': name, 'key': list(key)},
                    {'$set': {'name': name, 'key': list(key), 'state': new_state}},
                    upsert=True
                )
                elapsed = (time.time() - start) * 1000
                logger.warning(f"[PERSIST] SAVE conversation('{name}', {key}, state={new_state}): {elapsed:.1f}ms")
        except Exception as e:
            logger.error(f"[PERSIST] Error updating conversation: {e}")
    
    # ===== User Data - ALWAYS read from MongoDB =====
    
    async def get_user_data(self) -> Dict[int, Dict]:
        """Get all user data - ALWAYS from MongoDB"""
        user_data = {}
        try:
            async for doc in self.user_data_collection.find():
                user_id = doc.get('user_id')
                data = doc.get('data', {})
                if user_id:
                    user_data[user_id] = data
        except Exception as e:
            logger.error(f"[PERSIST] Error loading user_data: {e}")
        return user_data
    
    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Update user data - IMMEDIATELY to MongoDB"""
        try:
            await self.user_data_collection.update_one(
                {'user_id': user_id},
                {'$set': {'user_id': user_id, 'data': data}},
                upsert=True
            )
            logger.debug(f"[PERSIST] Saved user_data for {user_id}")
        except Exception as e:
            logger.error(f"[PERSIST] Error updating user_data: {e}")
    
    async def refresh_user_data(self, user_id: int, user_data: Dict) -> Optional[Dict]:
        """Refresh user data from MongoDB"""
        try:
            doc = await self.user_data_collection.find_one({'user_id': user_id})
            if doc:
                return doc.get('data', {})
        except Exception as e:
            logger.error(f"[PERSIST] Error refreshing user_data: {e}")
        return user_data
    
    async def drop_user_data(self, user_id: int) -> None:
        """Delete user data"""
        try:
            await self.user_data_collection.delete_one({'user_id': user_id})
        except Exception as e:
            logger.error(f"[PERSIST] Error dropping user_data: {e}")
    
    # ===== Chat Data =====
    
    async def get_chat_data(self) -> Dict[int, Dict]:
        """Get all chat data - ALWAYS from MongoDB"""
        chat_data = {}
        try:
            async for doc in self.chat_data_collection.find():
                chat_id = doc.get('chat_id')
                data = doc.get('data', {})
                if chat_id:
                    chat_data[chat_id] = data
        except Exception as e:
            logger.error(f"[PERSIST] Error loading chat_data: {e}")
        return chat_data
    
    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Update chat data - IMMEDIATELY to MongoDB"""
        try:
            await self.chat_data_collection.update_one(
                {'chat_id': chat_id},
                {'$set': {'chat_id': chat_id, 'data': data}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"[PERSIST] Error updating chat_data: {e}")
    
    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> Optional[Dict]:
        """Refresh chat data from MongoDB"""
        try:
            doc = await self.chat_data_collection.find_one({'chat_id': chat_id})
            if doc:
                return doc.get('data', {})
        except Exception as e:
            logger.error(f"[PERSIST] Error refreshing chat_data: {e}")
        return chat_data
    
    async def drop_chat_data(self, chat_id: int) -> None:
        """Delete chat data"""
        try:
            await self.chat_data_collection.delete_one({'chat_id': chat_id})
        except Exception as e:
            logger.error(f"[PERSIST] Error dropping chat_data: {e}")
    
    # ===== Bot Data =====
    
    async def get_bot_data(self) -> Dict:
        """Get bot data - ALWAYS from MongoDB"""
        try:
            doc = await self.bot_data_collection.find_one({'_id': 'bot_data'})
            if doc:
                return doc.get('data', {})
        except Exception as e:
            logger.error(f"[PERSIST] Error loading bot_data: {e}")
        return {}
    
    async def update_bot_data(self, data: Dict) -> None:
        """Update bot data - IMMEDIATELY to MongoDB"""
        try:
            await self.bot_data_collection.update_one(
                {'_id': 'bot_data'},
                {'$set': {'data': data}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"[PERSIST] Error updating bot_data: {e}")
    
    async def refresh_bot_data(self, bot_data: Dict) -> Dict:
        """Refresh bot data from MongoDB"""
        try:
            doc = await self.bot_data_collection.find_one({'_id': 'bot_data'})
            if doc:
                return doc.get('data', {})
        except Exception as e:
            logger.error(f"[PERSIST] Error refreshing bot_data: {e}")
        return bot_data
    
    # ===== Callback Data (not used) =====
    
    async def get_callback_data(self) -> Optional[Tuple[list, Dict]]:
        return None
    
    async def update_callback_data(self, data: Tuple[list, Dict]) -> None:
        pass
    
    # ===== Flush =====
    
    async def flush(self) -> None:
        """Flush - data is already saved immediately"""
        pass

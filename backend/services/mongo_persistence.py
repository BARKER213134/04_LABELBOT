"""
MongoDB Persistence for python-telegram-bot
Stores conversation states, user_data, chat_data, and bot_data in MongoDB
Uses local cache with short TTL to reduce DB load while staying synced
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from telegram.ext import BasePersistence, PersistenceInput

logger = logging.getLogger(__name__)

# Cache TTL in seconds - short enough to stay synced, long enough to avoid hammering DB
CACHE_TTL = 2.0


class MongoPersistence(BasePersistence):
    """MongoDB-based persistence for python-telegram-bot with local caching"""
    
    def __init__(self, db, store_data: Optional[PersistenceInput] = None):
        super().__init__(
            store_data=store_data or PersistenceInput(
                bot_data=True,
                chat_data=True,
                user_data=True,
                callback_data=False
            ),
            update_interval=1.0  # Batch updates every 1 second
        )
        self.db = db
        self.conversations_collection = db.ptb_conversations
        self.user_data_collection = db.ptb_user_data
        self.chat_data_collection = db.ptb_chat_data
        self.bot_data_collection = db.ptb_bot_data
        
        # Local caches
        self._conversations_cache: Dict[str, Dict[Tuple, Any]] = {}
        self._conversations_cache_time: Dict[str, float] = {}
        self._user_data_cache: Dict[int, Dict] = {}
        self._user_data_cache_time: float = 0
        self._chat_data_cache: Dict[int, Dict] = {}
        self._chat_data_cache_time: float = 0
        self._bot_data_cache: Dict = {}
        self._bot_data_cache_time: float = 0
    
    def _is_cache_valid(self, cache_time: float) -> bool:
        """Check if cache is still valid"""
        return (time.time() - cache_time) < CACHE_TTL
    
    # ===== Conversations =====
    
    async def get_conversations(self, name: str) -> Dict[Tuple, Any]:
        """Get all conversations - from cache if valid, else from MongoDB"""
        # Check cache first
        if name in self._conversations_cache and self._is_cache_valid(self._conversations_cache_time.get(name, 0)):
            return self._conversations_cache[name].copy()
        
        # Load from MongoDB
        conversations = {}
        try:
            async for doc in self.conversations_collection.find({'name': name}):
                key = tuple(doc.get('key', []))
                state = doc.get('state')
                conversations[key] = state
            
            # Update cache
            self._conversations_cache[name] = conversations.copy()
            self._conversations_cache_time[name] = time.time()
            
        except Exception as e:
            logger.error(f"[PERSIST] Error loading conversations: {e}")
            # Return cached data on error
            if name in self._conversations_cache:
                return self._conversations_cache[name].copy()
        
        return conversations
    
    async def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ) -> None:
        """Update conversation state - update cache immediately, DB async"""
        # Update local cache immediately
        if name not in self._conversations_cache:
            self._conversations_cache[name] = {}
        
        if new_state is None:
            self._conversations_cache[name].pop(key, None)
        else:
            self._conversations_cache[name][key] = new_state
        self._conversations_cache_time[name] = time.time()
        
        # Update MongoDB (non-blocking)
        try:
            if new_state is None:
                await self.conversations_collection.delete_one({
                    'name': name,
                    'key': list(key)
                })
            else:
                await self.conversations_collection.update_one(
                    {'name': name, 'key': list(key)},
                    {'$set': {'name': name, 'key': list(key), 'state': new_state}},
                    upsert=True
                )
        except Exception as e:
            logger.error(f"[PERSIST] Error updating conversation: {e}")
    
    # ===== User Data =====
    
    async def get_user_data(self) -> Dict[int, Dict]:
        """Get all user data - from cache if valid"""
        if self._is_cache_valid(self._user_data_cache_time):
            return self._user_data_cache.copy()
        
        user_data = {}
        try:
            async for doc in self.user_data_collection.find():
                user_id = doc.get('user_id')
                data = doc.get('data', {})
                if user_id:
                    user_data[user_id] = data
            
            self._user_data_cache = user_data.copy()
            self._user_data_cache_time = time.time()
            
        except Exception as e:
            logger.error(f"Error loading user_data: {e}")
            return self._user_data_cache.copy()
        
        return user_data
    
    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Update user data - cache immediately, DB async"""
        self._user_data_cache[user_id] = data.copy()
        self._user_data_cache_time = time.time()
        
        try:
            await self.user_data_collection.update_one(
                {'user_id': user_id},
                {'$set': {'user_id': user_id, 'data': data}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating user_data: {e}")
    
    async def refresh_user_data(self, user_id: int, user_data: Dict) -> Optional[Dict]:
        """Refresh user data"""
        if user_id in self._user_data_cache:
            return self._user_data_cache[user_id]
        return user_data
    
    async def drop_user_data(self, user_id: int) -> None:
        """Delete user data"""
        self._user_data_cache.pop(user_id, None)
        try:
            await self.user_data_collection.delete_one({'user_id': user_id})
        except Exception as e:
            logger.error(f"Error dropping user_data: {e}")
    
    # ===== Chat Data =====
    
    async def get_chat_data(self) -> Dict[int, Dict]:
        """Get all chat data"""
        if self._is_cache_valid(self._chat_data_cache_time):
            return self._chat_data_cache.copy()
        
        chat_data = {}
        try:
            async for doc in self.chat_data_collection.find():
                chat_id = doc.get('chat_id')
                data = doc.get('data', {})
                if chat_id:
                    chat_data[chat_id] = data
            
            self._chat_data_cache = chat_data.copy()
            self._chat_data_cache_time = time.time()
            
        except Exception as e:
            logger.error(f"Error loading chat_data: {e}")
            return self._chat_data_cache.copy()
        
        return chat_data
    
    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Update chat data"""
        self._chat_data_cache[chat_id] = data.copy()
        self._chat_data_cache_time = time.time()
        
        try:
            await self.chat_data_collection.update_one(
                {'chat_id': chat_id},
                {'$set': {'chat_id': chat_id, 'data': data}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating chat_data: {e}")
    
    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> Optional[Dict]:
        """Refresh chat data"""
        if chat_id in self._chat_data_cache:
            return self._chat_data_cache[chat_id]
        return chat_data
    
    async def drop_chat_data(self, chat_id: int) -> None:
        """Delete chat data"""
        self._chat_data_cache.pop(chat_id, None)
        try:
            await self.chat_data_collection.delete_one({'chat_id': chat_id})
        except Exception as e:
            logger.error(f"Error dropping chat_data: {e}")
    
    # ===== Bot Data =====
    
    async def get_bot_data(self) -> Dict:
        """Get bot data"""
        if self._is_cache_valid(self._bot_data_cache_time):
            return self._bot_data_cache.copy()
        
        try:
            doc = await self.bot_data_collection.find_one({'_id': 'bot_data'})
            if doc:
                self._bot_data_cache = doc.get('data', {})
                self._bot_data_cache_time = time.time()
                return self._bot_data_cache.copy()
        except Exception as e:
            logger.error(f"Error loading bot_data: {e}")
            return self._bot_data_cache.copy()
        
        return {}
    
    async def update_bot_data(self, data: Dict) -> None:
        """Update bot data"""
        self._bot_data_cache = data.copy()
        self._bot_data_cache_time = time.time()
        
        try:
            await self.bot_data_collection.update_one(
                {'_id': 'bot_data'},
                {'$set': {'data': data}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating bot_data: {e}")
    
    async def refresh_bot_data(self, bot_data: Dict) -> Dict:
        """Refresh bot data"""
        if self._bot_data_cache:
            return self._bot_data_cache.copy()
        return bot_data
    
    # ===== Callback Data (not used) =====
    
    async def get_callback_data(self) -> Optional[Tuple[list, Dict]]:
        """Get callback data - not implemented"""
        return None
    
    async def update_callback_data(self, data: Tuple[list, Dict]) -> None:
        """Update callback data - not implemented"""
        pass
    
    # ===== Flush =====
    
    async def flush(self) -> None:
        """Flush all data to storage - data is already persisted"""
        pass

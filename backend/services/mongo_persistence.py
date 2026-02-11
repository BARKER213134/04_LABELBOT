"""
MongoDB Persistence for python-telegram-bot
Stores conversation states, user_data, chat_data, and bot_data in MongoDB
"""
import logging
from typing import Dict, Any, Optional, Tuple
from telegram.ext import BasePersistence, PersistenceInput
from telegram.ext._contexttypes import ContextTypes
from copy import deepcopy

logger = logging.getLogger(__name__)


class MongoPersistence(BasePersistence):
    """MongoDB-based persistence for python-telegram-bot"""
    
    def __init__(self, db, store_data: Optional[PersistenceInput] = None):
        super().__init__(
            store_data=store_data or PersistenceInput(
                bot_data=True,
                chat_data=True,
                user_data=True,
                callback_data=False
            ),
            update_interval=1  # Save every second
        )
        self.db = db
        self.conversations_collection = db.ptb_conversations
        self.user_data_collection = db.ptb_user_data
        self.chat_data_collection = db.ptb_chat_data
        self.bot_data_collection = db.ptb_bot_data
        
        # In-memory cache
        self._conversations: Dict[str, Dict[Tuple, Any]] = {}
        self._user_data: Dict[int, Dict] = {}
        self._chat_data: Dict[int, Dict] = {}
        self._bot_data: Dict = {}
        self._loaded = False
    
    async def _load_all(self):
        """Load all data from MongoDB on startup"""
        if self._loaded:
            return
        
        try:
            # Load conversations
            async for doc in self.conversations_collection.find():
                name = doc.get('name')
                key = tuple(doc.get('key', []))
                state = doc.get('state')
                if name not in self._conversations:
                    self._conversations[name] = {}
                self._conversations[name][key] = state
            
            # Load user_data
            async for doc in self.user_data_collection.find():
                user_id = doc.get('user_id')
                data = doc.get('data', {})
                if user_id:
                    self._user_data[user_id] = data
            
            # Load chat_data
            async for doc in self.chat_data_collection.find():
                chat_id = doc.get('chat_id')
                data = doc.get('data', {})
                if chat_id:
                    self._chat_data[chat_id] = data
            
            # Load bot_data
            bot_doc = await self.bot_data_collection.find_one({'_id': 'bot_data'})
            if bot_doc:
                self._bot_data = bot_doc.get('data', {})
            
            self._loaded = True
            logger.info(f"MongoPersistence loaded: {len(self._conversations)} conversations, {len(self._user_data)} users")
            
        except Exception as e:
            logger.error(f"Error loading persistence data: {e}")
            self._loaded = True  # Mark as loaded to prevent infinite retries
    
    # ===== Conversations =====
    
    async def get_conversations(self, name: str) -> Dict[Tuple, Any]:
        """Get all conversations for a handler by name"""
        await self._load_all()
        return deepcopy(self._conversations.get(name, {}))
    
    async def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ) -> None:
        """Update conversation state"""
        if name not in self._conversations:
            self._conversations[name] = {}
        
        if new_state is None:
            # End conversation - remove from storage
            self._conversations[name].pop(key, None)
            await self.conversations_collection.delete_one({
                'name': name,
                'key': list(key)
            })
        else:
            # Update conversation state
            self._conversations[name][key] = new_state
            await self.conversations_collection.update_one(
                {'name': name, 'key': list(key)},
                {'$set': {'name': name, 'key': list(key), 'state': new_state}},
                upsert=True
            )
    
    # ===== User Data =====
    
    async def get_user_data(self) -> Dict[int, Dict]:
        """Get all user data"""
        await self._load_all()
        return deepcopy(self._user_data)
    
    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Update user data"""
        self._user_data[user_id] = data
        await self.user_data_collection.update_one(
            {'user_id': user_id},
            {'$set': {'user_id': user_id, 'data': data}},
            upsert=True
        )
    
    async def refresh_user_data(self, user_id: int, user_data: Dict) -> Optional[Dict]:
        """Refresh user data from storage"""
        doc = await self.user_data_collection.find_one({'user_id': user_id})
        if doc:
            return doc.get('data', {})
        return user_data
    
    async def drop_user_data(self, user_id: int) -> None:
        """Delete user data"""
        self._user_data.pop(user_id, None)
        await self.user_data_collection.delete_one({'user_id': user_id})
    
    # ===== Chat Data =====
    
    async def get_chat_data(self) -> Dict[int, Dict]:
        """Get all chat data"""
        await self._load_all()
        return deepcopy(self._chat_data)
    
    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Update chat data"""
        self._chat_data[chat_id] = data
        await self.chat_data_collection.update_one(
            {'chat_id': chat_id},
            {'$set': {'chat_id': chat_id, 'data': data}},
            upsert=True
        )
    
    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> Optional[Dict]:
        """Refresh chat data from storage"""
        doc = await self.chat_data_collection.find_one({'chat_id': chat_id})
        if doc:
            return doc.get('data', {})
        return chat_data
    
    async def drop_chat_data(self, chat_id: int) -> None:
        """Delete chat data"""
        self._chat_data.pop(chat_id, None)
        await self.chat_data_collection.delete_one({'chat_id': chat_id})
    
    # ===== Bot Data =====
    
    async def get_bot_data(self) -> Dict:
        """Get bot data"""
        await self._load_all()
        return deepcopy(self._bot_data)
    
    async def update_bot_data(self, data: Dict) -> None:
        """Update bot data"""
        self._bot_data = data
        await self.bot_data_collection.update_one(
            {'_id': 'bot_data'},
            {'$set': {'data': data}},
            upsert=True
        )
    
    async def refresh_bot_data(self, bot_data: Dict) -> Dict:
        """Refresh bot data from storage"""
        doc = await self.bot_data_collection.find_one({'_id': 'bot_data'})
        if doc:
            return doc.get('data', {})
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
        """Flush all data to storage (called on shutdown)"""
        logger.info("Flushing MongoPersistence data...")
        # Data is already persisted on each update, nothing to do here

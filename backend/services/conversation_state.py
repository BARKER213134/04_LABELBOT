# Persistent conversation state storage using MongoDB
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ConversationStateService:
    """Store conversation state in MongoDB for persistence across pods"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.conversation_states
    
    async def get_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation state for user"""
        try:
            doc = await self.collection.find_one(
                {"user_id": user_id},
                {"_id": 0}
            )
            return doc
        except Exception as e:
            logger.error(f"Error getting state for {user_id}: {e}")
            return None
    
    async def set_state(self, user_id: str, state: int, data: Dict[str, Any]):
        """Set conversation state for user"""
        try:
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "state": state,
                        "data": data,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error setting state for {user_id}: {e}")
    
    async def clear_state(self, user_id: str):
        """Clear conversation state for user"""
        try:
            await self.collection.delete_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error clearing state for {user_id}: {e}")


# Global instance
_state_service = None

def get_state_service(db=None):
    """Get or create state service"""
    global _state_service
    if _state_service is None and db is not None:
        _state_service = ConversationStateService(db)
    return _state_service

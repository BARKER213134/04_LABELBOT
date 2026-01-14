import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from models.user import User, UserCreate, UserBalanceUpdate

logger = logging.getLogger(__name__)


class UsersService:
    """Service for managing users"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.users
    
    async def get_or_create_user(
        self, 
        telegram_id: str, 
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get existing user or create a new one"""
        user = await self.collection.find_one({"telegram_id": telegram_id})
        
        if user:
            # Update username if changed
            update_data = {"updated_at": datetime.now(timezone.utc)}
            if username and user.get("username") != username:
                update_data["username"] = username
            if first_name and user.get("first_name") != first_name:
                update_data["first_name"] = first_name
            if last_name and user.get("last_name") != last_name:
                update_data["last_name"] = last_name
            
            if len(update_data) > 1:  # More than just updated_at
                await self.collection.update_one(
                    {"telegram_id": telegram_id},
                    {"$set": update_data}
                )
            
            user.pop("_id", None)
            return user
        
        # Create new user
        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            balance=0.0,
            total_orders=0,
            total_spent=0.0
        )
        
        user_dict = new_user.model_dump()
        await self.collection.insert_one(user_dict)
        
        logger.info(f"Created new user: {telegram_id} ({username})")
        return user_dict
    
    async def get_user(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get user by telegram_id"""
        user = await self.collection.find_one(
            {"telegram_id": telegram_id},
            {"_id": 0}
        )
        return user
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        cursor = self.collection.find({}, {"_id": 0}).sort("created_at", -1)
        users = await cursor.to_list(length=1000)
        return users
    
    async def update_balance(
        self, 
        telegram_id: str, 
        amount: float, 
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Add or subtract from user balance"""
        user = await self.collection.find_one({"telegram_id": telegram_id})
        
        if not user:
            logger.error(f"User not found: {telegram_id}")
            return None
        
        new_balance = user.get("balance", 0.0) + amount
        
        # Don't allow negative balance
        if new_balance < 0:
            logger.warning(f"Attempted to set negative balance for user {telegram_id}")
            new_balance = 0.0
        
        await self.collection.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "balance": new_balance,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Log balance change
        await self._log_balance_change(telegram_id, amount, new_balance, reason)
        
        logger.info(f"Updated balance for {telegram_id}: {amount:+.2f} -> {new_balance:.2f}")
        
        return await self.get_user(telegram_id)
    
    async def _log_balance_change(
        self, 
        telegram_id: str, 
        amount: float, 
        new_balance: float,
        reason: Optional[str] = None
    ):
        """Log balance changes for audit"""
        log_entry = {
            "telegram_id": telegram_id,
            "amount": amount,
            "new_balance": new_balance,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc)
        }
        await self.db.balance_logs.insert_one(log_entry)
    
    async def deduct_for_order(
        self, 
        telegram_id: str, 
        order_cost: float
    ) -> bool:
        """Deduct balance for order and update stats"""
        user = await self.collection.find_one({"telegram_id": telegram_id})
        
        if not user:
            return False
        
        current_balance = user.get("balance", 0.0)
        
        if current_balance < order_cost:
            logger.warning(f"Insufficient balance for {telegram_id}: {current_balance} < {order_cost}")
            return False
        
        new_balance = current_balance - order_cost
        
        await self.collection.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "balance": new_balance,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$inc": {
                    "total_orders": 1,
                    "total_spent": order_cost
                }
            }
        )
        
        await self._log_balance_change(
            telegram_id, 
            -order_cost, 
            new_balance, 
            "Order payment"
        )
        
        return True
    
    async def check_balance(self, telegram_id: str, required_amount: float) -> bool:
        """Check if user has sufficient balance"""
        user = await self.collection.find_one({"telegram_id": telegram_id})
        
        if not user:
            return False
        
        return user.get("balance", 0.0) >= required_amount
    
    async def get_balance_history(
        self, 
        telegram_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get balance change history for a user"""
        cursor = self.db.balance_logs.find(
            {"telegram_id": telegram_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return await cursor.to_list(length=limit)

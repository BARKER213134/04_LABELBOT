from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from database import Database
from services.users_service import UsersService
from models.user import UserBalanceUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


def get_users_service():
    return UsersService(Database.db)


@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_users(service: UsersService = Depends(get_users_service)):
    """Get all users"""
    users = await service.get_all_users()
    return users


@router.get("/{telegram_id}", response_model=Dict[str, Any])
async def get_user(
    telegram_id: str,
    service: UsersService = Depends(get_users_service)
):
    """Get user by telegram_id"""
    user = await service.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/balance", response_model=Dict[str, Any])
async def update_balance(
    update: UserBalanceUpdate,
    service: UsersService = Depends(get_users_service)
):
    """Update user balance (add or subtract)"""
    user = await service.update_balance(
        telegram_id=update.telegram_id,
        amount=update.amount,
        reason=update.reason
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.get("/{telegram_id}/balance-history", response_model=List[Dict[str, Any]])
async def get_balance_history(
    telegram_id: str,
    limit: int = 50,
    service: UsersService = Depends(get_users_service)
):
    """Get balance change history for a user"""
    history = await service.get_balance_history(telegram_id, limit)
    return history

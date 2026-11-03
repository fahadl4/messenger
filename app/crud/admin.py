from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserUpdate

# ///////////////////////////////For Admin\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

async def update_user_by_id(db: AsyncSession, user_id: int, user_data: UserUpdate):
    update_data = user_data.model_dump(
        exclude_unset=True
    )
    if "email" in update_data:
        result = await db.execute(select(User).where(User.email == update_data["email"], User.deleted_at.is_(None)))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email already exist."
            )
    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])
    
    updated_data = await db.execute(update(User).where(User.id == user_id).values(**update_data).returning(User))
    user = updated_data.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code="404", detail="User Not Found")

    await db.commit()
    return user

async def delete_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user_data = result.scalar_one_or_none()

    if user_data is None:
        raise HTTPException(
            status_code=404,
            detail="User Not Found"
        )
    
    user_data.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user_data)
    return {
        "messgae": "User Deleted Successfully."
    }
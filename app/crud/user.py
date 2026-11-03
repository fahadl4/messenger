from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from app.models.user import User
from app.schemas.auth import UserLogin
from app.schemas.user import UserRegistration, UserUpdate, ChangePassword
from app.core.security import create_access_token, hash_password, verify_password

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\For All\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    
async def get_all_users(
    db: AsyncSession,
    current_user_id: int
):
    result = await db.execute(
        select(User).where(User.id != current_user_id, User.deleted_at.is_(None))
    )
    return result.scalars().all()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(User).where(
            User.email == email,
            User.deleted_at.is_(None)
        )
    )

    return result.scalar_one_or_none()

async def registration(db: AsyncSession, user_data: UserRegistration):
    result = await db.execute(select(User).where(User.email == user_data.email, User.deleted_at.is_(None)))
    existing_data = result.scalar_one_or_none()
    
    if existing_data:
        raise HTTPException(
            status_code=404,
            detail="Email already registered!!!"
        )
    
    new_user = User(
        name = user_data.name,
        email = user_data.email,
        password = hash_password(user_data.password)
    )
    db.add(new_user)
    
    await db.commit()
    await db.refresh(new_user)
    
    return new_user

async def userLogin(db: AsyncSession, user_data: UserLogin):
    result = await db.execute(select(User).where(User.email == user_data.email, User.deleted_at.is_(None)))
    existing_data = result.scalar_one_or_none()
    
    if existing_data is None:
        raise HTTPException(
            status_code=404,
            detail="User doesn't exist!!!"
        )
    if not verify_password(user_data.password, existing_data.password):
        raise HTTPException(
            status_code=404,
            detail="Invalid Email or Password!!!"
        )
    token = create_access_token(existing_data.id, existing_data.role)
    
    return {
        "access_token": token,
        "token_type": "bearer"
    }


async def update_me(db: AsyncSession, user: User, user_data: UserUpdate):
    update_data = user_data.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != user.email:
        result = await db.execute(
            select(User).where(
                User.email == update_data["email"],
                User.deleted_at.is_(None),
                User.id != user.id,
            )
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email already exists!",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user


async def change_password(
    db: AsyncSession,
    user: User,
    password_data: ChangePassword,
):
    if not verify_password(
        password_data.current_password,
        user.password,
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect.",
        )

    if verify_password(password_data.new_password, user.password):
        raise HTTPException(
            status_code=400,
            detail="New password must be different from the current password.",
        )

    user.password = hash_password(password_data.new_password)

    await db.commit()
    await db.refresh(user)

    return {"message": "Password changed successfully."}


async def deleteUser(db: AsyncSession, user_data: User):
    user_data.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user_data)
    return user_data
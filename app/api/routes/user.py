from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.crud.user import (
    deleteUser,
    get_all_users,
    update_me,
    get_user_by_email,
    change_password,
)
from app.db.database_connection import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, ChangePassword

import uuid
from pathlib import Path

from fastapi import UploadFile, File

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get("", response_model=list[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_all_users(db, current_user.id)


@router.get("/search", response_model=UserResponse)
async def search_user(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await get_user_by_email(db, email)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot start a chat with yourself",
        )

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
async def updateMe(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await update_me(db, current_user, user_data)


@router.patch("/me/password")
async def change_my_password(
    password_data: ChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await change_password(db, current_user, password_data)


@router.delete("/me")
async def delete_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await deleteUser(db, current_user)

AVATAR_DIR = Path("uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WebP images are allowed.",
        )

    max_size = 5 * 1024 * 1024
    content = await file.read(max_size + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail="Avatar must be 5 MB or smaller.",
        )

    extension = allowed_types[file.content_type]
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = AVATAR_DIR / filename

    with file_path.open("wb") as avatar_file:
        avatar_file.write(content)

    current_user.avatar_url = f"/uploads/avatars/{filename}"

    await db.commit()
    await db.refresh(current_user)

    return current_user
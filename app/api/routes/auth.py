from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import registration, userLogin
from app.db.database_connection import get_db
from app.schemas.user import UserRegistration, UserResponse
from app.schemas.auth import TokenResponse, UserLogin

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegistration, db: AsyncSession = Depends(get_db)):
    return await registration(db, user_data)

@router.post("/login", response_model=TokenResponse)
async def user_login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    return await userLogin(db, user_data)
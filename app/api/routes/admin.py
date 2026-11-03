from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_admin, get_current_user
from app.crud.admin import delete_by_id, update_user_by_id
from app.db.database_connection import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(
    prefix="/management",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)]
)

@router.patch("/update/{user_id}", response_model=UserResponse)
async def update_by_id(user_data: UserUpdate, user_id: int, db: AsyncSession = Depends(get_db)):
    return await update_user_by_id(db, user_id, user_data)

@router.delete("/delete/{user_id}")
async def delete_User_By_Id(user_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_by_id(db, user_id)
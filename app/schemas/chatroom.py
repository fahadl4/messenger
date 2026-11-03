from datetime import datetime
from pydantic import BaseModel, Field

class ChatRoomCreate(BaseModel):
    receiver_id: int

class GroupChatCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    member_ids: list[int] = Field(min_length=1)

class ChatRoomDelete(BaseModel):
    room_id: int

class ChatRoomResponse(BaseModel):
    id: int
    created_by: int
    created_at: datetime
    name: str | None = None
    is_group: bool = False

    model_config = {
        "from_attributes": True
    }

class ChatRoomListResponse(BaseModel):
    id: int
    created_by: int
    created_at: datetime
    name: str | None = None
    is_group: bool = False
    other_user_id: int | None = None
    other_user_name: str | None = None
    other_user_email: str | None = None
    other_user_avatar_url: str | None = None
    member_count: int = 0
    last_message: str | None = None
    last_message_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    room_id: int

class MessageContent(MessageCreate):
    content: str

class MessageDelete(BaseModel):
    message_ids: list[int]

class MessageUpdate(BaseModel):
    message_id: int
    content: str

class MessageResponse(BaseModel):
    id: int
    room_id: int
    sender_id: int
    content: str
    created_at: datetime
    deleted_for_everyone_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True
    )
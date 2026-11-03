from datetime import datetime

from pydantic import BaseModel, Field

class MeetingAnalysisRequest(BaseModel):
    room_id: int = Field(gt=0)
    
class MeetingCreate(BaseModel):
    title: str
    meeting_date: datetime
    duration_minutes: int | None = None

class MeetingResponse(BaseModel):
    id: int
    room_id: int
    proposed_by: int
    title: str
    meeting_date: datetime
    duration_minutes: int | None = None
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }
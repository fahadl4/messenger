from pydantic import BaseModel, EmailStr, Field, field_validator

class UserBase(BaseModel):
    name: str
    email: EmailStr
    

class UserRegistration(UserBase):
    password: str = Field(..., min_length=8, max_length=72)
    
    @field_validator("password", mode="before")
    @classmethod
    def convert_password_to_string(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value
    
class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


class ChangePassword(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=72)

    @field_validator("new_password", mode="before")
    @classmethod
    def convert_password_to_string(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value


class UserResponse(UserBase):
    id: int
    avatar_url: str | None = None
    
    model_config = {
        "from_attributes": True
    }
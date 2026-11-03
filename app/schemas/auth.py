from pydantic import BaseModel, EmailStr, Field, field_validator

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    
    @field_validator("password", mode="before")
    @classmethod
    def convert_password_to_string(cls, value):
        if isinstance(value, (int, float)):
            return str(value)
        return value

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
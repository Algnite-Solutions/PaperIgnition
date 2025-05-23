from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    
class UserCreate(UserBase):
    password: str
    
class UserLogin(BaseModel):
    username: str
    password: str
    
class WechatLogin(BaseModel):
    code: str
    
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class TokenData(BaseModel):
    username: Optional[str] = None
    
class UserOut(UserBase):
    id: int
    is_active: bool
    interests_description: Optional[str] = None
    research_domain_ids: List[int] = []
    
    class Config:
        orm_mode = True

class WechatLoginResponse(Token):
    needs_profile_completion: bool = Field(False, description="Indicates if the user needs to complete their profile information.")

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    push_frequency: Optional[str] = None
    interests_description: Optional[str] = None
    research_domain_ids: Optional[List[int]] = None 
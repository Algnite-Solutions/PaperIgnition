from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    
class UserCreate(UserBase):
    username: str
    email: EmailStr
    password: str
    
class UserCreateEmail(BaseModel):
    email: EmailStr
    password: str
    
class UserLogin(BaseModel):
    username: str
    password: str
    
class UserLoginEmail(BaseModel):
    email: EmailStr
    password: str
    
class WechatLogin(BaseModel):
    code: str
    
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class TokenData(BaseModel):
    identifier: Optional[str] = None
    
class UserOut(UserBase):
    id: int
    is_active: Optional[bool] = True
    interests_description: Optional[List[str]] = None
    username: str
    email: EmailStr
    
    class Config:
        from_attributes = True

class UserInfo(BaseModel):
    email: EmailStr
    username: str

class EmailLoginResponse(Token):
    needs_interest_setup: bool = Field(False, description="Indicates if the user needs to set up their research interests.")
    user_info: UserInfo

class WechatLoginResponse(Token):
    needs_interest_setup: bool = Field(False, description="Indicates if the user needs to set up their research interests.")
    user_info: UserInfo

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    push_frequency: Optional[str] = None
    interests_description: Optional[List[str]] = None
    research_domain_ids: Optional[List[int]] = None
 
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class InquiryCreate(BaseModel):
    fullName: str
    email: EmailStr
    phone: str
    subject: Optional[str] = None
    message: str

class InquiryOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str
    subject: Optional[str] = None
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InquiryStatusUpdate(BaseModel):
    status: str  # pending | read | resolved
